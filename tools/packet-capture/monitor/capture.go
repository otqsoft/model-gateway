package monitor

// capture.go - 基于进程网络连接感知的HTTP流量捕获与Token提取
//
// 设计思路：
//   由于直接使用 gopacket/pcap 需要 WinPcap/npcap 驱动且存在跨平台复杂性，
//   本模块采用"连接级流量追踪"策略：
//
//   1. 通过 gopsutil 枚举目标进程的 TCP 连接，获取已建立连接的四元组
//   2. 对每个连接维护一个"流缓冲区"，积累数据
//   3. 同时通过 /proc/net/tcp 或 Windows ETW（轻量级）获取连接级流量差值
//   4. 结合协议特征（端口443/80、Host头部匹配）过滤出 AI API 连接
//   5. 尝试拦截明文HTTP流量（非TLS）；对TLS流量降级为字节估算
//
//   关键优化点：
//   - AI API 端口通常为 443（HTTPS），TLS 加密无法直接解析 payload
//   - 但豆包桌面客户端、部分工具可能走 HTTP 明文代理
//   - 更重要的是：通过进程级别的 IO 计数 + 连接过滤 可大幅提升估算精度

import (
	"bytes"
	"fmt"
	"net"
	"strconv"
	"strings"
	"sync"
	"time"

	psnet "github.com/shirou/gopsutil/v3/net"
	"github.com/sirupsen/logrus"
)

// ConnectionInfo 描述一个已建立的TCP连接
type ConnectionInfo struct {
	LocalAddr  string
	RemoteAddr string
	RemoteIP   string
	RemotePort uint32
	PID        int32
	IsAIHost   bool // 是否匹配已知AI服务主机
}

// StreamBuffer 对单条TCP连接的流数据进行缓冲
type StreamBuffer struct {
	data      []byte
	createdAt time.Time
	lastWrite time.Time
}

const (
	maxStreamBufferSize = 2 * 1024 * 1024 // 2MB
	streamBufferTTL     = 30 * time.Second
)

// ConnectionTracker 连接级别的流量追踪器
type ConnectionTracker struct {
	mu          sync.Mutex
	connections map[string]*ConnectionInfo  // key: "localAddr->remoteAddr"
	streams     map[string]*StreamBuffer    // key: connKey
	parser      *ProtocolParser
}

func NewConnectionTracker() *ConnectionTracker {
	ct := &ConnectionTracker{
		connections: make(map[string]*ConnectionInfo),
		streams:     make(map[string]*StreamBuffer),
		parser:      NewProtocolParser(),
	}
	go ct.gcLoop()
	return ct
}

// connKey 生成连接的唯一标识
func connKey(localAddr, remoteAddr string) string {
	return localAddr + "->" + remoteAddr
}

// ScanProcessConnections 扫描指定进程的TCP连接，识别AI API相关连接
func (ct *ConnectionTracker) ScanProcessConnections(pids []int32) []*ConnectionInfo {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	if len(pids) == 0 {
		return nil
	}

	pidSet := make(map[int32]bool, len(pids))
	for _, pid := range pids {
		pidSet[pid] = true
	}

	conns, err := psnet.Connections("tcp")
	if err != nil {
		logrus.Debugf("[Capture] Failed to get connections: %v", err)
		return nil
	}

	var aiConns []*ConnectionInfo
	for _, conn := range conns {
		if !pidSet[conn.Pid] {
			continue
		}
		if conn.Status != "ESTABLISHED" {
			continue
		}

		remoteIP := conn.Raddr.IP
		remotePort := conn.Raddr.Port

		// 只关注HTTP/HTTPS端口
		if remotePort != 80 && remotePort != 443 && remotePort != 8080 && remotePort != 8443 {
			continue
		}

		if !isExternalIP(remoteIP) {
			continue
		}

		localAddr := fmt.Sprintf("%s:%d", conn.Laddr.IP, conn.Laddr.Port)
		remoteAddr := fmt.Sprintf("%s:%d", remoteIP, remotePort)
		key := connKey(localAddr, remoteAddr)

		info := &ConnectionInfo{
			LocalAddr:  localAddr,
			RemoteAddr: remoteAddr,
			RemoteIP:   remoteIP,
			RemotePort: remotePort,
			PID:        conn.Pid,
		}

		// 尝试通过IP反查主机名来识别AI服务
		info.IsAIHost = ct.isKnownAIEndpoint(remoteIP, int(remotePort))

		ct.connections[key] = info
		aiConns = append(aiConns, info)
	}

	return aiConns
}

// FeedData 向指定连接的流缓冲区写入数据（用于非加密代理场景）
func (ct *ConnectionTracker) FeedData(localAddr, remoteAddr string, data []byte) *TokenUsage {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	key := connKey(localAddr, remoteAddr)
	buf, ok := ct.streams[key]
	if !ok {
		buf = &StreamBuffer{
			createdAt: time.Now(),
		}
		ct.streams[key] = buf
	}

	buf.data = append(buf.data, data...)
	buf.lastWrite = time.Now()

	// 防止缓冲区过大
	if len(buf.data) > maxStreamBufferSize {
		buf.data = buf.data[len(buf.data)-maxStreamBufferSize:]
	}

	// 尝试解析
	return ct.tryExtractTokens(key, buf)
}

