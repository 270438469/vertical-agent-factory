"""Validated tenant and provider configuration for the commercial API."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..model_providers import CHINA_OPENAI_COMPATIBLE_PROVIDERS, PROVIDER_TYPES


class CommercialConfigError(ValueError):
    pass


@dataclass
class TenantConfig:
    tenant_id: str
    api_key_env: str
    allowed_domains: list
    allowed_tasks: list
    allowed_providers: list
    default_provider: str = "local"
    allowed_models: dict = field(default_factory=dict)
    default_models: dict = field(default_factory=dict)
    approved_capabilities: list = field(default_factory=list)
    rate_limit_per_minute: int = 60
    monthly_request_quota: int = 10000

    def api_key(self):
        return os.environ.get(self.api_key_env, "")


@dataclass
class CommercialConfig:
    project_root: Path
    database_path: Path
    provider_key_envs: dict
    tenants: list
    provider_base_url_envs: dict = field(default_factory=dict)

    def provider_api_keys(self):
        return {
            provider: os.environ.get(environment_name, "")
            for provider, environment_name in self.provider_key_envs.items()
        }

    def provider_base_urls(self):
        return {
            provider: os.environ.get(environment_name, "")
            for provider, environment_name in self.provider_base_url_envs.items()
            if os.environ.get(environment_name)
        }


def _required(mapping, key, context):
    value = mapping.get(key)
    if value in (None, "", []):
        raise CommercialConfigError("{} requires {}".format(context, key))
    return value


def load_commercial_config(path):
    config_path = Path(path).resolve()
    if not config_path.exists():
        raise CommercialConfigError("Commercial config not found: {}".format(config_path))
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    project_root_value = data.get("project_root", "..")
    project_root = (config_path.parent / project_root_value).resolve()
    database_value = data.get("database_path", ".commercial/usage.sqlite3")
    database_path = (project_root / database_value).resolve()
    provider_key_envs = {}
    provider_base_url_envs = {}
    for provider, provider_data in (data.get("providers") or {}).items():
        if (
            provider not in PROVIDER_TYPES
            and provider not in CHINA_OPENAI_COMPATIBLE_PROVIDERS
        ):
            raise CommercialConfigError("Unsupported provider id: {}".format(provider))
        provider_key_envs[provider] = _required(
            provider_data or {}, "api_key_env", "provider {}".format(provider)
        )
        if (provider_data or {}).get("base_url_env"):
            provider_base_url_envs[provider] = provider_data["base_url_env"]

    tenants = []
    seen = set()
    for raw in data.get("tenants") or []:
        tenant_id = _required(raw, "id", "tenant")
        if tenant_id in seen:
            raise CommercialConfigError("Duplicate tenant id: {}".format(tenant_id))
        seen.add(tenant_id)
        allowed_providers = list(raw.get("allowed_providers") or ["local"])
        default_provider = raw.get("default_provider", "local")
        allowed_models = dict(raw.get("allowed_models") or {})
        default_models = dict(raw.get("default_models") or {})
        if default_provider not in allowed_providers:
            raise CommercialConfigError(
                "Tenant {} default_provider is not allowed".format(tenant_id)
            )
        tenant = TenantConfig(
            tenant_id=tenant_id,
            api_key_env=_required(raw, "api_key_env", "tenant {}".format(tenant_id)),
            allowed_domains=list(
                _required(raw, "allowed_domains", "tenant {}".format(tenant_id))
            ),
            allowed_tasks=list(
                _required(raw, "allowed_tasks", "tenant {}".format(tenant_id))
            ),
            allowed_providers=allowed_providers,
            default_provider=default_provider,
            allowed_models=allowed_models,
            default_models=default_models,
            approved_capabilities=list(raw.get("approved_capabilities") or []),
            rate_limit_per_minute=int(raw.get("rate_limit_per_minute", 60)),
            monthly_request_quota=int(raw.get("monthly_request_quota", 10000)),
        )
        if tenant.rate_limit_per_minute < 1 or tenant.monthly_request_quota < 1:
            raise CommercialConfigError(
                "Tenant {} limits must be positive".format(tenant_id)
            )
        for provider in tenant.allowed_providers:
            if provider != "local" and provider not in provider_key_envs:
                raise CommercialConfigError(
                    "Tenant {} references unconfigured provider {}".format(
                        tenant_id, provider
                    )
                )
            if provider == "local":
                continue
            models = tenant.allowed_models.get(provider)
            if not isinstance(models, list) or not models:
                raise CommercialConfigError(
                    "Tenant {} provider {} requires allowed_models".format(
                        tenant_id, provider
                    )
                )
            if len(models) > 3:
                raise CommercialConfigError(
                    "Tenant {} provider {} allows at most three model tiers".format(
                        tenant_id, provider
                    )
                )
            if any(not isinstance(model, str) or not model.strip() for model in models):
                raise CommercialConfigError(
                    "Tenant {} provider {} model ids must be non-empty strings".format(
                        tenant_id, provider
                    )
                )
            if len(models) != len(set(models)):
                raise CommercialConfigError(
                    "Tenant {} provider {} contains duplicate models".format(
                        tenant_id, provider
                    )
                )
            if tenant.default_models.get(provider) != models[0]:
                raise CommercialConfigError(
                    "Tenant {} provider {} default_model must be the first tier".format(
                        tenant_id, provider
                    )
                )
        tenants.append(tenant)
    if not tenants:
        raise CommercialConfigError("At least one tenant is required")
    return CommercialConfig(
        project_root=project_root,
        database_path=database_path,
        provider_key_envs=provider_key_envs,
        tenants=tenants,
        provider_base_url_envs=provider_base_url_envs,
    )
