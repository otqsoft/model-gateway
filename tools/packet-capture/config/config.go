package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server        ServerConfig   `yaml:"server" json:"server"`
	Gateway       GatewayConfig  `yaml:"gateway" json:"gateway"`
	MonitoredApps []MonitoredApp `yaml:"monitored_apps" json:"monitored_apps"`
	Log           LogConfig      `yaml:"log" json:"log"`
}

type ServerConfig struct {
	Port    int    `yaml:"port" json:"port"`
	WebRoot string `yaml:"web_root" json:"web_root"`
}

type GatewayConfig struct {
	URL            string `yaml:"url" json:"url"`
	Enabled        bool   `yaml:"enabled" json:"enabled"`
	ReportInterval int    `yaml:"report_interval" json:"report_interval"`
}

func (g *GatewayConfig) GetReportInterval() int {
	if g.ReportInterval <= 0 {
		return 10
	}
	return g.ReportInterval
}

// MonitoredApp 被监控的AI应用配置
type MonitoredApp struct {
	Name         string   `yaml:"name" json:"name"`
	ToolName     string   `yaml:"tool_name" json:"tool_name"`
	ProviderName string   `yaml:"provider_name" json:"provider_name"`
	ProcessNames []string `yaml:"process_names" json:"process_names"`
	// NetworkRatio: 该进程总IO流量中属于AI API调用的估算比例（0.0~1.0）
	// 用于从进程级IO计数中过滤出AI相关流量。
	// 精确token计数由协议解析器独立处理，与此比例无关。
	NetworkRatio float64 `yaml:"network_ratio" json:"network_ratio"`
	// TokenRatio: 已废弃，保留字段为向后兼容（解析时不报错）
	// Token估算现在由 AdaptiveTokenEstimator 动态调整
	TokenRatio float64 `yaml:"token_ratio,omitempty" json:"token_ratio,omitempty"`
}

// GetTokenRatio 已废弃的兼容方法，返回固定默认值
func (a *MonitoredApp) GetTokenRatio() float64 {
	return 4.0
}

func (a *MonitoredApp) GetNetworkRatio() float64 {
	if a.NetworkRatio <= 0 {
		return 0.05
	}
	return a.NetworkRatio
}

type LogConfig struct {
	Level string `yaml:"level" json:"level"`
	// Dir: 日志目录，每天自动生成 app-YYYY-MM-DD.log。
	// 优先级高于 File 字段。若不配置则默认使用 ./logs/。
	Dir string `yaml:"dir" json:"dir"`
	// File: 已废弃，仅保留兼容旧配置，其目录部分会被用作日志目录。
	File string `yaml:"file,omitempty" json:"file,omitempty"`
}

func LoadConfig(filePath string) (*Config, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}

func SaveConfig(filePath string, cfg *Config) error {
	data, err := yaml.Marshal(cfg)
	if err != nil {
		return err
	}

	return os.WriteFile(filePath, data, 0644)
}
