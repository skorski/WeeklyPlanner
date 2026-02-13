"""Azure OpenAI client setup and authentication."""

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from openai import AzureOpenAI, APIError, AuthenticationError, APIConnectionError


class ImageGenConfigError(Exception):
    """Raised when credentials or configuration are missing or invalid."""


class ImageGenAuthError(Exception):
    """Raised when Azure OpenAI rejects the provided credentials."""


class ImageGenAPIError(Exception):
    """Raised when an Azure OpenAI API call fails."""


def _find_env_file() -> Path | None:
    """Locate .env file in the skill directory."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return None


def _load_env():
    """Load environment variables from .env file."""
    env_file = _find_env_file()
    if env_file:
        load_dotenv(env_file)


def _validate_endpoint(endpoint: str) -> str:
    """Validate the Azure OpenAI endpoint URL format."""
    if not endpoint.startswith("https://"):
        raise ImageGenConfigError(
            f"AZURE_OPENAI_ENDPOINT must start with 'https://'. Got: '{endpoint}'\n"
            f"Expected format: https://YOUR-RESOURCE.openai.azure.com/"
        )
    if "YOUR-RESOURCE" in endpoint or "your-" in endpoint.lower():
        raise ImageGenConfigError(
            f"AZURE_OPENAI_ENDPOINT still contains placeholder values: '{endpoint}'\n"
            f"Replace with your actual Azure OpenAI resource URL from the Azure portal.\n"
            f"Find it at: Azure Portal > Your OpenAI Resource > Keys and Endpoint"
        )
    return endpoint.rstrip("/")


def _validate_api_key(api_key: str):
    """Validate the API key is not a placeholder."""
    placeholders = {"your-api-key-here", "your-key", "sk-", ""}
    if api_key.lower().strip() in placeholders:
        raise ImageGenConfigError(
            "AZURE_OPENAI_API_KEY contains a placeholder value.\n"
            "Set it to your actual API key from the Azure portal.\n"
            "Find it at: Azure Portal > Your OpenAI Resource > Keys and Endpoint > Key 1 or Key 2"
        )


@lru_cache(maxsize=1)
def get_client() -> AzureOpenAI:
    """Get a cached Azure OpenAI client instance.

    Reads credentials from .env in the skill directory or from
    environment variables:
      - AZURE_OPENAI_ENDPOINT
      - AZURE_OPENAI_API_KEY
      - AZURE_OPENAI_API_VERSION (default: 2024-06-01)

    Raises:
        ImageGenConfigError: When credentials are missing, malformed, or contain placeholders.
    """
    _load_env()

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-06-01").strip()

    env_file = _find_env_file()
    env_location = f" in {env_file}" if env_file else " as environment variables"

    if not endpoint:
        raise ImageGenConfigError(
            f"AZURE_OPENAI_ENDPOINT is not set.\n"
            f"Set it{env_location} to your Azure OpenAI resource URL.\n"
            f"Example: AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/\n"
            f"Find it at: Azure Portal > Your OpenAI Resource > Keys and Endpoint"
        )
    if not api_key:
        raise ImageGenConfigError(
            f"AZURE_OPENAI_API_KEY is not set.\n"
            f"Set it{env_location} to your Azure OpenAI API key.\n"
            f"Find it at: Azure Portal > Your OpenAI Resource > Keys and Endpoint > Key 1 or Key 2"
        )

    _validate_endpoint(endpoint)
    _validate_api_key(api_key)

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )


def get_image_deployment() -> str:
    """Get the image generation model deployment name."""
    _load_env()
    deployment = os.environ.get("AZURE_OPENAI_IMAGE_DEPLOYMENT", "dall-e-3").strip()
    if not deployment:
        raise ImageGenConfigError(
            "AZURE_OPENAI_IMAGE_DEPLOYMENT is empty. Set it to your DALL-E 3 deployment name.\n"
            "Find it at: Azure Portal > Your OpenAI Resource > Model deployments"
        )
    return deployment


def get_chat_deployment() -> str:
    """Get the chat/vision model deployment name."""
    _load_env()
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o").strip()
    if not deployment:
        raise ImageGenConfigError(
            "AZURE_OPENAI_CHAT_DEPLOYMENT is empty. Set it to your GPT-4o deployment name.\n"
            "Find it at: Azure Portal > Your OpenAI Resource > Model deployments"
        )
    return deployment


def handle_api_error(error: Exception, operation: str) -> Exception:
    """Translate openai SDK exceptions into descriptive ImageGen errors.

    Args:
        error: The original exception from the openai SDK.
        operation: Human-readable description of what was being attempted.

    Returns:
        An ImageGenAuthError or ImageGenAPIError with actionable message.
    """
    if isinstance(error, AuthenticationError):
        return ImageGenAuthError(
            f"Authentication failed during {operation}.\n"
            f"Your API key was rejected by Azure OpenAI. Possible causes:\n"
            f"  - The API key is incorrect or has been rotated\n"
            f"  - The API key does not have access to this resource\n"
            f"  - The Azure OpenAI resource has been deleted or disabled\n"
            f"Check your credentials at: Azure Portal > Your OpenAI Resource > Keys and Endpoint\n"
            f"Original error: {error}"
        )

    if isinstance(error, APIConnectionError):
        return ImageGenAPIError(
            f"Connection failed during {operation}.\n"
            f"Could not reach the Azure OpenAI endpoint. Possible causes:\n"
            f"  - The endpoint URL is incorrect\n"
            f"  - Network connectivity issues or firewall blocking the request\n"
            f"  - The Azure OpenAI resource is in a different region or has been deleted\n"
            f"Verify AZURE_OPENAI_ENDPOINT is correct and the resource is accessible.\n"
            f"Original error: {error}"
        )

    if isinstance(error, APIError):
        status = getattr(error, "status_code", None)
        body = getattr(error, "body", None)
        inner_code = None
        inner_message = str(error)
        if isinstance(body, dict):
            inner_error = body.get("error", {})
            inner_code = inner_error.get("code", "")
            inner_message = inner_error.get("message", str(error))

        if status == 401:
            return ImageGenAuthError(
                f"Authentication failed (HTTP 401) during {operation}.\n"
                f"Your API key was rejected. Verify it at: Azure Portal > Keys and Endpoint\n"
                f"Detail: {inner_message}"
            )

        if status == 403:
            return ImageGenAuthError(
                f"Access denied (HTTP 403) during {operation}.\n"
                f"Your API key does not have permission for this operation.\n"
                f"Ensure the key has access to the deployment and the resource allows this model.\n"
                f"Detail: {inner_message}"
            )

        if status == 404:
            return ImageGenAPIError(
                f"Deployment not found (HTTP 404) during {operation}.\n"
                f"The model deployment does not exist in your Azure OpenAI resource.\n"
                f"Check AZURE_OPENAI_IMAGE_DEPLOYMENT and AZURE_OPENAI_CHAT_DEPLOYMENT in .env.\n"
                f"List your deployments at: Azure Portal > Your OpenAI Resource > Model deployments\n"
                f"Detail: {inner_message}"
            )

        if status == 429:
            return ImageGenAPIError(
                f"Rate limit exceeded (HTTP 429) during {operation}.\n"
                f"You've sent too many requests. DALL-E 3 allows ~6 images/minute.\n"
                f"Wait a moment and try again, or request a quota increase in the Azure portal.\n"
                f"Detail: {inner_message}"
            )

        if inner_code == "content_filter" or "content_policy" in inner_message.lower():
            return ImageGenAPIError(
                f"Content policy violation during {operation}.\n"
                f"The prompt was rejected by Azure's content safety filters.\n"
                f"Modify the prompt to avoid restricted content and try again.\n"
                f"Detail: {inner_message}"
            )

        if inner_code == "billing_hard_limit_reached":
            return ImageGenAPIError(
                f"Billing limit reached during {operation}.\n"
                f"Your Azure OpenAI resource has hit its spending cap.\n"
                f"Increase the limit at: Azure Portal > Your OpenAI Resource > Pricing\n"
                f"Detail: {inner_message}"
            )

        return ImageGenAPIError(
            f"Azure OpenAI API error during {operation} (HTTP {status}).\n"
            f"Detail: {inner_message}"
        )

    # Unknown error type — wrap with context
    return ImageGenAPIError(
        f"Unexpected error during {operation}: {type(error).__name__}: {error}"
    )
