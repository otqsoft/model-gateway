package monitor

import (
	"ai-token-monitor/config"
	"ai-token-monitor/gateway"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
)

type ReportRecord struct {
	Timestamp        time.Time `json:"timestamp"`
	AppName          string    `json:"app_name"`
	Success          bool      `json:"success"`
	PromptTokens     int       `json:"prompt_tokens"`
	CompletionTokens int       `json:"completion_tokens"`
	TokenSource      string    `json:"token_source,omitempty"` // "parsed" | "estimated"
	ErrorMsg         string    `json:"error_msg,omitempty"`
}

type Manager struct {
	config              *config.Config
	gateway             *gateway.Client
	stats               map[string]*AppStats
	processMonitor      *ProcessMonitor
	estimators          map[string]*AdaptiveTokenEstimator // 每个应用独立的自适应估算器
	mu                  sync.RWMutex
	running             bool
	stopChan            chan struct{}
	reportStopChan      chan struct{}
	gatewaySuccessCount int
	gatewayFailCount    int
	gatewayLastLogTime  time.Time
	reportHistory       []ReportRecord
}

// AppStats 应用的Token使用统计，包含精确计数和估算计数
type AppStats struct {
	ToolName            string
	ProviderName        string
	ProcessNames        []string
	IsRunning           bool
	HasNetworkConn      bool
	RunningProcessNames []string

	// 总计统计（从程序启动累计）
	TotalSentBytes        uint64
	TotalReceivedBytes    uint64
	TotalPromptTokens     uint64 // 精确+估算的综合最优值
	TotalCompletionTokens uint64

	// 精确解析计数（从API响应JSON直接读取，最准确）
	TotalExactPromptTokens     uint64
	TotalExactCompletionTokens uint64
	ExactSampleCount           uint64 // 精确解析成功的次数

	// 本次会话统计（距离上次上报后的数据）
	SessionSentBytes        uint64
	SessionReceivedBytes    uint64
	SessionPromptTokens     uint64
	SessionCompletionTokens uint64

	// 会话精确计数
	SessionExactPromptTokens     uint64
	SessionExactCompletionTokens uint64

	// 估算精度指标
	TokenAccuracy    float64 `json:"token_accuracy"`    // 精确解析占比 0.0~1.0
	EstimateRatioReq float64 `json:"estimate_ratio_req"` // 当前请求字节/token 估算比率
	EstimateRatioRsp float64 `json:"estimate_ratio_rsp"` // 当前响应字节/token 估算比率

	// 最后检测到的模型名称
	LastModelName string

	LastUpdate time.Time
}

func NewManager(cfg *config.Config) *Manager {
	return &Manager{
		config:         cfg,
		gateway:        gateway.NewClient(cfg),
		stats:          make(map[string]*AppStats),
		estimators:     make(map[string]*AdaptiveTokenEstimator),
		processMonitor: NewProcessMonitor(),
		stopChan:       make(chan struct{}),
	}
}

// getOrCreateEstimator 获取或创建指定应用的自适应估算器
func (m *Manager) getOrCreateEstimator(appName string) *AdaptiveTokenEstimator {
	if e, ok := m.estimators[appName]; ok {
		return e
	}
	e := NewAdaptiveTokenEstimator()
	m.estimators[appName] = e
	return e
}

func (m *Manager) Start() {
	if m.running {
		return
	}
	m.running = true

	logrus.Info("Starting monitor manager...")

	for _, app := range m.config.MonitoredApps {
		m.stats[app.Name] = &AppStats{
			ToolName:         app.ToolName,
			ProviderName:     app.ProviderName,
			ProcessNames:     app.ProcessNames,
			EstimateRatioReq: defaultRequestRatio,
			EstimateRatioRsp: defaultResponseRatio,
		}
		m.estimators[app.Name] = NewAdaptiveTokenEstimator()
		logrus.Infof("Monitoring app: %s (process: %v, network_ratio: %.4f)",
			app.Name, app.ProcessNames, app.GetNetworkRatio())
	}

	go m.monitorLoop()
	if m.config.Gateway.Enabled {
		go m.reportLoop()
	} else {
		logrus.Info("Gateway reporting disabled, report loop not started")
	}
}

func (m *Manager) Stop() {
	if !m.running {
		return
	}
	m.running = false
	close(m.stopChan)
	logrus.Info("Monitor manager stopped")
}

func (m *Manager) monitorLoop() {
	m.pollProcessIO()

	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.pollProcessIO()
		case <-m.stopChan:
			return
		}
	}
}

