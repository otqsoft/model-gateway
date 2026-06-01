package main

import (
	"ai-token-monitor/config"
	"ai-token-monitor/logger"
	"ai-token-monitor/monitor"
	"ai-token-monitor/server"
	"ai-token-monitor/tray"
	"os"
	"path/filepath"

	"github.com/sirupsen/logrus"
)

func main() {
	cfg, err := config.LoadConfig("config.yaml")
	if err != nil {
		logrus.Fatalf("Failed to load config: %v", err)
	}

	rotateWriter, err := setupLogger(cfg)
	if err != nil {
		logrus.Warnf("Logger setup warning: %v (falling back to stdout)", err)
	}

	logrus.Infof("Starting AI Token Monitor... (log: %s)", func() string {
		if rotateWriter != nil {
			return rotateWriter.CurrentFile()
		}
		return "stdout"
	}())

	monitorManager := monitor.NewManager(cfg)
	go monitorManager.Start()

	webServer := server.NewServer(cfg, monitorManager)
	go webServer.Start()

	t := tray.NewTray(cfg.Server.Port)
	t.Run(func() {
		logrus.Info("Shutting down...")
		monitorManager.Stop()
		webServer.Stop()

		if rotateWriter != nil {
			_ = rotateWriter.Close()
		}
	})
}

func setupLogger(cfg *config.Config) (*logger.DailyRotateWriter, error) {
	level, err := logrus.ParseLevel(cfg.Log.Level)
	if err != nil {
		level = logrus.InfoLevel
	}
	logrus.SetLevel(level)

	logrus.SetFormatter(&logrus.TextFormatter{
		FullTimestamp:   true,
		TimestampFormat: "2006-01-02 15:04:05",
		ForceColors:     false,
		DisableColors:   false,
	})

	logDir := "./logs"
	if cfg.Log.Dir != "" {
		logDir = cfg.Log.Dir
	} else if cfg.Log.File != "" {
		dir := filepath.Dir(cfg.Log.File)
		if dir != "" && dir != "." {
			logDir = dir
		}
	}
	prefix := "app"

	rotateWriter, err := logger.NewDailyRotateWriter(logDir, prefix)
	if err != nil {
		logrus.SetOutput(os.Stdout)
		return nil, err
	}

	tee := logger.NewTeeWriter(os.Stdout, rotateWriter)
	logrus.SetOutput(tee)

	return rotateWriter, nil
}
