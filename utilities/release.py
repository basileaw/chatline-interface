# release.py
import sys
import time
import requests
import argparse
import subprocess
from rich import box
from pathlib import Path
from rich.panel import Panel
from rich.console import Console

console = Console()


def run(cmd, check=True):
    result = subprocess.run(cmd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout.strip()


def get_version_from_pyproject():
    """Extract version directly from pyproject.toml file."""
    with open("pyproject.toml", "r") as f:
        content = f.read()

    for line in content.split("\n"):
        if line.strip().startswith("version = "):
            return line.split("=")[1].strip().strip('"').strip("'")

    raise ValueError("Could not find version in pyproject.toml")


def update_version_in_pyproject(version_type):
    """Update version in pyproject.toml based on version_type (patch, minor, major)."""
    current_version = get_version_from_pyproject()
    parts = current_version.split(".")

    if version_type == "patch":
        parts[2] = str(int(parts[2]) + 1)
    elif version_type == "minor":
        parts[1] = str(int(parts[1]) + 1)
        parts[2] = "0"
    elif version_type == "major":
        parts[0] = str(int(parts[0]) + 1)
        parts[1] = "0"
        parts[2] = "0"

    new_version = ".".join(parts)

    with open("pyproject.toml", "r") as f:
        content = f.readlines()

    with open("pyproject.toml", "w") as f:
        for line in content:
            if line.strip().startswith("version = "):
                version_prefix = line.split("=")[0] + "= "
                quote = '"' if '"' in line else "'"
                f.write(f"{version_prefix}{quote}{new_version}{quote}\n")
            else:
                f.write(line)

    return new_version


def wait_for_pypi(package_name, expected_version, max_retries=12, interval=5):
    spinner = "|/-\\"
    idx = 0
    repo_url = run(["git", "config", "--get", "remote.origin.url"]).strip()
    # Convert SSH URL to HTTPS if necessary
    if repo_url.startswith("git@github.com:"):
        repo_url = repo_url.replace("git@github.com:", "https://github.com/")
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    actions_url = f"{repo_url}/actions"

    console.print(f"Waiting for version {expected_version} to appear on PyPI...")
    for _ in range(max_retries):
        for _ in range(4):  # 4 ticks per interval
            print(f"\rPolling PyPI {spinner[idx]}", end="", flush=True)
            idx = (idx + 1) % len(spinner)
            time.sleep(interval / 4)

        try:
            response = requests.get(
                f"https://pypi.org/pypi/{package_name}/json", timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                latest_version = data["info"]["version"]
                if latest_version == expected_version:
                    print("\r", end="")  # Clear the spinner line
                    console.print(
                        f"[bold green]✓ Version {expected_version} successfully published to PyPI!"
                    )
                    return
        except requests.exceptions.RequestException:
            pass

    print("\r", end="")  # Clear the spinner line
    console.print(
        f"[bold red]✗ Timed out waiting for version {expected_version} on PyPI."
    )
    console.print(f"[bold blue]Check progress at: {actions_url}")


def confirm_proceed(package_name, current_version, new_version, dry_run):
    actions = [
        "Bump version in pyproject.toml",
        "Commit version bump",
        "Create git tag",
        "Push commit and tag to origin",
    ]

    if not dry_run:
        actions.extend(
            [
                "Trigger GitHub Action to publish to PyPI",
                "Poll PyPI to confirm publication",
            ]
        )
    else:
        actions.append("(Dry run mode, no changes will be made)")

    confirmation_text = "\n".join(
        [
            f"Package name: {package_name}",
            f"Current version: {current_version}",
            f"New version: {new_version}",
            f"Dry run: {'Yes' if dry_run else 'No'}",
            f"Actions to be performed:",
            "\n".join(f" - {action}" for action in actions),
        ]
    )

    # Create a panel with a tighter width - 60 characters or content width, whichever is smaller
    panel_width = min(60, max(len(line) for line in confirmation_text.split("\n")))
    console.print(
        Panel(
            confirmation_text,
            title="Release Details",
            border_style="green",
            box=box.ROUNDED,
            width=panel_width,
            expand=False,
        )
    )

    # Custom single-key confirmation prompt
    console.print("Proceed? (Y/n): ", end="")
    # Use python's built-in input but only check the first character
    response = input().strip().lower()
    return not response or response[0] != "n"


def check_publish_workflow_exists(workflow_path=None):
    if workflow_path is None:
        workflow_path = ".github/workflows/publish.yml"
    workflow_file = Path(workflow_path)
    if not workflow_file.is_file():
        console.print(
            f"[bold red]Error: publish workflow not found at {workflow_path}."
        )
        console.print(
            f"[bold red]Ensure your GitHub Action is set up before releasing."
        )
        sys.exit(1)


def get_package_name():
    try:
        # Try to extract package name from pyproject.toml
        if Path("pyproject.toml").exists():
            content = Path("pyproject.toml").read_text()
            # Look for name = "package_name" in pyproject.toml
            for line in content.split("\n"):
                if line.strip().startswith("name = "):
                    # Extract the package name from quotes
                    name = line.split("=")[1].strip()
                    name = name.strip('"').strip("'")
                    return name
    except Exception as e:
        console.print(
            f"[bold red]Error extracting package name from pyproject.toml: {e}"
        )

    # If automatic detection fails, prompt the user
    return console.input("Enter the package name: ").strip()


def main():
    parser = argparse.ArgumentParser(
        description="Bump version, commit, tag, push, and poll PyPI."
    )
    parser.add_argument(
        "type", choices=["patch", "minor", "major"], help="Version bump type."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate without making changes."
    )
    parser.add_argument(
        "--package-name",
        help="Override the package name (auto-detected from pyproject.toml by default).",
    )
    parser.add_argument(
        "--workflow-path",
        help="Path to the GitHub publish workflow (default: .github/workflows/publish.yml).",
    )
    parser.add_argument(
        "--skip-pypi-check",
        action="store_true",
        help="Skip checking PyPI for the new version.",
    )
    args = parser.parse_args()

    dry_run = args.dry_run
    package_name = args.package_name or get_package_name()

    # Check publish workflow exists
    check_publish_workflow_exists(args.workflow_path)

    # Check clean git state
    status = run(["git", "status", "--porcelain"], check=False)
    if status:
        console.print(
            "[bold red]Error: Repository has uncommitted changes. Commit or stash them first."
        )
        sys.exit(1)

    old_commit = run(["git", "rev-parse", "HEAD"])

    # Get current version from pyproject.toml
    current_version = get_version_from_pyproject()

    # Calculate new version
    if dry_run:
        parts = current_version.split(".")
        if args.type == "patch":
            parts[2] = str(int(parts[2]) + 1)
        elif args.type == "minor":
            parts[1] = str(int(parts[1]) + 1)
            parts[2] = "0"
        elif args.type == "major":
            parts[0] = str(int(parts[0]) + 1)
            parts[1] = "0"
            parts[2] = "0"
        new_version = ".".join(parts)
    else:
        new_version = current_version  # Will be updated later

    if not confirm_proceed(package_name, current_version, new_version, dry_run):
        console.print("[bold red]Aborted by user.")
        sys.exit(0)

    commit_message = f"release {new_version}"
    tag_name = f"v{new_version}"

    try:
        if dry_run:
            console.print(
                f"[bold yellow][DRY-RUN] Would update version from {current_version} to {new_version} in pyproject.toml"
            )
            console.print(f"[bold yellow][DRY-RUN] Would git add pyproject.toml")
            console.print(
                f"[bold yellow][DRY-RUN] Would commit with message: '{commit_message}'"
            )
            console.print(f"[bold yellow][DRY-RUN] Would create git tag: '{tag_name}'")
            console.print(f"[bold yellow][DRY-RUN] Would push commit and tag to origin")
        else:
            # Update the version in pyproject.toml
            new_version = update_version_in_pyproject(args.type)
            console.print(
                f"Updated version from {current_version} to {new_version} in pyproject.toml"
            )

            # Commit the changes
            run(["git", "add", "pyproject.toml"])
            run(["git", "commit", "-m", commit_message])
            run(["git", "tag", tag_name])

            console.print(f"Pushing commit and tag '{tag_name}' to origin...")
            run(["git", "push", "origin", "HEAD"])
            run(["git", "push", "origin", tag_name])

            if not args.skip_pypi_check:
                wait_for_pypi(package_name, new_version)
    except subprocess.CalledProcessError as e:
        console.print("[bold red]Error occurred during release process.")
        console.print(f"Command: {' '.join(e.cmd)}")
        if e.output:
            console.print(f"Output:\n{e.output}")
        if e.stderr:
            console.print(f"Error:\n{e.stderr}")

        if not dry_run:
            console.print("[yellow]Rolling back changes...")
            run(["git", "checkout", "pyproject.toml"], check=False)
            run(["git", "reset", "--hard", old_commit], check=False)
            run(["git", "tag", "-d", tag_name], check=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
