package server

import (
	"ai-token-monitor/config"
	"ai-token-monitor/monitor"
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

type Server struct {
	config  *config.Config
	monitor *monitor.Manager
	engine  *gin.Engine
	server  *http.Server
}

func NewServer(cfg *config.Config, m *monitor.Manager) *Server {
	gin.SetMode(gin.ReleaseMode)
	engine := gin.Default()

	s := &Server{
		config:  cfg,
		monitor: m,
		engine:  engine,
	}

	s.setupRoutes()
	return s
}

func (s *Server) setupRoutes() {
	s.engine.Static("/static", s.config.Server.WebRoot+"/static")
	s.engine.LoadHTMLGlob(s.config.Server.WebRoot + "/*.html")

	s.engine.GET("/", func(c *gin.Context) {
		c.HTML(http.StatusOK, "index.html", nil)
	})

	api := s.engine.Group("/api")
	{
		api.GET("/stats", s.getStats)
		api.GET("/config", s.getConfig)
		api.POST("/config", s.updateConfig)
		api.POST("/test/traffic", s.addTestTraffic)
		api.GET("/report-history", s.getReportHistory)
		// 精确Token上报接口：由外部代理/插件在获取到真实token数时调用
		api.POST("/usage/exact", s.recordExactUsage)
		// 协议分析接口：直接上传HTTP响应体进行token解析
		api.POST("/usage/parse", s.parseHTTPPayload)
	}
}

func (s *Server) Start() {
	addr := fmt.Sprintf(":%d", s.config.Server.Port)
	s.server = &http.Server{
		Addr:    addr,
		Handler: s.engine,
	}

	logrus.Infof("Web server starting on %s", addr)
	if err := s.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logrus.Fatalf("Failed to start server: %v", err)
	}
}

func (s *Server) Stop() {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := s.server.Shutdown(ctx); err != nil {
		logrus.Errorf("Server shutdown error: %v", err)
	}
}

func (s *Server) getStats(c *gin.Context) {
	stats := s.monitor.GetStats()
	gatewayStats := s.monitor.GetGatewayStats()
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    stats,
		"gateway": gatewayStats,
	})
}

func (s *Server) getConfig(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    s.config,
	})
}

func (s *Server) updateConfig(c *gin.Context) {
	var newConfig config.Config
	if err := c.ShouldBindJSON(&newConfig); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	if err := config.SaveConfig("config.yaml", &newConfig); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	s.config = &newConfig
	s.monitor.UpdateConfig(&newConfig)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "Config updated successfully",
	})
}

func (s *Server) addTestTraffic(c *gin.Context) {
	var req struct {
		AppName       string `json:"app_name" binding:"required"`
		SentBytes     uint64 `json:"sent_bytes"`
		ReceivedBytes uint64 `json:"received_bytes"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	s.monitor.RecordTraffic(req.AppName, req.SentBytes, req.ReceivedBytes)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": fmt.Sprintf("Added traffic for %s: sent=%d, received=%d", req.AppName, req.SentBytes, req.ReceivedBytes),
	})
}

func (s *Server) getReportHistory(c *gin.Context) {
	history := s.monitor.GetReportHistory()
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    history,
	})
}

// recordExactUsage 接收来自外部（浏览器插件、代理脚本等）上报的精确token数
// 这是精度最高的数据来源，会同时校准自适应估算器
func (s *Server) recordExactUsage(c *gin.Context) {
	var req struct {
		AppName          string  `json:"app_name" binding:"required"`
		PromptTokens     uint64  `json:"prompt_tokens"`
		CompletionTokens uint64  `json:"completion_tokens"`
		TotalTokens      uint64  `json:"total_tokens"`
		ModelName        string  `json:"model_name"`
		SentBytes        uint64  `json:"sent_bytes"`
		ReceivedBytes    uint64  `json:"received_bytes"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "error": err.Error()})
		return
	}

	usage := &monitor.TokenUsage{
		PromptTokens:     req.PromptTokens,
		CompletionTokens: req.CompletionTokens,
		TotalTokens:      req.TotalTokens,
		ModelName:        req.ModelName,
	}
	if usage.TotalTokens == 0 {
		usage.TotalTokens = usage.PromptTokens + usage.CompletionTokens
	}

	s.monitor.RecordExactTokenUsage(req.AppName, req.SentBytes, req.ReceivedBytes, usage)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": fmt.Sprintf("Recorded exact usage for %s: prompt=%d, completion=%d",
			req.AppName, req.PromptTokens, req.CompletionTokens),
	})
}

// parseHTTPPayload 接收原始HTTP响应体，尝试解析其中的token用量
// 适用于代理脚本转发的明文HTTP响应
func (s *Server) parseHTTPPayload(c *gin.Context) {
	var req struct {
		AppName  string `json:"app_name" binding:"required"`
		Payload  []byte `json:"payload"`   // base64编码的原始HTTP响应
		RawJSON  string `json:"raw_json"`  // 或者直接传JSON字符串
		SentBytes     uint64 `json:"sent_bytes"`
		ReceivedBytes uint64 `json:"received_bytes"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"success": false, "error": err.Error()})
		return
	}

	parser := monitor.NewProtocolParser()
	var usage *monitor.TokenUsage

	if len(req.Payload) > 0 {
		usage = parser.TryParseHTTPResponse(req.Payload)
		if usage == nil {
			usage = parser.TryParseRawPayload(req.Payload)
		}
	} else if req.RawJSON != "" {
		usage = parser.TryParseRawPayload([]byte(req.RawJSON))
	}

	if usage == nil {
		c.JSON(http.StatusOK, gin.H{
			"success": false,
			"message": "No token usage found in payload",
		})
		return
	}

	s.monitor.RecordExactTokenUsage(req.AppName, req.SentBytes, req.ReceivedBytes, usage)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"usage": gin.H{
			"prompt_tokens":     usage.PromptTokens,
			"completion_tokens": usage.CompletionTokens,
			"total_tokens":      usage.TotalTokens,
			"model":             usage.ModelName,
			"source":            usage.Source.String(),
		},
	})
}