// tryExtractTokens 尝试从流缓冲区中提取完整的HTTP响应并解析token
func (ct *ConnectionTracker) tryExtractTokens(key string, buf *StreamBuffer) *TokenUsage {
	if len(buf.data) < 12 {
		return nil
	}

	// 查找HTTP响应起始位置
	httpIdx := bytes.Index(buf.data, []byte("HTTP/1."))
	if httpIdx < 0 {
		httpIdx = bytes.Index(buf.data, []byte("HTTP/2"))
	}
	if httpIdx < 0 {
		return nil
	}

	slice := buf.data[httpIdx:]
	usage := ct.parser.TryParseHTTPResponse(slice)
	if usage != nil {
		// 清空已消费的数据
		buf.data = nil
		logrus.Debugf("[Capture] Extracted token usage from stream %s: prompt=%d, completion=%d",
			key, usage.PromptTokens, usage.CompletionTokens)
	}

	return usage
}

// isKnownAIEndpoint 通过IP和端口判断是否为已知AI服务端点
// 在实际场景中可以维护一个IP缓存或通过反向DNS查询
func (ct *ConnectionTracker) isKnownAIEndpoint(ip string, port int) bool {
	// 常见AI API服务的IP段特征（示例）
	// 实际中可以通过DNS缓存或手动配置IP白名单
	knownHosts := []string{
		"api.openai.com",
		"ark.cn-beijing.volces.com",
		"api.anthropic.com",
		"trae.ai",
		"api.cursor.sh",
	}

	for _, host := range knownHosts {
		addrs, err := net.LookupHost(host)
		if err != nil {
			continue
		}
		for _, addr := range addrs {
			if addr == ip {
				return true
			}
		}
	}

	return false
}

// GetAIConnectionCount 返回当前追踪的AI相关连接数量
func (ct *ConnectionTracker) GetAIConnectionCount() int {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	count := 0
	for _, conn := range ct.connections {
		if conn.IsAIHost {
			count++
		}
	}
	return count
}

// gcLoop 定期清理过期的流缓冲区和连接信息
func (ct *ConnectionTracker) gcLoop() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		ct.mu.Lock()
		now := time.Now()
		for key, buf := range ct.streams {
			if now.Sub(buf.lastWrite) > streamBufferTTL {
				delete(ct.streams, key)
			}
		}
		ct.mu.Unlock()
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// HTTPInterceptProxy - 轻量级本地HTTP代理拦截器
// 通过在本地开启透明代理，拦截非加密HTTP流量来获取精确Token
// ─────────────────────────────────────────────────────────────────────────────

// InterceptResult 拦截结果
type InterceptResult struct {
	AppName  string
	Usage    *TokenUsage
	ReqHost  string
	ReqPath  string
	ReqSize  int
	RespSize int
}

// PayloadScanner 扫描原始payload中的token信息（用于进程内存或代理场景）
type PayloadScanner struct {
	parser *ProtocolParser
}

func NewPayloadScanner() *PayloadScanner {
	return &PayloadScanner{
		parser: NewProtocolParser(),
	}
}

// ScanBytes 对任意字节块尝试提取token用量
// 按优先级依次尝试：完整HTTP响应 → SSE数据块 → 裸JSON
func (ps *PayloadScanner) ScanBytes(data []byte) *TokenUsage {
	if len(data) < 10 {
		return nil
	}

	// 尝试完整HTTP响应解析
	if isHTTPResponse(data) {
		if usage := ps.parser.TryParseHTTPResponse(data); usage != nil {
			return usage
		}
	}

	// 尝试SSE数据解析
	if bytes.Contains(data, []byte("data:")) {
		if usage := ps.parser.parseSSEBody(data, ""); usage != nil {
			return usage
		}
	}

	// 尝试裸JSON解析
	if idx := bytes.Index(data, []byte(`"usage"`)); idx >= 0 {
		// 找到包含usage的JSON对象
		start := bytes.LastIndexByte(data[:idx], '{')
		if start >= 0 {
			if usage := ps.parser.TryParseRawPayload(data[start:]); usage != nil {
				return usage
			}
		}
	}

	return nil
}

// ParseHTTPLogLine 解析HTTP访问日志中的token信息
// 支持格式：通过Nginx/Caddy等代理输出的包含token计数的访问日志
func ParseHTTPLogLine(line string) *TokenUsage {
	// 匹配自定义日志格式中的token字段
	// 例如：... prompt_tokens=100 completion_tokens=200 ...
	parts := strings.Fields(line)
	usage := &TokenUsage{Source: TokenSourceParsed}
	found := false

	for _, part := range parts {
		if kv := strings.SplitN(part, "=", 2); len(kv) == 2 {
			key := kv[0]
			val, err := strconv.ParseInt(kv[1], 10, 64)
			if err != nil {
				continue
			}
			switch key {
			case "prompt_tokens", "input_tokens":
				usage.PromptTokens = uint64(val)
				found = true
			case "completion_tokens", "output_tokens":
				usage.CompletionTokens = uint64(val)
				found = true
			case "total_tokens":
				usage.TotalTokens = uint64(val)
			case "model":
				usage.ModelName = kv[1]
			}
		}
	}

	if !found {
		return nil
	}

	if usage.TotalTokens == 0 {
		usage.TotalTokens = usage.PromptTokens + usage.CompletionTokens
	}

	return usage
}

