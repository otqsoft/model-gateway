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

type MonitoredApp struct {
	Name           string   `yaml:"name" json:"name"`
	ToolName       string   `yaml:"tool_name" json:"tool_name"`
	ProviderName   string   `yaml:"provider_name" json:"provider_name"`
	ProcessNames   []string `yaml:"process_names" json:"process_names"`
	TokenRatio     float64  `yaml:"token_ratio" json:"token_ratio"`
	NetworkRatio   float64  `yaml:"network_ratio" json:"network_ratio"`
}

func (a *MonitoredApp) GetTokenRatio() float64 {
	if a.TokenRatio <= 0 {
		return 4.0
	}
	return a.TokenRatio
}

func (a *MonitoredApp) GetNetworkRatio() float64 {
	if a.NetworkRatio <= 0 {
		return 0.05
	}
	return a.NetworkRatio
}

type LogConfig struct {
	Level string `yaml:"level" json:"level"`
	File  string `yaml:"file" json:"file"`
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
