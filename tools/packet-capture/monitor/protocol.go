package monitor

import (
	"bufio"
	"bytes"
	"compress/gzip"
	"encoding/json"
	"io"
	"net/http"
	"strings"

	"github.com/sirupsen/logrus"
)

// TokenSource 标记token数据的来源精确度
type TokenSource int

const (
	TokenSourceUnknown   TokenSource = iota // 未知来源
	TokenSourceEstimated                    // 字节数估算
	TokenSourceParsed                       // 从API响应JSON解析（最精确）
)

func (ts TokenSource) String() string {
	switch ts {
	case TokenSourceEstimated:
		return "estimated"
	case TokenSourceParsed:
		return "parsed"
	default:
		return "unknown"
	}
}

// TokenUsage 精确的token使用量
type TokenUsage struct {
	PromptTokens     uint64      `json:"prompt_tokens"`
	CompletionTokens uint64      `json:"completion_tokens"`
	TotalTokens      uint64      `json:"total_tokens"`
	Source           TokenSource `json:"source"`
	ModelName        string      `json:"model_name,omitempty"`
}

// openAIUsage OpenAI兼容的usage响应结构
type openAIUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
	// 部分厂商扩展字段
	PromptTokensDetails     *tokenDetails `json:"prompt_tokens_details,omitempty"`
	CompletionTokensDetails *tokenDetails `json:"completion_tokens_details,omitempty"`
}

type tokenDetails struct {
	CachedTokens int `json:"cached_tokens"`
	AudioTokens  int `json:"audio_tokens"`
}

// openAIResponse OpenAI兼容的响应体结构（非流式）
type openAIResponse struct {
	ID      string      `json:"id"`
	Object  string      `json:"object"`
	Model   string      `json:"model"`
	Usage   openAIUsage `json:"usage"`
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
}

// sseChunk SSE流式chunk中的usage（只在最后一个chunk中出现）
type sseChunk struct {
	Object string      `json:"object"`
	Usage  openAIUsage `json:"usage"`
	Model  string      `json:"model"`
}

// AIAPIPattern AI服务端点特征
type AIAPIPattern struct {
	// URL路径匹配规则
	PathPatterns []string
	// 请求Host匹配规则
	HostPatterns []string
	// Provider标识
	ProviderHint string
}

// knownAIPatterns 已知的AI API端点特征列表
var knownAIPatterns = []AIAPIPattern{
	{
		PathPatterns: []string{"/v1/chat/completions", "/v1/completions", "/chat/completions"},
		HostPatterns: []string{"api.openai.com"},
		ProviderHint: "openai",
	},
	{
		PathPatterns: []string{"/v1/chat/completions", "/api/v3/chat/completions"},
		HostPatterns: []string{"ark.cn-beijing.volces.com", "maas-api.ml-platform-cn-beijing.volces.com"},
		ProviderHint: "volcengine/doubao",
	},
	{
		PathPatterns: []string{"/v1/chat/completions"},
		HostPatterns: []string{"api.anthropic.com"},
		ProviderHint: "anthropic",
	},
	{
		PathPatterns: []string{"/v1/chat/completions", "/v1/messages"},
		HostPatterns: []string{"generativelanguage.googleapis.com"},
		ProviderHint: "google",
	},
	{
		PathPatterns: []string{"/v1/chat/completions", "/api/chat"},
		HostPatterns: []string{"trae.ai", "trae-api.tencent.com", "openapi.trae.ai"},
		ProviderHint: "trae",
	},
	{
		PathPatterns: []string{"/v1/chat/completions"},
		HostPatterns: []string{"api.cursor.sh", "api2.cursor.sh"},
		ProviderHint: "cursor",
	},
	{
		// 通用兜底：任何包含 /chat/completions 或 /v1/completions 的路径
		PathPatterns: []string{"/chat/completions", "/v1/completions", "/v1/messages"},
		HostPatterns: []string{},
		ProviderHint: "generic",
	},
}

// ProtocolParser 协议层解析器，负责从原始字节流中识别AI API流量并提取Token
type ProtocolParser struct{}

func NewProtocolParser() *ProtocolParser {
	return &ProtocolParser{}
}

