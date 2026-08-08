"""Tenant-aware service layer behind the public HTTP API."""

import hashlib
import hmac
import json
import threading
import time
import uuid
from collections import defaultdict, deque

from ..errors import ApprovalRequired, AgentFactoryError
from ..model_handlers import make_research_synthesis_handler
from ..model_providers import ModelGateway
from ..runtime import AgentRuntime
from .usage import UsageStore


class CommercialAPIError(Exception):
    def __init__(self, status_code, code, message, retry_after=None, request_id=None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retry_after = retry_after
        self.request_id = request_id
        super().__init__(message)


class MinuteRateLimiter(object):
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, tenant_id, limit):
        now = time.monotonic()
        with self._lock:
            events = self._events[tenant_id]
            while events and now - events[0] >= 60:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(60 - (now - events[0])))
                raise CommercialAPIError(
                    429, "rate_limit_exceeded", "Request rate limit exceeded", retry_after
                )
            events.append(now)


class CommercialService(object):
    def __init__(self, config, usage_store=None, model_gateway=None, rate_limiter=None):
        self.config = config
        for tenant in config.tenants:
            configured_key = tenant.api_key()
            if not configured_key:
                raise ValueError(
                    "API key environment variable {} is not set".format(
                        tenant.api_key_env
                    )
                )
            if len(configured_key) < 32:
                raise ValueError(
                    "API key for tenant {} must be at least 32 characters".format(
                        tenant.tenant_id
                    )
                )
        self.usage = usage_store or UsageStore(config.database_path)
        self.model_gateway = model_gateway or ModelGateway(config.provider_api_keys())
        self.rate_limiter = rate_limiter or MinuteRateLimiter()

    def authenticate(self, authorization):
        scheme, separator, supplied = (authorization or "").partition(" ")
        if not separator or scheme.lower() != "bearer" or not supplied:
            raise CommercialAPIError(401, "unauthorized", "A Bearer API key is required")
        matched = None
        for tenant in self.config.tenants:
            configured = tenant.api_key()
            if configured and hmac.compare_digest(configured, supplied):
                matched = tenant
        if matched is None:
            raise CommercialAPIError(401, "unauthorized", "Invalid API key")
        return matched

    def models(self, tenant):
        return {
            "default_provider": tenant.default_provider,
            "providers": [
                {
                    "id": provider,
                    "models": list(tenant.allowed_models.get(provider) or []),
                    "default_model": tenant.default_models.get(provider),
                }
                for provider in tenant.allowed_providers
            ],
        }

    def usage_summary(self, tenant):
        summary = self.usage.summary(tenant.tenant_id)
        summary.update(
            {
                "month": time.strftime("%Y-%m", time.gmtime()),
                "request_quota": tenant.monthly_request_quota,
                "requests_remaining": max(
                    0, tenant.monthly_request_quota - summary["requests"]
                ),
            }
        )
        return summary

    def run(self, tenant, payload, idempotency_key=None):
        request_hash = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if idempotency_key:
            if len(idempotency_key) > 128:
                raise CommercialAPIError(
                    400, "invalid_idempotency_key", "Idempotency key is too long"
                )
            cached = self.usage.idempotent_response(tenant.tenant_id, idempotency_key)
            if cached:
                cached_hash, response = cached
                if not hmac.compare_digest(cached_hash, request_hash):
                    raise CommercialAPIError(
                        409,
                        "idempotency_conflict",
                        "Idempotency key was already used for a different request",
                    )
                response["idempotent_replay"] = True
                return response

        self.rate_limiter.check(tenant.tenant_id, tenant.rate_limit_per_minute)
        if self.usage.request_count(tenant.tenant_id) >= tenant.monthly_request_quota:
            raise CommercialAPIError(429, "quota_exceeded", "Monthly request quota exceeded")

        domain = payload.get("domain")
        task = payload.get("task")
        if domain not in tenant.allowed_domains:
            raise CommercialAPIError(403, "domain_forbidden", "Domain is not enabled")
        if task not in tenant.allowed_tasks:
            raise CommercialAPIError(403, "task_forbidden", "Task is not enabled")

        provider, model = self._select_model(tenant, payload)
        request_id = str(uuid.uuid4())
        started = time.monotonic()
        captured_usage = {}
        handlers = {}
        if provider != "local":
            if task != "research.answer.query":
                raise CommercialAPIError(
                    400,
                    "provider_not_supported_for_task",
                    "Selected model provider is not supported for this task",
                )

            def capture(result):
                captured_usage.update(result.usage())

            handlers["research_answer_synthesize"] = make_research_synthesis_handler(
                self.model_gateway, provider, model, usage_sink=capture
            )

        approvals = {item: True for item in tenant.approved_capabilities}
        status = "SUCCESS"
        try:
            runtime = AgentRuntime(
                self.config.project_root,
                domain,
                handlers=handlers,
                approvals=approvals,
            )
            result = runtime.run(task, payload.get("input") or {})
            response = {
                "request_id": request_id,
                "tenant_id": tenant.tenant_id,
                "provider": provider,
                "model": model,
                "usage": captured_usage
                or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "result": result,
                "idempotent_replay": False,
            }
        except ApprovalRequired as exc:
            status = "APPROVAL_REQUIRED"
            raise CommercialAPIError(
                409,
                "approval_required",
                "Approval required for {}".format(exc.capability),
                request_id=request_id,
            )
        except AgentFactoryError:
            status = "ERROR"
            raise CommercialAPIError(
                502,
                "agent_execution_failed",
                "Agent execution failed",
                request_id=request_id,
            )
        finally:
            latency_ms = int((time.monotonic() - started) * 1000)
            self.usage.record(
                request_id,
                tenant.tenant_id,
                provider,
                model or "",
                status,
                captured_usage,
                latency_ms,
            )
        if idempotency_key:
            self.usage.save_idempotent_response(
                tenant.tenant_id, idempotency_key, request_hash, response
            )
        return response

    @staticmethod
    def _select_model(tenant, payload):
        provider = payload.get("provider") or tenant.default_provider
        if provider not in tenant.allowed_providers:
            raise CommercialAPIError(403, "provider_forbidden", "Provider is not enabled")
        if provider == "local":
            if payload.get("model"):
                raise CommercialAPIError(
                    400, "invalid_model", "Local provider does not accept a model"
                )
            return provider, None
        allowed = list(tenant.allowed_models.get(provider) or [])
        model = payload.get("model") or tenant.default_models.get(provider)
        if not model:
            raise CommercialAPIError(400, "model_required", "A model is required")
        if model not in allowed:
            raise CommercialAPIError(403, "model_forbidden", "Model is not enabled")
        return provider, model
