import logging
from collections.abc import Generator
from typing import Optional, Union

from dify_plugin import OAICompatLargeLanguageModel
from dify_plugin.config.logger_format import plugin_logger_handler
from dify_plugin.entities.model import ModelFeature
from dify_plugin.entities.model.llm import LLMMode, LLMResult
from dify_plugin.entities.model.message import PromptMessage, PromptMessageTool
from yarl import URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class ModelGatewayLargeLanguageModel(OAICompatLargeLanguageModel):
    """通过 OpenAI 兼容接口调用 model-gateway。"""

    def _invoke(
        self,
        model: str,
        credentials: dict,
        prompt_messages: list[PromptMessage],
        model_parameters: dict,
        tools: Optional[list[PromptMessageTool]] = None,
        stop: Optional[list[str]] = None,
        stream: bool = True,
        user: Optional[str] = None,
    ) -> Union[LLMResult, Generator]:
        self._add_custom_parameters(credentials)
        self._add_function_call(model, credentials)
        # 根据界面设置处理思考模式（默认不开启）
        self._apply_thinking_mode(credentials, model_parameters)
        return super()._invoke(
            model,
            credentials,
            prompt_messages,
            model_parameters,
            tools,
            stop,
            stream,
            user,
        )

    @staticmethod
    def _apply_thinking_mode(credentials: dict, model_parameters: dict) -> None:
        """
        根据界面上的 thinking_mode 设置控制思考模式。
        参数注入到 model_parameters 中，SDK 会通过 **model_parameters
        将其展开到 HTTP 请求体里。（credentials["extra_body"] 不会被 SDK 使用）
        """
        thinking_mode = bool(model_parameters.pop("thinking_mode", False))

        if thinking_mode:
            model_parameters["enable_thinking"] = True
            model_parameters["thinking"] = {"type": "enabled"}
            model_parameters["reasoning"] = True
            logger.debug("thinking_mode=True, model_parameters=%s", model_parameters)
        else:
            model_parameters["enable_thinking"] = False
            model_parameters["thinking"] = {"type": "disabled"}
            model_parameters["reasoning"] = False
            logger.debug("thinking_mode=False, model_parameters=%s", model_parameters)

    def validate_credentials(self, model: str, credentials: dict) -> None:
        self._add_custom_parameters(credentials)
        super().validate_credentials(model, credentials)

    @staticmethod
    def _add_custom_parameters(credentials: dict) -> None:
        base = (credentials.get("gateway_url") or "").strip().rstrip("/")
        if not base:
            raise ValueError("gateway_url is required")
        credentials["endpoint_url"] = str(URL(f"{base}/v1"))
        credentials["mode"] = LLMMode.CHAT.value

    def _add_function_call(self, model: str, credentials: dict) -> None:
        model_schema = self.get_model_schema(model, credentials)
        if model_schema and {
            ModelFeature.TOOL_CALL,
            ModelFeature.MULTI_TOOL_CALL,
        }.intersection(model_schema.features or []):
            credentials["function_calling_type"] = "tool_call"
            credentials["stream_function_calling"] = "supported"
