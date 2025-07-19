def parse_github_webhook(payload: dict) -> dict:
    """
    Parses a GitHub webhook JSON payload and extracts key info.

    Returns a dict with:
      - event_type (push, pull_request, etc.)
      - repo_name
      - ref (branch or tag)
      - commit_sha
      - pusher (username/email)
      - action (for PR events)
    """

    # Verify the signature of the payload
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")

    event = {}

    # Basic info
    event['repo_name'] = payload.get('repository', {}).get('full_name')
    event['ref'] = payload.get('ref')
    event['commit_sha'] = None
    event['pusher'] = None
    event['action'] = payload.get('action')

    # Identify event type by presence of keys
    if 'pull_request' in payload:
        event['event_type'] = 'pull_request'
        pr = payload['pull_request']
        event['commit_sha'] = pr.get('head', {}).get('sha')
        event['pusher'] = pr.get('user', {}).get('login')
    elif 'head_commit' in payload:
        event['event_type'] = 'push'
        event['commit_sha'] = payload['head_commit'].get('id')
        event['pusher'] = payload.get('pusher', {}).get('name')
    else:
        event['event_type'] = 'unknown'

    return event
