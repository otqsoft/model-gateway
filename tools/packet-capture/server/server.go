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
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    stats,
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
