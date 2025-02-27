import sys
import subprocess
import os
import re

def run_cmd(cmd, capture=False, shell=False):
    """Run a shell command and return the result."""
    print("Running:", " ".join(cmd) if not shell else cmd)
    return subprocess.run(cmd, check=True, capture_output=capture, text=True, shell=shell)

def extract_version(output):
    """Extracts version number safely using regex."""
    match = re.search(r"(\d+\.\d+\.\d+)", output)
    if match:
        return match.group(1)
    else:
        print("Error: Unable to extract version number.")
        sys.exit(1)

def bump_patch_version():
    """Bumps the patch version if a version conflict occurs."""
    print("🔄 Version conflict detected! Bumping patch version...")
    try:
        out = run_cmd(["poetry", "version", "patch"], capture=True).stdout.strip()
        new_ver = extract_version(out)
        print(f"✅ New version bumped to: {new_ver}")
        return new_ver
    except subprocess.CalledProcessError as e:
        print("❌ Error bumping patch version:", e)
        sys.exit(1)

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor", "major"):
        print("Usage: python publish.py [patch|minor|major]")
        sys.exit(1)
    
    bump = sys.argv[1]

    # Bump version using Poetry
    try:
        out = run_cmd(["poetry", "version", bump], capture=True).stdout.strip()
        new_ver = extract_version(out)
    except subprocess.CalledProcessError as e:
        print("Error bumping version:", e)
        sys.exit(1)

    print("New version:", new_ver)

    # Build the package
    try:
        run_cmd(["poetry", "build"])
    except subprocess.CalledProcessError as e:
        print("Build failed:", e)
        sys.exit(1)

    # Publish to PyPI
    try:
        run_cmd(["poetry", "publish", "--build", "--no-interaction"], capture=True)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else ""
        
        # Detect if the error is due to a version conflict
        if "filename has already been used" in error_msg:
            new_ver = bump_patch_version()
            run_cmd(["poetry", "build"])
            run_cmd(["poetry", "publish", "--build", "--no-interaction"], capture=True)
        else:
            print("Publish error:", error_msg)
            sys.exit(e.returncode)

    print(f"Published {new_ver} successfully!")

if __name__ == "__main__":
    main()
