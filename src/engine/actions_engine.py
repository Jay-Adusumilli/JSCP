from typing import Any, Dict, Iterable, Optional, Union
import os
import traceback

from logger.logger import Logs
from builder.builder import build_and_push_registry2, rollout_restart_deployment
from status.status import set_github_commit_status
from payload.payload_parser import GitHubWebhook
from config.config_parser import Config


WebhookLike = Union[GitHubWebhook, Dict[str, Any]]


def _normalize_branch(ref: Optional[str]) -> Optional[str]:
    """Convert a git ref like 'refs/heads/main' or 'refs/tags/v1' to just the branch/tag name."""
    if not ref:
        return ref
    prefixes = ("refs/heads/", "refs/tags/")
    for p in prefixes:
        if ref.startswith(p):
            return ref[len(p) :]
    return ref


def _flatten_condition(cond: Any) -> Dict[str, Any]:
    """Allow either a mapping or a list of one-key mappings, return a flat dict."""
    if cond is None:
        return {}
    if isinstance(cond, dict):
        return cond
    if isinstance(cond, Iterable):
        flat: Dict[str, Any] = {}
        for item in cond:
            if isinstance(item, dict):
                flat.update(item)
        return flat
    return {}


def _value_from_config_or_env(cfg: Dict[str, Any], key: str, env: str, default: Optional[str] = None) -> Optional[str]:
    return cfg.get(key) or os.getenv(env) or default


def _as_webhook(payload: WebhookLike) -> GitHubWebhook:
    if isinstance(payload, GitHubWebhook):
        return payload
    if isinstance(payload, dict):
        # Best-effort: create GitHubWebhook from dict keys if present
        return GitHubWebhook(
            event_type=payload.get("event_type") or payload.get("event") or "ignored",
            repo_name=payload.get("repo_name") or payload.get("repository"),
            ref=payload.get("ref"),
            commit_sha=payload.get("commit_sha") or payload.get("sha"),
            pusher=payload.get("pusher"),
            action=payload.get("action"),
            build_relevant=payload.get("build_relevant", True),
            raw=payload.get("raw") or payload,
        )
    raise TypeError("payload must be a GitHubWebhook or dict")