// TryParseHTTPResponse 尝试将原始字节流解析为HTTP响应，并提取token用量
// 返回 nil 表示不是有效的AI API响应
func (p *ProtocolParser) TryParseHTTPResponse(data []byte) *TokenUsage {
	if len(data) < 12 {
		return nil
	}

	// 快速检测是否为HTTP响应（以HTTP/1.x或HTTP/2开头）
	if !isHTTPResponse(data) {
		return nil
	}

	resp, err := http.ReadResponse(bufio.NewReader(bytes.NewReader(data)), nil)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	// 只处理成功响应
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil
	}

	contentType := resp.Header.Get("Content-Type")
	if !isAIAPIContentType(contentType) {
		return nil
	}

	// 读取body（处理gzip压缩）
	body, err := readResponseBody(resp)
	if err != nil || len(body) == 0 {
		return nil
	}

	// 判断是否为SSE流式响应
	if strings.Contains(contentType, "text/event-stream") {
		return p.parseSSEBody(body, resp.Header.Get("X-Model-Name"))
	}

	// 尝试解析标准JSON响应
	return p.parseJSONBody(body)
}

// TryParseRawPayload 直接对原始payload（非完整HTTP帧）尝试提取token
// 用于已经分离出HTTP body的场景
func (p *ProtocolParser) TryParseRawPayload(data []byte) *TokenUsage {
	if len(data) < 10 {
		return nil
	}

	// 尝试JSON解析
	if data[0] == '{' {
		return p.parseJSONBody(data)
	}

	// 尝试SSE解析
	if bytes.HasPrefix(data, []byte("data:")) {
		return p.parseSSEBody(data, "")
	}

	return nil
}

// parseJSONBody 解析JSON格式的API响应，提取usage字段
func (p *ProtocolParser) parseJSONBody(body []byte) *TokenUsage {
	// 找到 "usage" 字段所在位置（快速路径，避免完整反序列化）
	usageIdx := bytes.Index(body, []byte(`"usage"`))
	if usageIdx < 0 {
		return nil
	}

	var resp openAIResponse
	if err := json.Unmarshal(body, &resp); err != nil {
		// 降级：尝试只解析usage部分
		return p.extractUsageFragment(body)
	}

	if resp.Usage.PromptTokens <= 0 && resp.Usage.CompletionTokens <= 0 {
		return nil
	}

	usage := &TokenUsage{
		PromptTokens:     uint64(resp.Usage.PromptTokens),
		CompletionTokens: uint64(resp.Usage.CompletionTokens),
		TotalTokens:      uint64(resp.Usage.TotalTokens),
		Source:           TokenSourceParsed,
		ModelName:        resp.Model,
	}

	if usage.TotalTokens == 0 {
		usage.TotalTokens = usage.PromptTokens + usage.CompletionTokens
	}

	logrus.Debugf("[Protocol] Parsed token usage from JSON: prompt=%d, completion=%d, model=%s",
		usage.PromptTokens, usage.CompletionTokens, usage.ModelName)

	return usage
}

// parseSSEBody 解析SSE流式响应中的token用量
// OpenAI兼容格式中，最后一个 data: 块（或 stream_options: include_usage 时）包含usage
func (p *ProtocolParser) parseSSEBody(body []byte, modelHint string) *TokenUsage {
	var lastUsage *TokenUsage

	scanner := bufio.NewScanner(bytes.NewReader(body))
	scanner.Buffer(make([]byte, 64*1024), 64*1024)

	for scanner.Scan() {
		line := scanner.Text()

		if !strings.HasPrefix(line, "data:") {
			continue
		}

		jsonStr := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
		if jsonStr == "[DONE]" {
			continue
		}

		if len(jsonStr) < 2 {
			continue
		}

		var chunk sseChunk
		if err := json.Unmarshal([]byte(jsonStr), &chunk); err != nil {
			continue
		}

		// 只有包含usage字段的chunk才有token信息
		if chunk.Usage.PromptTokens > 0 || chunk.Usage.CompletionTokens > 0 {
			modelName := chunk.Model
			if modelName == "" {
				modelName = modelHint
			}
			lastUsage = &TokenUsage{
				PromptTokens:     uint64(chunk.Usage.PromptTokens),
				CompletionTokens: uint64(chunk.Usage.CompletionTokens),
				TotalTokens:      uint64(chunk.Usage.TotalTokens),
				Source:           TokenSourceParsed,
				ModelName:        modelName,
			}
			if lastUsage.TotalTokens == 0 {
				lastUsage.TotalTokens = lastUsage.PromptTokens + lastUsage.CompletionTokens
			}
		}
	}

	if lastUsage != nil {
		logrus.Debugf("[Protocol] Parsed token usage from SSE: prompt=%d, completion=%d",
			lastUsage.PromptTokens, lastUsage.CompletionTokens)
	}

	return lastUsage
}

