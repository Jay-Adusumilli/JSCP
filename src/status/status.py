import requests

def set_github_commit_status(
    repo: str,
    commit_sha: str,
    state: str,
    description: str,
    context: str,
    github_token: str,
    target_url: str = None
):
    """
    Update the status of a commit on GitHub.

    :param repo: "owner/repo" (e.g., "octocat/Hello-World")
    :param commit_sha: SHA of the commit to update
    :param state: "error", "failure", "pending", or "success"
    :param description: Short description (e.g. "Build finished successfully")
    :param context: A string label to identify the status source (e.g. "CI/CD:K3s")
    :param github_token: Personal access token with `repo:status` permission
    :param target_url: Optional URL linking to build logs, UI, etc.
    """

    url = f"https://api.github.com/repos/{repo}/statuses/{commit_sha}"
    headers = {"Authorization": f"token {github_token}"}
    payload = {
        "state": state,
        "description": description,
        "context": context,
    }
    if target_url:
        payload["target_url"] = target_url

    r = requests.post(url, json=payload, headers=headers)
    if r.status_code != 201:
        raise Exception(f"Failed to set status: {r.status_code} {r.text}")
    return r.json()
