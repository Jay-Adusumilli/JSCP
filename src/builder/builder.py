import subprocess
import os

def build_and_push_registry2(
    repo_url: str,
    dockerfile_path: str,
    registry_url: str,
    project: str,
    ref: str = "main"
) -> str:
    """
    Build a Docker image from a GitHub repo and push it to a registry:2 instance running in k3s.

    :param repo_url: e.g. https://github.com/user/repo.git.
    :param dockerfile_path: path to Dockerfile in repo.
    :param registry_url: e.g. registry.local:5000.
    :param project: logical grouping (path segment).
    :param ref: branch, tag, or commit SHA (default: main).
    :return: Full image tag pushed to registry.
    """

    # Registry URL should not have a trailing slash or .git suffix.
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    tag = ref
    image_tag = f"{registry_url}/{project}/{repo_name}:{tag}"

    # Determine build context directory and Dockerfile name
    df_dir, df_file = os.path.split(dockerfile_path)
    context_dir = df_dir or "."

    # Build directly from git (branch or commit ref).
    cmd = [
        "nerdctl", "--insecure-registry",
        "build",
        "-t", image_tag,
    ]
    # Only specify -f if the Dockerfile name is non-default relative to the context
    if df_file and df_file != "Dockerfile":
        cmd += ["-f", df_file]

    cmd += [f"{repo_url}#{ref}:{context_dir}"]

    subprocess.run(cmd, check=True)

    # Push to registry.
    subprocess.run([
        "nerdctl", "--insecure-registry",
        "push", image_tag
    ], check=True)

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
