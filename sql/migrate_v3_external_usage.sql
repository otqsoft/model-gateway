-- ============================================================
-- 外部 Token 使用量上报表
-- 用于接收来自本地抓包程序、浏览器扩展等外部来源的 Token 统计
-- ============================================================

CREATE TABLE IF NOT EXISTS `external_usage` (
  `id`                BIGINT       UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `request_id`        CHAR(36)     NOT NULL COMMENT 'UUID，由上报端生成',
  `source`            VARCHAR(50)  NOT NULL COMMENT '来源标识：packet_capture / browser_ext / proxy / manual',
  `tool_name`         VARCHAR(100) NOT NULL COMMENT '工具名称：doubao / qianwen / cursor / trae 等',
  `provider_name`     VARCHAR(64)  NOT NULL COMMENT '厂商标识：doubao / qianwen / openai 等',
  `model_alias`       VARCHAR(128) NOT NULL DEFAULT '' COMMENT '模型名称',
  `prompt_tokens`     INT          NOT NULL DEFAULT 0 COMMENT '输入 token',
  `completion_tokens` INT          NOT NULL DEFAULT 0 COMMENT '输出 token',
  `total_tokens`      INT          NOT NULL DEFAULT 0 COMMENT '总 token',
  `input_price`       DECIMAL(12,6)NOT NULL DEFAULT 0.000000 COMMENT '输入单价快照（元/1K tokens）',
  `output_price`      DECIMAL(12,6)NOT NULL DEFAULT 0.000000 COMMENT '输出单价快照',
  `input_cost`        DECIMAL(14,8)NOT NULL DEFAULT 0.00000000 COMMENT '输入费用（元）',
  `output_cost`       DECIMAL(14,8)NOT NULL DEFAULT 0.00000000 COMMENT '输出费用（元）',
  `total_cost`        DECIMAL(14,8)NOT NULL DEFAULT 0.00000000 COMMENT '总费用（元）',
  `client_ip`         VARCHAR(64)           DEFAULT NULL COMMENT '上报端 IP',
  `detail`            JSON                  DEFAULT NULL COMMENT '原始请求/响应摘要（可选）',
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上报时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_request_id` (`request_id`),
  KEY `idx_source`       (`source`),
  KEY `idx_tool_name`    (`tool_name`),
  KEY `idx_provider`     (`provider_name`),
  KEY `idx_model`        (`model_alias`),
  KEY `idx_created_at`   (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='外部 Token 使用量上报';
