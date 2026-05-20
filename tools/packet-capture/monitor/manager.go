package monitor

import (
	"ai-token-monitor/config"
	"ai-token-monitor/gateway"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
)

type Manager struct {
	config             *config.Config
	gateway            *gateway.Client
	stats              map[string]*AppStats
	processMonitor     *ProcessMonitor
	mu                 sync.RWMutex
	running            bool
	stopChan           chan struct{}
	gatewayFailCount   int
	gatewayLastLogTime time.Time
}

type AppStats struct {
	ToolName                string
	ProviderName            string
	ProcessNames            []string
	IsRunning               bool
	HasNetworkConn          bool
	RunningProcessNames     []string
	TotalSentBytes          uint64
	TotalReceivedBytes      uint64
	TotalPromptTokens       uint64
	TotalCompletionTokens   uint64
	SessionSentBytes        uint64
	SessionReceivedBytes    uint64
	SessionPromptTokens     uint64
	SessionCompletionTokens uint64
	LastUpdate              time.Time
}

func NewManager(cfg *config.Config) *Manager {
	return &Manager{
		config:         cfg,
		gateway:        gateway.NewClient(cfg),
		stats:          make(map[string]*AppStats),
		processMonitor: NewProcessMonitor(),
		stopChan:       make(chan struct{}),
	}
}

func (m *Manager) Start() {
	if m.running {
		return
	}
	m.running = true

	logrus.Info("Starting monitor manager...")

	for _, app := range m.config.MonitoredApps {
		m.stats[app.Name] = &AppStats{
			ToolName:     app.ToolName,
			ProviderName: app.ProviderName,
			ProcessNames: app.ProcessNames,
		}
		logrus.Infof("Monitoring app: %s (process: %v, token_ratio: %.1f, network_ratio: %.4f)",
			app.Name, app.ProcessNames, app.GetTokenRatio(), app.GetNetworkRatio())
	}

	go m.monitorLoop()
	go m.reportLoop()
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
				ToolName:     app.ToolName,
				ProviderName: app.ProviderName,
				ProcessNames: app.ProcessNames,
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
			tokenRatio := app.GetTokenRatio()

			networkSentBytes := uint64(float64(delta.SentDelta) * networkRatio)
			networkReceivedBytes := uint64(float64(delta.ReceivedDelta) * networkRatio)

			promptTokens := estimateTokens(networkSentBytes, tokenRatio)
			completionTokens := estimateTokens(networkReceivedBytes, tokenRatio)

			stats.TotalSentBytes += networkSentBytes
			stats.TotalReceivedBytes += networkReceivedBytes
			stats.TotalPromptTokens += promptTokens
			stats.TotalCompletionTokens += completionTokens

			stats.SessionSentBytes += networkSentBytes
			stats.SessionReceivedBytes += networkReceivedBytes
			stats.SessionPromptTokens += promptTokens
			stats.SessionCompletionTokens += completionTokens

			stats.LastUpdate = time.Now()

			logrus.Infof("[%s] IO delta: sent=%d, received=%d | network(%.2f%%): sent=%d, received=%d | tokens: prompt=%d, completion=%d",
				app.Name, delta.SentDelta, delta.ReceivedDelta, networkRatio*100,
				networkSentBytes, networkReceivedBytes, promptTokens, completionTokens)
		}
	}
}

func (m *Manager) GetStats() map[string]*AppStats {
	m.mu.RLock()
	defer m.mu.RUnlock()

	stats := make(map[string]*AppStats)
	for k, v := range m.stats {
		s := &AppStats{
			ToolName:                v.ToolName,
			ProviderName:            v.ProviderName,
			ProcessNames:            v.ProcessNames,
			IsRunning:               v.IsRunning,
			HasNetworkConn:          v.HasNetworkConn,
			RunningProcessNames:     v.RunningProcessNames,
			TotalSentBytes:          v.TotalSentBytes,
			TotalReceivedBytes:      v.TotalReceivedBytes,
			TotalPromptTokens:       v.TotalPromptTokens,
			TotalCompletionTokens:   v.TotalCompletionTokens,
			SessionSentBytes:        v.SessionSentBytes,
			SessionReceivedBytes:    v.SessionReceivedBytes,
			SessionPromptTokens:     v.SessionPromptTokens,
			SessionCompletionTokens: v.SessionCompletionTokens,
			LastUpdate:              v.LastUpdate,
		}
		if v.RunningProcessNames != nil {
			s.RunningProcessNames = make([]string, len(v.RunningProcessNames))
			copy(s.RunningProcessNames, v.RunningProcessNames)
		}
		stats[k] = s
	}
	return stats
}

