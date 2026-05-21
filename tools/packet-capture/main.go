package main

import (
	"ai-token-monitor/config"
	"ai-token-monitor/logger"
	"ai-token-monitor/monitor"
	"ai-token-monitor/server"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

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

	waitForShutdown()

	logrus.Info("Shutting down...")
	monitorManager.Stop()
	webServer.Stop()

	if rotateWriter != nil {
		_ = rotateWriter.Close()
	}
}

// setupLogger 配置 logrus 日志级别、格式，并启用每日轮转文件输出。
// 同时保留 stdout 输出（tee 模式）。
// 返回 rotateWriter 供 main 在退出时关闭。
func setupLogger(cfg *config.Config) (*logger.DailyRotateWriter, error) {
	// ── 1. 日志级别 ──────────────────────────────────────────────
	level, err := logrus.ParseLevel(cfg.Log.Level)
	if err != nil {
		level = logrus.InfoLevel
	}
	logrus.SetLevel(level)

	// ── 2. 日志格式：带颜色的文本格式（终端），写文件时禁用颜色 ──
	logrus.SetFormatter(&logrus.TextFormatter{
		FullTimestamp:   true,
		TimestampFormat: "2006-01-02 15:04:05",
		ForceColors:     false,
		DisableColors:   false,
	})

	// ── 3. 确定日志目录（优先级：Log.Dir > Log.File目录 > 默认./logs）──
	logDir := "./logs"
	if cfg.Log.Dir != "" {
		logDir = cfg.Log.Dir
	} else if cfg.Log.File != "" {
		// 兼容旧配置：取 file 字段的目录部分作为日志目录
		dir := filepath.Dir(cfg.Log.File)
		if dir != "" && dir != "." {
			logDir = dir
		}
	}
	prefix := "app"

	// ── 4. 创建每日轮转写入器 ─────────────────────────────────────
	rotateWriter, err := logger.NewDailyRotateWriter(logDir, prefix)
	if err != nil {
		// 写文件失败时退回纯 stdout
		logrus.SetOutput(os.Stdout)
		return nil, err
	}

	// ── 5. tee 模式：同时输出到文件和 stdout ─────────────────────
	tee := logger.NewTeeWriter(os.Stdout, rotateWriter)
	logrus.SetOutput(tee)

	return rotateWriter, nil
}

func waitForShutdown() {
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan
}
