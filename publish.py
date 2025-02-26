# publish.py 

import sys, subprocess, os

def run_cmd(cmd, capture=False, shell=False):
    print("Running:", " ".join(cmd) if not shell else cmd)
    return subprocess.run(cmd, check=True, capture_output=capture, text=True, shell=shell)

def safe_push():
    try:
        run_cmd(["git", "push"])
    except subprocess.CalledProcessError:
        print("Push failed; attempting 'git pull --rebase'...")
        if os.path.exists(".git/rebase-merge") or os.path.exists(".git/rebase-apply"):
            run_cmd(["git", "rebase", "--abort"])
        run_cmd(["git", "pull", "--rebase"])
        run_cmd(["git", "push"])

def revert_pyproject():
    print("Reverting pyproject.toml...")
    run_cmd(["git", "checkout", "--", "pyproject.toml"])

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor", "major"):
        print("Usage: python release.py [patch|minor|major]")
        sys.exit(1)
    bump = sys.argv[1]

    # Bump version using Poetry.
    try:
        out = run_cmd(["poetry", "version", bump], capture=True).stdout.strip()
        if "->" in out:
            new_ver = out.split("->")[-1].strip()
        elif "to" in out:
            new_ver = out.split("to")[-1].strip()
        else:
            print("Unexpected output from poetry version.")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("Error bumping version:", e)
        sys.exit(1)
    print("New version:", new_ver)

    # Build the package.
    try:
        run_cmd(["poetry", "build"])
    except subprocess.CalledProcessError as e:
        print("Build failed:", e)
        revert_pyproject()
        sys.exit(1)

    # Publish to PyPI (interactive if needed).
    try:
        run_cmd(["poetry", "publish", "--build"], capture=True)
    except subprocess.CalledProcessError as e:
        print("Publish error:", e.stderr)
        revert_pyproject()
        sys.exit(e.returncode)

    # Now that publish succeeded, commit and tag the version bump.
    try:
        run_cmd(["git", "add", "pyproject.toml"])
        run_cmd(["git", "commit", "-m", f"Released v{new_ver}"])
        tag = f"v{new_ver}"
        if tag in run_cmd(["git", "tag", "--list", tag], capture=True).stdout.split():
            run_cmd(["git", "tag", "-d", tag])
        run_cmd(["git", "tag", tag])
    except subprocess.CalledProcessError as e:
        print("Git commit/tag error:", e)
        sys.exit(1)

    try:
        safe_push()
        run_cmd(["git", "push", "--tags"])
    except subprocess.CalledProcessError as e:
        print("Error pushing to remote:", e)
        sys.exit(1)

    print(f"Release {new_ver} published successfully!")

if __name__ == "__main__":
    main()