// extractUsageFragment 当完整JSON解析失败时，尝试用字节搜索提取usage片段
func (p *ProtocolParser) extractUsageFragment(body []byte) *TokenUsage {
	// 查找 "prompt_tokens" 和 "completion_tokens" 字段
	type partialUsage struct {
		Usage struct {
			PromptTokens     int `json:"prompt_tokens"`
			CompletionTokens int `json:"completion_tokens"`
			TotalTokens      int `json:"total_tokens"`
		} `json:"usage"`
	}

	var partial partialUsage
	if err := json.Unmarshal(body, &partial); err != nil {
		return nil
	}

	if partial.Usage.PromptTokens <= 0 && partial.Usage.CompletionTokens <= 0 {
		return nil
	}

	return &TokenUsage{
		PromptTokens:     uint64(partial.Usage.PromptTokens),
		CompletionTokens: uint64(partial.Usage.CompletionTokens),
		TotalTokens:      uint64(partial.Usage.TotalTokens),
		Source:           TokenSourceParsed,
	}
}

// IsAIAPIRequest 判断HTTP请求是否为AI API请求
func IsAIAPIRequest(host, path, method string) bool {
	if method != "POST" {
		return false
	}
	return matchesAIPattern(host, path)
}

// matchesAIPattern 检查host和path是否匹配已知AI API特征
func matchesAIPattern(host, path string) bool {
	hostLower := strings.ToLower(host)
	pathLower := strings.ToLower(path)

	for _, pattern := range knownAIPatterns {
		// 路径匹配（必须）
		pathMatched := false
		for _, pathPat := range pattern.PathPatterns {
			if strings.Contains(pathLower, strings.ToLower(pathPat)) {
				pathMatched = true
				break
			}
		}
		if !pathMatched {
			continue
		}

		// 无host限制（通用匹配）
		if len(pattern.HostPatterns) == 0 {
			return true
		}

		// host匹配
		for _, hostPat := range pattern.HostPatterns {
			if strings.Contains(hostLower, strings.ToLower(hostPat)) {
				return true
			}
		}
	}
	return false
}

// isHTTPResponse 快速判断字节流是否为HTTP响应
func isHTTPResponse(data []byte) bool {
	return bytes.HasPrefix(data, []byte("HTTP/1.")) ||
		bytes.HasPrefix(data, []byte("HTTP/2"))
}

// isAIAPIContentType 判断Content-Type是否为AI API常见类型
func isAIAPIContentType(ct string) bool {
	ct = strings.ToLower(ct)
	return strings.Contains(ct, "application/json") ||
		strings.Contains(ct, "text/event-stream")
}

// readResponseBody 读取HTTP响应body，处理gzip压缩
func readResponseBody(resp *http.Response) ([]byte, error) {
	var reader io.Reader = resp.Body

	if strings.EqualFold(resp.Header.Get("Content-Encoding"), "gzip") {
		gzReader, err := gzip.NewReader(resp.Body)
		if err != nil {
			return nil, err
		}
		defer gzReader.Close()
		reader = gzReader
	}

	return io.ReadAll(io.LimitReader(reader, 1*1024*1024)) // 最多读取1MB
}

// EstimateTokensFromBytes 基于字节数的兜底估算（精度较低，仅作备用）
// 考虑到JSON结构开销，请求/响应有不同的压缩率
func EstimateTokensFromBytes(bytes uint64, isRequest bool) uint64 {
	if bytes == 0 {
		return 0
	}
	// 请求体：平均每个token约5-6字节（含JSON包装）
	// 响应体：平均每个token约3-4字节
	ratio := 5.5
	if !isRequest {
		ratio = 3.5
	}
	tokens := uint64(float64(bytes) / ratio)
	if tokens < 1 {
		tokens = 1
	}
	return tokens
}