func (m *Manager) pollProcessIO() {
	m.mu.Lock()
	defer m.mu.Unlock()

	for _, app := range m.config.MonitoredApps {
		delta := m.processMonitor.SampleAndCalculateDelta(app.Name, app.ProcessNames)

		stats, ok := m.stats[app.Name]
		if !ok {
			stats = &AppStats{
				ToolName:         app.ToolName,
				ProviderName:     app.ProviderName,
				ProcessNames:     app.ProcessNames,
				EstimateRatioReq: defaultRequestRatio,
				EstimateRatioRsp: defaultResponseRatio,
			}
			m.stats[app.Name] = stats
		}

		stats.IsRunning = delta.Running
		stats.HasNetworkConn = delta.HasNetworkConn

		if delta.Running {
			stats.RunningProcessNames = m.processMonitor.GetRunningProcessNames(app.Name, app.ProcessNames)
		} else {
			stats.RunningProcessNames = nil
		}

		if delta.SentDelta > 0 || delta.ReceivedDelta > 0 {
			networkRatio := app.GetNetworkRatio()

			// 过滤出AI API相关的网络流量（基于network_ratio配置）
			networkSentBytes := uint64(float64(delta.SentDelta) * networkRatio)
			networkReceivedBytes := uint64(float64(delta.ReceivedDelta) * networkRatio)

			// 使用自适应估算器计算token
			estimator := m.getOrCreateEstimator(app.Name)
			estimated := estimator.EstimateFromBytes(networkSentBytes, networkReceivedBytes)

			reqRatio, rspRatio := estimator.GetCurrentRatios()
			stats.EstimateRatioReq = reqRatio
			stats.EstimateRatioRsp = rspRatio

			stats.TotalSentBytes += networkSentBytes
			stats.TotalReceivedBytes += networkReceivedBytes
			stats.TotalPromptTokens += estimated.PromptTokens
			stats.TotalCompletionTokens += estimated.CompletionTokens

			stats.SessionSentBytes += networkSentBytes
			stats.SessionReceivedBytes += networkReceivedBytes
			stats.SessionPromptTokens += estimated.PromptTokens
			stats.SessionCompletionTokens += estimated.CompletionTokens

			stats.LastUpdate = time.Now()

			logrus.Debugf("[%s] IO delta: sent=%d, received=%d | ai_traffic(%.2f%%): sent=%d, received=%d | estimated tokens: prompt=%d, completion=%d (ratio: req=%.1f, rsp=%.1f)",
				app.Name, delta.SentDelta, delta.ReceivedDelta, networkRatio*100,
				networkSentBytes, networkReceivedBytes,
				estimated.PromptTokens, estimated.CompletionTokens,
				reqRatio, rspRatio)
		}
	}
}

func (m *Manager) GetStats() map[string]*AppStats {
	m.mu.RLock()
	defer m.mu.RUnlock()

	stats := make(map[string]*AppStats)
	for k, v := range m.stats {
		s := &AppStats{
			ToolName:                    v.ToolName,
			ProviderName:                v.ProviderName,
			ProcessNames:                v.ProcessNames,
			IsRunning:                   v.IsRunning,
			HasNetworkConn:              v.HasNetworkConn,
			RunningProcessNames:         v.RunningProcessNames,
			TotalSentBytes:              v.TotalSentBytes,
			TotalReceivedBytes:          v.TotalReceivedBytes,
			TotalPromptTokens:           v.TotalPromptTokens,
			TotalCompletionTokens:       v.TotalCompletionTokens,
			TotalExactPromptTokens:      v.TotalExactPromptTokens,
			TotalExactCompletionTokens:  v.TotalExactCompletionTokens,
			ExactSampleCount:            v.ExactSampleCount,
			SessionSentBytes:            v.SessionSentBytes,
			SessionReceivedBytes:        v.SessionReceivedBytes,
			SessionPromptTokens:         v.SessionPromptTokens,
			SessionCompletionTokens:     v.SessionCompletionTokens,
			SessionExactPromptTokens:    v.SessionExactPromptTokens,
			SessionExactCompletionTokens: v.SessionExactCompletionTokens,
			TokenAccuracy:               v.TokenAccuracy,
			EstimateRatioReq:            v.EstimateRatioReq,
			EstimateRatioRsp:            v.EstimateRatioRsp,
			LastModelName:               v.LastModelName,
			LastUpdate:                  v.LastUpdate,
		}
		if v.RunningProcessNames != nil {
			s.RunningProcessNames = make([]string, len(v.RunningProcessNames))
			copy(s.RunningProcessNames, v.RunningProcessNames)
		}
		stats[k] = s
	}
	return stats
}

func (m *Manager) GetGatewayStats() map[string]int {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return map[string]int{
		"success_count": m.gatewaySuccessCount,
		"fail_count":    m.gatewayFailCount,
	}
}