func (m *Manager) RecordTraffic(appName string, sentBytes, receivedBytes uint64) {
	m.mu.Lock()
	defer m.mu.Unlock()

	stats, ok := m.stats[appName]
	if !ok {
		stats = &AppStats{
			ToolName: appName,
		}
		m.stats[appName] = stats
	}

	tokenRatio := 4.0
	for _, app := range m.config.MonitoredApps {
		if app.Name == appName {
			tokenRatio = app.GetTokenRatio()
			break
		}
	}

	promptTokens := estimateTokens(sentBytes, tokenRatio)
	completionTokens := estimateTokens(receivedBytes, tokenRatio)

	stats.TotalSentBytes += sentBytes
	stats.TotalReceivedBytes += receivedBytes
	stats.TotalPromptTokens += promptTokens
	stats.TotalCompletionTokens += completionTokens

	stats.SessionSentBytes += sentBytes
	stats.SessionReceivedBytes += receivedBytes
	stats.SessionPromptTokens += promptTokens
	stats.SessionCompletionTokens += completionTokens

	stats.LastUpdate = time.Now()

	logrus.Infof("[Manual] Recorded traffic for %s: sent=%d, received=%d, prompt_tokens=%d, completion_tokens=%d",
		appName, sentBytes, receivedBytes, promptTokens, completionTokens)
}

func (m *Manager) AddTraffic(appName string, sent, received uint64) {
	m.RecordTraffic(appName, sent, received)
}

func (m *Manager) UpdateConfig(cfg *config.Config) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.config = cfg

	appNames := make(map[string]bool)
	for _, app := range cfg.MonitoredApps {
		appNames[app.Name] = true
		if _, ok := m.stats[app.Name]; !ok {
			m.stats[app.Name] = &AppStats{
				ToolName:     app.ToolName,
				ProviderName: app.ProviderName,
				ProcessNames: app.ProcessNames,
			}
		} else {
			m.stats[app.Name].ToolName = app.ToolName
			m.stats[app.Name].ProviderName = app.ProviderName
			m.stats[app.Name].ProcessNames = app.ProcessNames
		}
	}

	for name := range m.stats {
		if !appNames[name] {
			delete(m.stats, name)
		}
	}
}

func (m *Manager) reportLoop() {
	interval := time.Duration(m.config.Gateway.GetReportInterval()) * time.Second
	logrus.Infof("Gateway report interval: %v", interval)

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.reportStats()
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

	for appName, stats := range m.stats {
		if stats.SessionPromptTokens == 0 && stats.SessionCompletionTokens == 0 {
			continue
		}

		report := &gateway.UsageItem{
			ToolName:         stats.ToolName,
			ProviderName:     stats.ProviderName,
			PromptTokens:     int(stats.SessionPromptTokens),
			CompletionTokens: int(stats.SessionCompletionTokens),
			Detail:           map[string]interface{}{"type": "session", "description": "Session traffic statistics"},
		}

		err := m.gateway.ReportUsage(report)
		if err != nil {
			m.gatewayFailCount++
			if time.Since(m.gatewayLastLogTime) >= 5*time.Minute || m.gatewayFailCount <= 1 {
				logrus.Warnf("Failed to report usage for %s: %v (consecutive failures: %d)", appName, err, m.gatewayFailCount)
				m.gatewayLastLogTime = time.Now()
			}
		} else {
			if m.gatewayFailCount > 0 {
				logrus.Infof("Gateway recovered after %d failures", m.gatewayFailCount)
				m.gatewayFailCount = 0
			}
			logrus.Infof("Reported usage for %s: prompt=%d, completion=%d",
				appName, stats.SessionPromptTokens, stats.SessionCompletionTokens)
		}

		stats.SessionSentBytes = 0
		stats.SessionReceivedBytes = 0
		stats.SessionPromptTokens = 0
		stats.SessionCompletionTokens = 0
	}
}

func estimateTokens(bytes uint64, tokenRatio float64) uint64 {
	if bytes == 0 {
		return 0
	}
	tokens := uint64(float64(bytes) / tokenRatio)
	if tokens < 1 {
		tokens = 1
	}
	return tokens
}
