import subprocess
import os


def build_and_push_registry2(
    repo_url: str,
    dockerfile_path: str,
    registry_url: str,
    project: str,
    ref: str = "main",
    registry_insecure: bool = False,
) -> str:
    """
    Build a Docker image from a GitHub repo with BuildKit (buildctl) and push it to a registry:2 instance.

    :param repo_url: e.g. https://github.com/user/repo.git.
    :param dockerfile_path: path to Dockerfile in repo (relative to repo root).
    :param registry_url: e.g. registry.local:5000.
    :param project: logical grouping (path segment).
    :param ref: branch, tag, or commit SHA (default: main).
    :param registry_insecure: set True to allow pushing to insecure (HTTP) registries.
    :return: Full image tag pushed to registry.
    """

    # Normalize values
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    tag = ref
    image_tag = f"{registry_url}/{project}/{repo_name}:{tag}"

    # Split Dockerfile path into context dir and Dockerfile filename
    df_dir, df_file = os.path.split(dockerfile_path or "Dockerfile")
    context_dir = df_dir or "."
    dockerfile_name = df_file or "Dockerfile"

    # Prefer HTTPS/SSH URL as-is to avoid blocked git:// protocol
    git_ctx_base = repo_url

    # Compose full git/https context with ref and optional subdirectory
    if context_dir and context_dir != ".":
        git_context = f"{git_ctx_base}#{ref}:{context_dir}"
    else:
        git_context = f"{git_ctx_base}#{ref}"

    # Build output attributes
    out = f"type=image,name={image_tag},push=true"
    if registry_insecure:
        out += ",registry.insecure=true"

    # Invoke buildctl to build and push
    cmd = [
        "buildctl", "build",
        "--frontend", "dockerfile.v0",
        "--opt", f"filename={dockerfile_name}",
        "--opt", f"context={git_context}",
        "--output", out,
    ]

    subprocess.run(cmd, check=True)

    return image_tag


def rollout_restart_deployment(deployment_name: str, namespace: str = "default") -> None:
    """
    Perform a rollout restart of a Kubernetes deployment using kubectl.

    :param deployment_name: Name of the deployment to restart.
    :param namespace: Kubernetes namespace (default: default).
    """

    subprocess.run([
        "kubectl", "rollout", "restart",
        f"deployment/{deployment_name}",
        "-n", namespace
    ], check=True)