func (m *Manager) GetReportHistory() []ReportRecord {
	m.mu.RLock()
	defer m.mu.RUnlock()

	history := make([]ReportRecord, len(m.reportHistory))
	copy(history, m.reportHistory)
	return history
}

func (m *Manager) RecordTraffic(appName string, sentBytes, receivedBytes uint64) {
	m.mu.Lock()
	defer m.mu.Unlock()

	stats, ok := m.stats[appName]
	if !ok {
		stats = &AppStats{
			ToolName:         appName,
			EstimateRatioReq: defaultRequestRatio,
			EstimateRatioRsp: defaultResponseRatio,
		}
		m.stats[appName] = stats
	}

	estimator := m.getOrCreateEstimator(appName)
	estimated := estimator.EstimateFromBytes(sentBytes, receivedBytes)

	stats.TotalSentBytes += sentBytes
	stats.TotalReceivedBytes += receivedBytes
	stats.TotalPromptTokens += estimated.PromptTokens
	stats.TotalCompletionTokens += estimated.CompletionTokens

	stats.SessionSentBytes += sentBytes
	stats.SessionReceivedBytes += receivedBytes
	stats.SessionPromptTokens += estimated.PromptTokens
	stats.SessionCompletionTokens += estimated.CompletionTokens

	stats.LastUpdate = time.Now()

	logrus.Infof("[Manual] Recorded traffic for %s: sent=%d, received=%d, estimated prompt_tokens=%d, completion_tokens=%d",
		appName, sentBytes, receivedBytes, estimated.PromptTokens, estimated.CompletionTokens)
}

// RecordExactTokenUsage 记录从API响应中精确解析得到的Token数量
// 这是最准确的数据来源，同时用于校准自适应估算器
func (m *Manager) RecordExactTokenUsage(appName string, sentBytes, receivedBytes uint64, usage *TokenUsage) {
	m.mu.Lock()
	defer m.mu.Unlock()

	stats, ok := m.stats[appName]
	if !ok {
		logrus.Warnf("[Exact] App %s not found in stats", appName)
		return
	}

	// 用精确数据校准估算器
	estimator := m.getOrCreateEstimator(appName)
	estimator.FeedExactSample(sentBytes, receivedBytes, usage)

	// 更新精确计数
	stats.TotalExactPromptTokens += usage.PromptTokens
	stats.TotalExactCompletionTokens += usage.CompletionTokens
	stats.SessionExactPromptTokens += usage.PromptTokens
	stats.SessionExactCompletionTokens += usage.CompletionTokens
	stats.ExactSampleCount++

	if usage.ModelName != "" {
		stats.LastModelName = usage.ModelName
	}

	// 更新综合最优token值：优先使用精确值
	// 对于已精确计数的token，直接叠加到total中（不再做估算重复加）
	stats.TotalPromptTokens = stats.TotalExactPromptTokens
	stats.TotalCompletionTokens = stats.TotalExactCompletionTokens
	stats.SessionPromptTokens = stats.SessionExactPromptTokens
	stats.SessionCompletionTokens = stats.SessionExactCompletionTokens

	// 更新精度指标
	reqRatio, rspRatio := estimator.GetCurrentRatios()
	stats.EstimateRatioReq = reqRatio
	stats.EstimateRatioRsp = rspRatio
	if stats.TotalPromptTokens+stats.TotalCompletionTokens > 0 {
		exactTotal := float64(stats.TotalExactPromptTokens + stats.TotalExactCompletionTokens)
		allTotal := float64(stats.TotalPromptTokens + stats.TotalCompletionTokens)
		if allTotal > 0 {
			stats.TokenAccuracy = exactTotal / allTotal
		}
	}

	stats.LastUpdate = time.Now()

	logrus.Infof("[Exact] Recorded exact token usage for %s: prompt=%d, completion=%d, model=%s (accuracy: %.1f%%)",
		appName, usage.PromptTokens, usage.CompletionTokens, usage.ModelName, stats.TokenAccuracy*100)
}

func (m *Manager) AddTraffic(appName string, sent, received uint64) {
	m.RecordTraffic(appName, sent, received)
}

