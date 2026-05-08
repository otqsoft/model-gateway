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
