from __future__ import annotations

from domain.base import ToolError


class ProviderFailureError(Exception):
    def __init__(
        self,
        *,
        message: str = "Real provider failed",
        error_layer: str = "network",
        retryable: bool = True,
        detail: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.tool_error = ToolError(
            code="PROVIDER_FAILURE",
            message=message,
            retryable=retryable,
            error_layer=error_layer,
            detail=detail,
        )

