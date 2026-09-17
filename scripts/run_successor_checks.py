#!/usr/bin/env python3
"""Explicit successor CI dispatch with an isolated, pinned methodology runtime."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from validate_successor_release import METHODOLOGY_COMMITS, read, relative_path, release_profile


def run(command, **kwargs):
    subprocess.run([str(part) for part in command], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--release", default="successor-release.json")
    parser.add_argument("--if-selected", action="store_true", help="Before first selection, report v3-only; deletion after selection fails closed")
    parser.add_argument("--methodology-repo", type=Path, help="Use an existing exact-byte checkout without network/bootstrap")
    parser.add_argument("--python", default=sys.executable, help="Compatible interpreter for --methodology-repo; otherwise used to create the isolated venv")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        descriptor = relative_path(root, args.release)
        if args.if_selected and not descriptor.exists():
            history = subprocess.check_output(["git", "-C", str(root), "log", "-1", "--format=%H", "--", args.release])
            if not history.strip():
                print(json.dumps({"successor_validation": "not_selected", "scope": "historical_v3_only"}))
                return 0
        if not descriptor.is_file():
            raise ValueError("Selected successor release metadata is missing")
        profile = release_profile(read(descriptor))
        commit = METHODOLOGY_COMMITS[profile]
        test_name = "test_successor_release_v9.py" if profile == "v9" else "test_successor_release.py"
        if not (root / "tests" / test_name).is_file():
            raise ValueError("Focused successor tests are missing")
        with tempfile.TemporaryDirectory(prefix="successor-methodology-") as directory:
            temporary = Path(directory)
            method = args.methodology_repo.resolve() if args.methodology_repo else temporary / "methodology"
            python = Path(args.python)
            if args.methodology_repo is None:
                run(["git", "init", "--quiet", method])
                run(["git", "-C", method, "fetch", "--depth=1", "https://github.com/publication-intelligence/evaluate-subject-index.git", commit])
                run(["git", "-C", method, "checkout", "--quiet", "--detach", commit])
                run([args.python, "-m", "venv", temporary / "venv"])
                python = temporary / "venv/bin/python"
                run([python, "-m", "pip", "install", "--disable-pip-version-check", "-r", method / "requirements.txt"])
            env = {**os.environ, "SUCCESSOR_METHODOLOGY_REPO": str(method), "PYTHONDONTWRITEBYTECODE": "1"}
            run([python, "-m", "pip", "check"], env=env)
            run([python, "-m", "unittest", "discover", "-s", root / "tests", "-p", test_name, "-v"], env=env)
            run([python, root / "scripts/validate_successor_release.py", "--root", root, "--release", args.release, "--methodology-repo", method], env=env)
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