def _config_content(cfg: Union[Config, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(cfg, Config):
        return cfg.content or {}
    return cfg or {}


def _match_condition(cond: Dict[str, Any], webhook: GitHubWebhook) -> bool:
    # Expect keys: branch, event
    branch_needed = cond.get("branch")
    event_needed = cond.get("event")

    if branch_needed is None or event_needed is None:
        # If condition not fully specified, do not run
        return False

    ref_branch = _normalize_branch(webhook.ref)

    # Accept either branch name or full ref in config
    branch_ok = branch_needed == ref_branch or branch_needed == (webhook.ref or "")
    event_ok = str(event_needed).lower() == str(webhook.event_type or "").lower()

    return bool(branch_ok and event_ok)


def _send_status_safe(repo: str, sha: Optional[str], state: str, description: str, context: str, token: Optional[str], target_url: Optional[str] = None):
    if not repo or not sha or not token:
        # Not enough info to post a status
        Logs.warning(f"Skipping GitHub status (missing repo/sha/token) context='{context}', state='{state}'")
        return
    try:
        set_github_commit_status(
            repo=repo,
            commit_sha=sha,
            state=state,
            description=description,
            context=context,
            github_token=token,
            target_url=target_url,
        )
    except Exception as e:
        Logs.error(f"Failed to set GitHub status [{context} -> {state}]: {e}")


def run_configured_actions(configs: Dict[str, Union[Config, Dict[str, Any]]], payload: WebhookLike) -> None:
    """
    Execute pipelines for the repo in payload, if its config exists and condition matches.

    Inputs
    - configs: dict from ConfigManager.get_configs(); values may be Config or raw dict.
    - payload: dict or GitHubWebhook from payload_parser.

    Behavior
    - Match repo in payload to a config entry.
    - For each pipeline, if condition {branch,event} matches payload, run builder.
    - Send GitHub status updates at build/push steps.
    """
    webhook = _as_webhook(payload)

    if not webhook.build_relevant:
        Logs.info("Ignoring non build-relevant event")
        return

    repo_full = webhook.repo_name or ""
    if not repo_full:
        Logs.warning("Payload missing repository name; cannot match a config")
        return

    # Find config by exact repo name
    repo_cfg_obj = configs.get(repo_full)
    if not repo_cfg_obj:
        Logs.info(f"No config found for repo '{repo_full}', skipping")
        return

    cfg = _config_content(repo_cfg_obj)

    pipelines = cfg.get("pipelines") or []
    if not isinstance(pipelines, list) or not pipelines:
        Logs.info(f"No pipelines defined for repo '{repo_full}', nothing to do")
        return

    # Resolve shared settings with env fallbacks
    github_token = _value_from_config_or_env(cfg, "github_token", "GITHUB_TOKEN")
    registry_url = _value_from_config_or_env(cfg, "registry_url", "REGISTRY_URL")
    project = _value_from_config_or_env(cfg, "project", "REGISTRY_PROJECT", default="default")

    # Optional: insecure registry flag (top-level default)
    registry_insecure_default = bool(cfg.get("registry_insecure") or os.getenv("REGISTRY_INSECURE") in {"1", "true", "yes", "on"})

    # repo_url can be provided or derived from repo full name
    repo_url = cfg.get("repo_url") or (f"https://github.com/{repo_full}.git" if repo_full else None)

    matched_any = False

    ################################################################################################################
    # Process each pipeline in order
    ################################################################################################################
    for pipe in pipelines:
        name = pipe.get("name") or "pipeline"
        cond = _flatten_condition(pipe.get("condition"))
        if not _match_condition(cond, webhook):
            Logs.debug(f"Pipeline '{name}' condition not met; skipping")
            continue

        matched_any = True

        # Per-pipeline overrides
        dockerfile_path = pipe.get("dockerfile_path") or pipe.get("dockerfile") or "Dockerfile"
        pipe_registry_url = pipe.get("registry_url") or registry_url
        pipe_project = pipe.get("project") or project
        namespace = pipe.get("namespace") or "default"
        pipe_registry_insecure = bool(pipe.get("registry_insecure") if pipe.get("registry_insecure") is not None else registry_insecure_default)

        # Validate required items
        if not repo_url:
            Logs.error(f"Pipeline '{name}': repo_url not set and cannot be derived; skipping")
            continue
        if not pipe_registry_url:
            Logs.error(f"Pipeline '{name}': registry_url missing (set in config or REGISTRY_URL); skipping")
            continue

        # Status contexts include pipeline name for clarity
        build_ctx = f"JCSP Build ({name})"
        push_ctx = f"JCSP Push ({name})"

        _send_status_safe(repo_full, webhook.commit_sha, "pending", "Build started", build_ctx, github_token)
        # Optional: indicate push will happen next
        _send_status_safe(repo_full, webhook.commit_sha, "pending", "Push queued", push_ctx, github_token)

        ################################################################################################################
        # The build step
        ################################################################################################################
        build_success = False
        image_tag: Optional[str] = None
        try:
            image_tag = build_and_push_registry2(
                repo_url=repo_url,
                dockerfile_path=dockerfile_path,
                registry_url=pipe_registry_url,
                project=pipe_project,
                ref=_normalize_branch(webhook.ref) or "main",
                registry_insecure=pipe_registry_insecure,
            )

            build_success = True
            # Mark build as successful
            _send_status_safe(repo_full, webhook.commit_sha, "success", "Build Completed!", build_ctx, github_token)
            Logs.info(f"Pipeline build '{name}' succeeded: {image_tag}")

        except Exception as e:
            # Mark both contexts as failed to reflect pipeline failure
            _send_status_safe(repo_full, webhook.commit_sha, "failure", "Build Failed!", build_ctx, github_token)
            Logs.error(f"Pipeline build '{name}' failed: {e}")
            Logs.debug(traceback.format_exc())

        ################################################################################################################
        # The push/rollout step
        ################################################################################################################
        deployment_name = pipe.get("deployment_name")
        if not build_success:
            _send_status_safe(repo_full, webhook.commit_sha, "failure", "Skipped: build failed", push_ctx, github_token)
            Logs.info(f"Skipping rollout for pipeline '{name}' due to build failure")
            continue
        if not deployment_name:
            _send_status_safe(repo_full, webhook.commit_sha, "failure", "Skipped: deployment_name missing", push_ctx, github_token)
            Logs.error(f"Pipeline '{name}': deployment_name not provided; skipping rollout")
            continue

        try:
            rollout_restart_deployment(deployment_name=deployment_name, namespace=namespace)
            _send_status_safe(repo_full, webhook.commit_sha, "success", f"Rollout Successful!", push_ctx, github_token)
            Logs.info(f"Deployment '{deployment_name}' restarted (namespace='{namespace}') due to new image '{image_tag}'")
        except Exception as e:
            _send_status_safe(repo_full, webhook.commit_sha, "failure", f"Rollout Failed!", push_ctx, github_token)
            Logs.error(f"Failed to restart deployment '{deployment_name}' in ns '{namespace}': {e}")
            Logs.debug(traceback.format_exc())

    if not matched_any:
        Logs.info(f"No pipelines matched conditions for repo '{repo_full}' and event '{webhook.event_type}'")
