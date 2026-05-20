package main

import (
	"ai-token-monitor/config"
	"ai-token-monitor/monitor"
	"ai-token-monitor/server"
	"os"
	"os/signal"
	"syscall"

	"github.com/sirupsen/logrus"
)

func main() {
	cfg, err := config.LoadConfig("config.yaml")
	if err != nil {
		logrus.Fatalf("Failed to load config: %v", err)
	}

	setupLogger(cfg)

	logrus.Info("Starting AI Token Monitor...")

	monitorManager := monitor.NewManager(cfg)
	go monitorManager.Start()

	webServer := server.NewServer(cfg, monitorManager)
	go webServer.Start()

	waitForShutdown()

	logrus.Info("Shutting down...")
	monitorManager.Stop()
	webServer.Stop()
}

func setupLogger(cfg *config.Config) {
	if cfg.Log.File != "" {
		_ = os.MkdirAll("logs", 0755)
		file, err := os.OpenFile(cfg.Log.File, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
		if err == nil {
			logrus.SetOutput(file)
		}
	}

	level, err := logrus.ParseLevel(cfg.Log.Level)
	if err == nil {
		logrus.SetLevel(level)
	}
}

func waitForShutdown() {
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan
}