// AdaptiveTokenEstimator 自适应Token估算器
// 在无法精确解析时，根据历史数据动态调整估算比率
type AdaptiveTokenEstimator struct {
	mu sync.RWMutex
	// 历史精确样本：[字节数, token数]
	requestSamples  []samplePoint
	responseSamples []samplePoint
	// 当前估算比率（字节/token）
	requestRatio  float64
	responseRatio float64
	// 精确token总量（已解析）
	exactPromptTokens     uint64
	exactCompletionTokens uint64
	// 估算token总量
	estimatedPromptTokens     uint64
	estimatedCompletionTokens uint64
}

type samplePoint struct {
	bytes  uint64
	tokens uint64
}

const (
	defaultRequestRatio  = 5.5  // 请求：每token约5.5字节（含JSON包装）
	defaultResponseRatio = 3.5  // 响应：每token约3.5字节
	maxSamples           = 100  // 最多保留100个历史样本
)

func NewAdaptiveTokenEstimator() *AdaptiveTokenEstimator {
	return &AdaptiveTokenEstimator{
		requestRatio:  defaultRequestRatio,
		responseRatio: defaultResponseRatio,
	}
}

// FeedExactSample 输入一个精确的token-字节对应样本，用于校准估算比率
func (e *AdaptiveTokenEstimator) FeedExactSample(requestBytes, responseBytes uint64, usage *TokenUsage) {
	e.mu.Lock()
	defer e.mu.Unlock()

	if usage.PromptTokens > 0 && requestBytes > 0 {
		e.requestSamples = append(e.requestSamples, samplePoint{requestBytes, usage.PromptTokens})
		if len(e.requestSamples) > maxSamples {
			e.requestSamples = e.requestSamples[1:]
		}
		e.requestRatio = e.calcRatio(e.requestSamples)
	}

	if usage.CompletionTokens > 0 && responseBytes > 0 {
		e.responseSamples = append(e.responseSamples, samplePoint{responseBytes, usage.CompletionTokens})
		if len(e.responseSamples) > maxSamples {
			e.responseSamples = e.responseSamples[1:]
		}
		e.responseRatio = e.calcRatio(e.responseSamples)
	}

	e.exactPromptTokens += usage.PromptTokens
	e.exactCompletionTokens += usage.CompletionTokens

	logrus.Debugf("[Estimator] Updated ratios: request=%.2f bytes/token, response=%.2f bytes/token",
		e.requestRatio, e.responseRatio)
}

// EstimateFromBytes 基于当前校准后的比率估算token数
func (e *AdaptiveTokenEstimator) EstimateFromBytes(requestBytes, responseBytes uint64) *TokenUsage {
	e.mu.RLock()
	defer e.mu.RUnlock()

	promptTokens := uint64(float64(requestBytes) / e.requestRatio)
	completionTokens := uint64(float64(responseBytes) / e.responseRatio)

	if promptTokens == 0 && requestBytes > 0 {
		promptTokens = 1
	}
	if completionTokens == 0 && responseBytes > 0 {
		completionTokens = 1
	}

	return &TokenUsage{
		PromptTokens:     promptTokens,
		CompletionTokens: completionTokens,
		TotalTokens:      promptTokens + completionTokens,
		Source:           TokenSourceEstimated,
	}
}

// GetCurrentRatios 获取当前的估算比率
func (e *AdaptiveTokenEstimator) GetCurrentRatios() (requestRatio, responseRatio float64) {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.requestRatio, e.responseRatio
}

// GetAccuracyStats 获取精度统计
func (e *AdaptiveTokenEstimator) GetAccuracyStats() map[string]interface{} {
	e.mu.RLock()
	defer e.mu.RUnlock()

	return map[string]interface{}{
		"exact_prompt_tokens":      e.exactPromptTokens,
		"exact_completion_tokens":  e.exactCompletionTokens,
		"estimated_prompt_tokens":  e.estimatedPromptTokens,
		"estimated_completion_tokens": e.estimatedCompletionTokens,
		"request_ratio":            e.requestRatio,
		"response_ratio":           e.responseRatio,
		"sample_count":             len(e.requestSamples),
	}
}

// calcRatio 基于历史样本计算字节/token比率（加权平均）
func (e *AdaptiveTokenEstimator) calcRatio(samples []samplePoint) float64 {
	if len(samples) == 0 {
		return defaultRequestRatio
	}

	var totalBytes, totalTokens uint64
	for _, s := range samples {
		totalBytes += s.bytes
		totalTokens += s.tokens
	}

	if totalTokens == 0 {
		return defaultRequestRatio
	}

	return float64(totalBytes) / float64(totalTokens)
}
