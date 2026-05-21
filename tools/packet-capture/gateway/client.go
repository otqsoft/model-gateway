package gateway

import (
	"ai-token-monitor/config"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
)

type Client struct {
	config *config.Config
	client *http.Client
}

type UsageItem struct {
	RequestID        string                 `json:"request_id"`
	ToolName         string                 `json:"tool_name"`
	ProviderName     string                 `json:"provider_name"`
	ModelAlias       string                 `json:"model_alias,omitempty"`
	PromptTokens     int                    `json:"prompt_tokens"`
	CompletionTokens int                    `json:"completion_tokens"`
	TotalTokens      int                    `json:"total_tokens,omitempty"`
	InputPrice       float64                `json:"input_price,omitempty"`
	OutputPrice      float64                `json:"output_price,omitempty"`
	Detail           map[string]interface{} `json:"detail,omitempty"`
}

type UsageReport struct {
	Source string      `json:"source"`
	Items  []UsageItem `json:"items"`
}

func NewClient(cfg *config.Config) *Client {
	return &Client{
		config: cfg,
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (c *Client) UpdateConfig(cfg *config.Config) {
	c.config = cfg
}

func (c *Client) ReportUsage(item *UsageItem) error {
	if !c.config.Gateway.Enabled {
		logrus.Debug("Gateway reporting disabled")
		return nil
	}

	item.RequestID = uuid.New().String()
	if item.TotalTokens == 0 {
		item.TotalTokens = item.PromptTokens + item.CompletionTokens
	}

	report := &UsageReport{
		Source: "packet_capture",
		Items:  []UsageItem{*item},
	}

	jsonData, err := json.Marshal(report)
	if err != nil {
		return fmt.Errorf("failed to marshal report: %w", err)
	}

	logrus.Debug("Sending usage report: %s", string(jsonData))

	req, err := http.NewRequest("POST", c.config.Gateway.URL, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Admin-Token", "KEY_OTQSOFT_MODEL_GATEWAY_888888")

	resp, err := c.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("unexpected status code: %d, response: %s", resp.StatusCode, string(body))
	}

	logrus.Infof("Successfully reported usage: request_id=%s, tool=%s", item.RequestID, item.ToolName)
	return nil
}
