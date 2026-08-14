"""FastAPI application factory and production server entrypoint."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from .config import load_commercial_config
from .service import CommercialAPIError, CommercialService
from ..channels.wechat import WeChatChannelError, WeChatOfficialAccountChannel
from .setup import (
    SetupValidationError,
    apply_setup,
    authorize_setup,
    convert_setup,
    load_local_environment,
    public_catalog,
    remote_setup_allowed,
    setup_enabled,
)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str = Field(min_length=1, max_length=80)
    task: str = Field(min_length=1, max_length=160)
    input: Dict[str, Any] = Field(default_factory=dict)
    provider: Optional[str] = Field(default=None, max_length=40)
    model: Optional[str] = Field(default=None, max_length=160)


class ProviderSetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40)
    api_key: str = Field(default="", max_length=4096)
    base_url: str = Field(default="", max_length=2048)
    models: List[str] = Field(default_factory=list, max_length=3)


class FinanceSetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_mode: str = Field(default="fixture", max_length=20)
    tushare_token: str = Field(default="", max_length=4096)
    alphavantage_api_key: str = Field(default="", max_length=4096)
    fred_api_key: str = Field(default="", max_length=4096)
    wechat_enabled: bool = False
    wechat_token: str = Field(default="", max_length=4096)
    wechat_data_mode: str = Field(default="fixture", max_length=20)


class SetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1, max_length=80)
    customer_api_key: str = Field(default="", max_length=4096)
    allowed_tasks: List[str] = Field(default_factory=list, max_length=10)
    providers: List[ProviderSetupRequest] = Field(default_factory=list, max_length=30)
    default_provider: str = Field(default="local", max_length=40)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=100000)
    monthly_request_quota: int = Field(default=10000, ge=1, le=1000000000)
    finance: Optional[FinanceSetupRequest] = None


def create_app(config_path=None, service=None):
    path = config_path or os.environ.get(
        "VAF_COMMERCIAL_CONFIG", "config/commercial.yaml"
    )
    boot_error = None
    if service is None:
        try:
            service = CommercialService(load_commercial_config(path))
        except (OSError, ValueError) as exc:
            if not setup_enabled():
                raise
            boot_error = str(exc)
    maximum_request_bytes = int(os.environ.get("VAF_MAX_REQUEST_BYTES", "262144"))

    app = FastAPI(
        title="Vertical Agent Factory API",
        version="1.0.0",
        description="Tenant-aware commercial API for governed vertical agents.",
    )
    app.state.commercial_service = service
    app.state.commercial_boot_error = boot_error

    allowed_origins = [
        item.strip()
        for item in os.environ.get("VAF_SETUP_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    ]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.exception_handler(CommercialAPIError)
    async def commercial_error_handler(request, exc):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else {}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)
        if exc.request_id:
            headers["X-Request-ID"] = exc.request_id
        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": exc.request_id,
                }
            },
        )

    @app.exception_handler(SetupValidationError)
    async def setup_validation_error_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_setup", "messages": exc.errors}},
        )

    def current_tenant(authorization=Header(default=None)):
        if app.state.commercial_service is None:
            raise CommercialAPIError(
                503,
                "setup_required",
                "Commercial API setup is incomplete; finish the setup wizard and restart",
            )
        return app.state.commercial_service.authenticate(authorization)

    def setup_authorized(
        request: Request, authorization=Header(default=None)
    ):
        if not setup_enabled():
            raise CommercialAPIError(404, "not_found", "Not found")
        client_host = request.client.host if request.client else ""
        if not remote_setup_allowed(client_host):
            raise CommercialAPIError(
                403, "setup_remote_forbidden", "Setup API accepts local requests only"
            )
        if not authorize_setup(authorization):
            raise CommercialAPIError(
                401, "setup_unauthorized", "A valid setup administrator key is required"
            )
        return True

    @app.get("/v1/health", tags=["system"])
    def health():
        return {
            "status": "ok" if app.state.commercial_service is not None else "setup_required",
            "service": "vertical-agent-factory",
        }

    @app.get("/v1/setup/catalog", tags=["setup"])
    def setup_catalog():
        return {"providers": public_catalog()}

    @app.get("/v1/setup/status", tags=["setup"])
    def setup_status(authorized=Depends(setup_authorized)):
        return {
            "enabled": True,
            "configured": app.state.commercial_service is not None,
            "boot_error": app.state.commercial_boot_error,
            "config_path": str(Path(path).resolve()),
            "environment_path": str(
                Path(os.environ.get("VAF_SETUP_ENV_FILE", ".env")).resolve()
            ),
        }

    @app.post("/v1/setup/preview", tags=["setup"])
    def setup_preview(body: SetupRequest, authorized=Depends(setup_authorized)):
        converted = convert_setup(body.model_dump())
        return {
            key: value
            for key, value in converted.items()
            if key not in {"config", "secrets"}
        }

    @app.post("/v1/setup/apply", tags=["setup"])
    def setup_apply(body: SetupRequest, authorized=Depends(setup_authorized)):
        return apply_setup(
            body.model_dump(),
            path,
            os.environ.get("VAF_SETUP_ENV_FILE", ".env"),
        )

    def wechat_channel():
        if app.state.commercial_service is None:
            raise CommercialAPIError(503, "setup_required", "Commercial API setup is incomplete")
        token = os.environ.get("WECHAT_OFFICIAL_ACCOUNT_TOKEN", "")
        if len(token) < 16:
            raise CommercialAPIError(503, "wechat_not_configured", "WeChat Official Account token is not configured")
        return WeChatOfficialAccountChannel(app.state.commercial_service, token=token)

    @app.get("/v1/channels/wechat/official-account", tags=["channels"])
    def verify_wechat_callback(
        signature: str = "", timestamp: str = "", nonce: str = "", echostr: str = ""
    ):
        channel = wechat_channel()
        if not channel.verify(signature, timestamp, nonce):
            raise CommercialAPIError(403, "wechat_signature_invalid", "Invalid WeChat signature")
        return PlainTextResponse(echostr)

    @app.post("/v1/channels/wechat/official-account", tags=["channels"])
    async def receive_wechat_message(
        request: Request,
        signature: str = "",
        timestamp: str = "",
        nonce: str = "",
        encrypt_type: str = "",
    ):
        channel = wechat_channel()
        if encrypt_type and encrypt_type.lower() != "raw":
            raise CommercialAPIError(
                501,
                "wechat_encryption_not_enabled",
                "This deployment supports WeChat plaintext mode only",
            )
        if not channel.verify(signature, timestamp, nonce):
            raise CommercialAPIError(403, "wechat_signature_invalid", "Invalid WeChat signature")
        raw = await request.body()
        maximum_wechat_bytes = int(os.environ.get("VAF_WECHAT_MAX_REQUEST_BYTES", "65536"))
        if len(raw) > maximum_wechat_bytes:
            raise CommercialAPIError(413, "wechat_message_too_large", "WeChat message exceeds the configured limit")
        try:
            rendered = channel.handle(raw)
        except WeChatChannelError as exc:
            raise CommercialAPIError(400, "invalid_wechat_message", str(exc))
        return Response(content=rendered, media_type="application/xml")

    @app.get("/v1/models", tags=["models"])
    def models(tenant=Depends(current_tenant)):
        return app.state.commercial_service.models(tenant)

    @app.get("/v1/usage", tags=["billing"])
    def usage(tenant=Depends(current_tenant)):
        return app.state.commercial_service.usage_summary(tenant)

    @app.post("/v1/agent/runs", tags=["agents"])
    def run_agent(
        body: RunRequest,
        request: Request,
        tenant=Depends(current_tenant),
        idempotency_key=Header(default=None, alias="Idempotency-Key"),
    ):
        payload = body.model_dump()
        response = app.state.commercial_service.run(
            tenant, payload, idempotency_key=idempotency_key
        )
        request.state.request_id = response["request_id"]
        return response

    @app.middleware("http")
    async def request_id_header(request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > maximum_request_bytes
            except ValueError:
                too_large = True
            if too_large:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "request_too_large",
                            "message": "Request body exceeds the configured limit",
                            "request_id": None,
                        }
                    },
                )
        response = await call_next(request)
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response

    return app


def run():
    import uvicorn

    load_local_environment(os.environ.get("VAF_SETUP_ENV_FILE", ".env"))
    uvicorn.run(
        "vertical_agent_factory.commercial.app:create_app",
        factory=True,
        host=os.environ.get("VAF_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("VAF_API_PORT", "8000")),
        proxy_headers=False,
    )


if __name__ == "__main__":
    run()