func (m *Manager) UpdateConfig(cfg *config.Config) {
	m.mu.Lock()

	oldEnabled := m.config.Gateway.Enabled
	oldInterval := m.config.Gateway.GetReportInterval()

	m.config = cfg
	m.gateway.UpdateConfig(cfg)

	appNames := make(map[string]bool)
	for _, app := range cfg.MonitoredApps {
		appNames[app.Name] = true
		if _, ok := m.stats[app.Name]; !ok {
			m.stats[app.Name] = &AppStats{
				ToolName:         app.ToolName,
				ProviderName:     app.ProviderName,
				ProcessNames:     app.ProcessNames,
				EstimateRatioReq: defaultRequestRatio,
				EstimateRatioRsp: defaultResponseRatio,
			}
			m.estimators[app.Name] = NewAdaptiveTokenEstimator()
		} else {
			m.stats[app.Name].ToolName = app.ToolName
			m.stats[app.Name].ProviderName = app.ProviderName
			m.stats[app.Name].ProcessNames = app.ProcessNames
		}
	}

	for name := range m.stats {
		if !appNames[name] {
			delete(m.stats, name)
			delete(m.estimators, name)
		}
	}

	m.mu.Unlock()

	if !oldEnabled && cfg.Gateway.Enabled {
		go m.reportLoop()
	}

	if oldInterval != cfg.Gateway.GetReportInterval() {
		go m.reportLoop()
	}
}

func (m *Manager) reportLoop() {
	interval := time.Duration(m.config.Gateway.GetReportInterval()) * time.Second
	logrus.Infof("Gateway report interval: %v", interval)

	stopChan := make(chan struct{})
	m.mu.Lock()
	if m.reportStopChan != nil {
		close(m.reportStopChan)
	}
	m.reportStopChan = stopChan
	m.mu.Unlock()

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.reportStats()
		case <-stopChan:
			return
		case <-m.stopChan:
			return
		}
	}
}

func (m *Manager) reportStats() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.config.Gateway.Enabled {
		return
	}

	now := time.Now()

	for appName, stats := range m.stats {
		if stats.SessionPromptTokens == 0 && stats.SessionCompletionTokens == 0 {
			continue
		}

		// 优先使用精确解析的token数，回退到估算值
		promptTokens := stats.SessionPromptTokens
		completionTokens := stats.SessionCompletionTokens
		tokenSource := "estimated"

		if stats.SessionExactPromptTokens > 0 || stats.SessionExactCompletionTokens > 0 {
			promptTokens = stats.SessionExactPromptTokens
			completionTokens = stats.SessionExactCompletionTokens
			tokenSource = "parsed"
		}

		detail := map[string]interface{}{
			"type":          "session",
			"description":   "Session traffic statistics",
			"token_source":  tokenSource,
			"token_accuracy": stats.TokenAccuracy,
		}
		if stats.LastModelName != "" {
			detail["model"] = stats.LastModelName
		}

		report := &gateway.UsageItem{
			ToolName:         stats.ToolName,
			ProviderName:     stats.ProviderName,
			PromptTokens:     int(promptTokens),
			CompletionTokens: int(completionTokens),
			Detail:           detail,
		}

		err := m.gateway.ReportUsage(report)
		record := ReportRecord{
			Timestamp:        now,
			AppName:          appName,
			PromptTokens:     int(promptTokens),
			CompletionTokens: int(completionTokens),
			TokenSource:      tokenSource,
		}
		if err != nil {
			m.gatewayFailCount++
			record.Success = false
			record.ErrorMsg = err.Error()
			if time.Since(m.gatewayLastLogTime) >= 5*time.Minute || m.gatewayFailCount <= 1 {
				logrus.Warnf("Failed to report usage for %s: %v (consecutive failures: %d)", appName, err, m.gatewayFailCount)
				m.gatewayLastLogTime = time.Now()
			}
		} else {
			m.gatewaySuccessCount++
			record.Success = true
			if m.gatewayFailCount > 0 {
				logrus.Infof("Gateway recovered after %d failures", m.gatewayFailCount)
				m.gatewayFailCount = 0
			}
			logrus.Infof("Reported usage for %s: prompt=%d, completion=%d [source=%s, accuracy=%.1f%%]",
				appName, promptTokens, completionTokens, tokenSource, stats.TokenAccuracy*100)
		}

		m.reportHistory = append(m.reportHistory, record)
		if len(m.reportHistory) > 200 {
			m.reportHistory = m.reportHistory[len(m.reportHistory)-200:]
		}

		// 重置会话统计
		stats.SessionSentBytes = 0
		stats.SessionReceivedBytes = 0
		stats.SessionPromptTokens = 0
		stats.SessionCompletionTokens = 0
		stats.SessionExactPromptTokens = 0
		stats.SessionExactCompletionTokens = 0
	}
}

// estimateTokens 保留旧的估算函数作为兼容层（已由 AdaptiveTokenEstimator 替代）
func estimateTokens(b uint64, tokenRatio float64) uint64 {
	if b == 0 {
		return 0
	}
	tokens := uint64(float64(b) / tokenRatio)
	if tokens < 1 {
		tokens = 1
	}
	return tokens
}
