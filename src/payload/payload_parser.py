from dataclasses import dataclass
from typing import Optional, Any, Dict

from payload.signature import verify_signature


@dataclass
class GitHubWebhook:
    event_type: str
    repo_name: Optional[str] = None
    ref: Optional[str] = None
    commit_sha: Optional[str] = None
    pusher: Optional[str] = None
    action: Optional[str] = None
    build_relevant: bool = False
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "repo_name": self.repo_name,
            "ref": self.ref,
            "commit_sha": self.commit_sha,
            "pusher": self.pusher,
            "action": self.action,
            "build_relevant": self.build_relevant,
            "raw": self.raw,
        }


def _detect_event_type(p: Dict[str, Any]) -> str:
    """
    Detect only build-relevant GitHub event types:
    - push (branch or tag pushes)
    - pull_request (opened, synchronize, reopened)
    - release (published)
    - workflow_run (completed workflows)
    - deployment (requested deployments)
    Everything else returns 'ignored'.
    """
    if "pull_request" in p:
        return "pull_request"
    if "head_commit" in p or "commits" in p:
        return "push"
    if "release" in p:
        return "release"
    if "workflow_run" in p:
        return "workflow_run"
    if "deployment" in p:
        return "deployment"
    return "ignored"


def parse_github_webhook(
    payload: dict, payload_body: bytes, secret_token: str, signature_header: str
) -> GitHubWebhook:
    """
    Parse and verify GitHub webhook events into a normalized GitHubWebhook.

    Args:
        payload: The JSON payload (already parsed).
        payload_body: Raw request body (bytes) used to verify signature.
        secret_token: Your GitHub webhook secret.
        signature_header: The 'x-hub-signature-256' header from GitHub.

    Raises:
        SignatureError: If the webhook signature verification fails.

    Returns:
        GitHubWebhook: Normalized webhook object.
    """

    verify_signature(payload_body, secret_token, signature_header)

    # Detect event type and build relevance
    event_type = _detect_event_type(payload)
    build_relevant = event_type != "ignored"

    if not build_relevant:
        return GitHubWebhook(event_type="ignored", build_relevant=False, raw=payload)

    repo_name = payload.get("repository", {}).get("full_name")
    ref: Optional[str] = None
    commit_sha: Optional[str] = None

    # Extract relevant fields based on event type
    if event_type == "push":
        ref = payload.get("ref")
        commit_sha = (payload.get("head_commit", {}) or {}).get("id") or payload.get(
            "after"
        )
    elif event_type == "pull_request":
        pr = payload.get("pull_request", {})
        ref = pr.get("head", {}).get("ref")
        commit_sha = pr.get("head", {}).get("sha")
    elif event_type == "release":
        release = payload.get("release", {})
        ref = release.get("target_commitish")
        commit_sha = release.get("tag_name")
    elif event_type == "workflow_run":
        workflow = payload.get("workflow_run", {})
        ref = workflow.get("head_branch")
        commit_sha = workflow.get("head_sha")
    elif event_type == "deployment":
        deploy = payload.get("deployment", {})
        ref = deploy.get("ref")
        commit_sha = deploy.get("sha")

    # Actor/pusher extraction
    pusher = (
        payload.get("pusher", {}).get("name")
        or payload.get("sender", {}).get("login")
        or payload.get("pull_request", {}).get("user", {}).get("login")
        or (payload.get("release", {}) or {}).get("author", {}).get("login")
        or (payload.get("deployment", {}) or {}).get("creator", {}).get("login")
        or (payload.get("workflow_run", {}) or {}).get("actor", {}).get("login")
    )

    action = payload.get("action")

    return GitHubWebhook(
        event_type=event_type,
        repo_name=repo_name,
        ref=ref,
        commit_sha=commit_sha,
        pusher=pusher,
        action=action,
        build_relevant=build_relevant,
        raw=payload,
    )
