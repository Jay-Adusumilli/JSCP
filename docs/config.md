# JCSP Configuration Guide

This document explains how to configure JCSP via YAML files. It covers where configs live, how they’re loaded and reloaded, and the schema for top-level and per-pipeline settings.

## Where configuration files live

- JCSP reads all `.yaml` files in the directory specified by the `CONFIGS_LOCATION` environment variable.
  - Default: `./configs`
- You can keep multiple configs in that folder—typically one per GitHub repository you want JCSP to handle.
- Config changes are hot‑reloaded automatically (no server restart required). JCSP watches the folder and reloads with a short debounce.

## File discovery and precedence

- Every `.yaml` file is parsed into a config object.
- The config’s identity key is `repo` (the full GitHub name `owner/repo`). If `repo` is not present, JCSP uses the YAML filename (without extension) as the key.
- Duplicate handling when multiple files target the same `repo`:
  - If both have a numeric `version`, the higher version wins.
  - If versions are equal, JCSP logs a warning and keeps the first one it loaded.
  - If versions are missing, JCSP logs a warning and keeps the first one it loaded.

## Supported GitHub events

JCSP only considers the following events as build‑relevant. All others are ignored.
- `push`
- `pull_request` (opened, synchronize, reopened)
- `release` (published)
- `workflow_run` (completed)
- `deployment` (requested)

## Top-level schema

Top‑level keys apply to the whole repo and provide defaults for all pipelines.

- `repo` (string, required): GitHub repository in `owner/repo` form. If omitted, the filename (without `.yaml`) is used.
- `version` (integer, optional): Used only for precedence when duplicate `repo` configs exist.
- `github_token` (string, optional): GitHub token used for commit status updates. If omitted, falls back to `GITHUB_TOKEN` env.
  - Minimum scope: `repo:status` for classic PATs.
- `registry_url` (string, optional): Docker registry hostname (e.g., `localhost:5000`). If omitted, falls back to `REGISTRY_URL` env.
- `project` (string, optional): Path segment used in the image tag (e.g., `myproject`). If omitted, falls back to `REGISTRY_PROJECT` env or defaults to `default`.
- `repo_url` (string, optional): Full Git clone URL. If omitted, JCSP derives `https://github.com/<repo>.git` from `repo`.
- `pipelines` (array, required): One or more pipeline definitions (see below).

## Pipeline schema

Each item in `pipelines` defines a condition and the actions to take when matched.

Common fields:
- `name` (string, optional): Friendly name used in logs and GitHub status context labels.
- `condition` (required): Determines when this pipeline runs. It can be:
  - a mapping like `{ branch: main, event: push }`, or
  - a list of one‑key mappings like `[ { branch: main }, { event: push } ]`.
  - Required keys inside condition:
    - `branch`: Branch name (e.g., `main`). You may also use the full ref (e.g., `refs/heads/main`).
    - `event`: One of `push`, `pull_request`, `release`, `workflow_run`, `deployment`.

Build and rollout settings:
- `dockerfile_path` or `dockerfile` (string, optional): Path to the Dockerfile within the repo. Default: `Dockerfile` at the repo root.
  - Examples: `Dockerfile`, `deploy/Dockerfile`, `services/api/Dockerfile`.
  - JCSP builds directly from the Git repo using `nerdctl` with a Git URL as the build context. If the Dockerfile isn’t named `Dockerfile`, JCSP will pass `-f <name>` automatically, and set the context to the Dockerfile’s directory.
- `registry_url` (string, optional): Overrides the top‑level `registry_url` for this pipeline.
- `project` (string, optional): Overrides the top‑level `project` for this pipeline.
- `deployment_name` (string, recommended): Kubernetes Deployment to rollout‑restart after pushing the image.
  - If omitted, rollout is skipped—and JCSP will mark the rollout status as "Skipped" for visibility.
- `namespace` (string, optional): Kubernetes namespace for the deployment. Default: `default`.

Notes:
- Unknown keys in the pipeline are ignored by the current engine.
- The pipeline key named `pipeline` (singular) is not used by the engine.

## Image tagging

JCSP tags images as:
```
<registry_url>/<project>/<repo_name>:<ref>
```
- `repo_name` is derived from the Git URL (the last path segment without `.git`).
- `<ref>` is the branch/tag (e.g., `main`, `test`). Pull requests use the head branch; releases use the tag name; other events extract a meaningful ref as available.

## GitHub commit statuses

For each matched pipeline, JCSP posts statuses (when token and SHA are available):
- Build context: `JCSP Build (<pipeline name>)`
  - pending → success/failure
- Push/Rollout context: `JCSP Push (<pipeline name>)`
  - pending → success/failure (or "Skipped" message when build fails or `deployment_name` is missing)

If `github_token` isn’t provided and `GITHUB_TOKEN` isn’t set, statuses are skipped with a warning in logs.

## End‑to‑end example

A minimal working example, matching a push to branch `test`:

```yaml
repo: Jay-Adusumilli/test
version: 1
registry_url: localhost:5000
github_token: <your PAT with repo:status>
project: example_project
pipelines:
  - name: example_pipeline
    condition:
      - branch: test
      - event: push
    # Optional if your Dockerfile is at the repo root
    # dockerfile_path: Dockerfile
    deployment_name: example_deployment
    # Optional, defaults to "default"
    # namespace: default
```

A second pipeline in the same file, building a sub‑dir Dockerfile and deploying to a custom namespace:

```yaml
pipelines:
  - name: api
    condition: { branch: main, event: push }
    dockerfile_path: services/api/Dockerfile
    project: myproject
    deployment_name: api-deployment
    namespace: production

  - name: pr-checks
    condition: [ { branch: main }, { event: pull_request } ]
    # No deployment_name → rollout is skipped, but build still runs and is reported
```

## Environment variables used by JCSP

- `CONFIGS_LOCATION`: Directory to load YAML configs from. Default: `./configs`.
- `WEBHOOK_SECRET`: Required by the server to verify GitHub webhook signatures.
- `GITHUB_TOKEN`: Fallback for `github_token` (used for commit statuses).
- `REGISTRY_URL`: Fallback for `registry_url`.
- `REGISTRY_PROJECT`: Fallback for `project` (default is `default`).
- `LOG_PATH`: Optional path for log file (default is `./logs/jscp.log`).

## Hot reload behavior

- JCSP watches the config directory and reloads configs on change with a short debounce.
- Syntax or validation errors in updated files are logged; valid configs continue to be used.

## Operational prerequisites

- The JCSP server host must have `nerdctl` and `kubectl` available in PATH.
- The registry specified by `registry_url` must be reachable from the server.
- For GitHub status updates, the token must have `repo:status` scope (for classic PATs).

## Troubleshooting tips

- Pipeline not firing?
  - Ensure `condition` has both `branch` and `event` and that they match the incoming webhook.
  - Check that the repo name in the webhook (`owner/repo`) matches the `repo` in your YAML.
- Build fails immediately?
  - Verify `dockerfile_path` is correct and exists at that path in the repo.
  - Ensure the server can clone the repo URL and access the specified branch/tag/commit.
- Rollout fails or is skipped?
  - Provide `deployment_name` and confirm `kubectl` has access to the cluster/namespace.

