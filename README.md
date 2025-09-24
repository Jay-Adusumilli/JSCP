# Jay's Simple Configurable Pipeline

Want to just build and deploy your Dockerized app to Kubernetes on GitHub events, without the complexity of full CI/CD systems? JCSP is a lightweight server that watches your GitHub repo and triggers builds and rollouts based on simple YAML configs.

### Features:
- Simple YAML-based pipeline definitions.
- Supports multiple pipelines per repo.
- Builds Docker images using `nerdctl`.
- Pushes images to your specified registry.
- Deploys to Kubernetes using `kubectl rollout restart`.
- Posts build statuses back to GitHub.

### Requires:
- A Docker registry (e.g., Docker Hub, GitHub Container Registry, a private registry.
- A Kubernetes cluster with `kubectl` access.
- A GitHub Personal Access Token (PAT) with `repo:status` scope to post build statuses.
- `nerdctl` installed on the server for building and pushing images.
- A GitHub webhook pointing to your JCSP server.
- Python.


