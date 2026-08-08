"""FastAPI application factory and production server entrypoint."""

import os
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import load_commercial_config
from .service import CommercialAPIError, CommercialService


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str = Field(min_length=1, max_length=80)
    task: str = Field(min_length=1, max_length=160)
    input: Dict[str, Any] = Field(default_factory=dict)
    provider: Optional[str] = Field(default=None, max_length=40)
    model: Optional[str] = Field(default=None, max_length=160)


def create_app(config_path=None, service=None):
    if service is None:
        path = config_path or os.environ.get(
            "VAF_COMMERCIAL_CONFIG", "config/commercial.yaml"
        )
        service = CommercialService(load_commercial_config(path))
    maximum_request_bytes = int(os.environ.get("VAF_MAX_REQUEST_BYTES", "262144"))

    app = FastAPI(
        title="Vertical Agent Factory API",
        version="1.0.0",
        description="Tenant-aware commercial API for governed vertical agents.",
    )
    app.state.commercial_service = service

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

    def current_tenant(authorization=Header(default=None)):
        return app.state.commercial_service.authenticate(authorization)

    @app.get("/v1/health", tags=["system"])
    def health():
        return {"status": "ok", "service": "vertical-agent-factory"}

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

    uvicorn.run(
        "vertical_agent_factory.commercial.app:create_app",
        factory=True,
        host=os.environ.get("VAF_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("VAF_API_PORT", "8000")),
        proxy_headers=False,
    )


if __name__ == "__main__":
    run()
