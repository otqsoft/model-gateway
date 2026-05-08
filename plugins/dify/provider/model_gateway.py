import logging
from typing import Mapping

import httpx
from dify_plugin import ModelProvider
from dify_plugin.errors.model import CredentialsValidateFailedError

logger = logging.getLogger(__name__)


class ModelGatewayProvider(ModelProvider):
    """校验 model-gateway 是否可达（GET /v1/models）。"""

    def validate_provider_credentials(self, credentials: Mapping) -> None:
        creds = dict(credentials)
        gateway_url = (creds.get("gateway_url") or "").strip().rstrip("/")
        api_key = (creds.get("api_key") or "").strip()

        if not gateway_url:
            raise CredentialsValidateFailedError("Gateway base URL is required")
        if not api_key:
            raise CredentialsValidateFailedError("API Key is required")
        if not gateway_url.startswith(("http://", "https://")):
            raise CredentialsValidateFailedError("Gateway URL must start with http:// or https://")

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{gateway_url}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
        except httpx.ConnectError as e:
            logger.exception("model-gateway connect failed")
            raise CredentialsValidateFailedError(f"Cannot connect to gateway: {e}") from e
        except httpx.TimeoutException as e:
            raise CredentialsValidateFailedError("Gateway connection timeout") from e
        except Exception as e:
            logger.exception("model-gateway validate failed")
            raise CredentialsValidateFailedError(str(e)) from e

        if resp.status_code == 401:
            raise CredentialsValidateFailedError("Invalid API Key (HTTP 401)")
        if resp.status_code != 200:
            raise CredentialsValidateFailedError(
                f"Gateway returned HTTP {resp.status_code}: {resp.text[:200]}"
            )
