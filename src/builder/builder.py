import subprocess

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

    # Build directly from git (branch or commit ref).
    subprocess.run([
        "nerdctl", "--insecure-registry",
        "build",
        "-t", image_tag,
        f"{repo_url}#{ref}:{dockerfile_path}"
    ], check=True)

    # Push to registry.
    subprocess.run([
        "nerdctl", "--insecure-registry",
        "push", image_tag
    ], check=True)

    return image_tag


if __name__ == "__main__":
    # Example usage.
    build_and_push_registry2(
        repo_url="",
        dockerfile_path="Dockerfile",
        registry_url="registry.local:5000",
        project="myproject",
        ref="main"
    )