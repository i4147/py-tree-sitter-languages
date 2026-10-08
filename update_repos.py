#!/usr/bin/env python3
"""
This script updates repos.txt to use the latest available commits.

The purpose of repos.txt is to make it easy to see and configure what
version of each language is used.

Differences from the original bash script:
  - Cloning is parallelised with 4 worker processes to speed things up.
  - Each worker gets its own temporary directory so clones cannot collide.
  - Results are written in the original order, so repos.txt stays stable
    and reviewable.

All temporary files/directories are cleaned up automatically, even on
failure (equivalent to the bash `trap ... EXIT`).
"""

import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor


REPOS_TXT = "repos.txt"
MAX_WORKERS = 4


def get_urls(path):
    """
    Return the first whitespace-separated field of every non-empty line
    in `path`, preserving order.  This mirrors:
        cut -d' ' -f1 repos.txt
    but is more forgiving with multiple spaces/tabs.
    """
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            urls.append(line.split()[0])
    return urls


def fetch_latest_commit(url):
    """
    Shallow-clone `url` into a private temporary directory, return
    (url, HEAD commit hash).  Runs inside a worker process.

    Equivalent to the per-URL body of the bash loop:
        git clone -q --depth=1 "$url" "$tempdir"/repo
        latest_commit=$(cd "$tempdir"/repo && git rev-parse HEAD)
        rm -rf "$tempdir"/repo
    """
    with tempfile.TemporaryDirectory() as tempdir:
        repo_dir = os.path.join(tempdir, "repo")
        subprocess.check_call(["git", "clone", "-q", "--depth=1", url, repo_dir])
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            text=True,
        ).strip()
        return url, commit


def main():
    # Read original URLs first, before we overwrite repos.txt.
    urls = get_urls(REPOS_TXT)
    if not urls:
        print(f"{sys.argv[0]}: no URLs found in {REPOS_TXT}", file=sys.stderr)
        return

    # Temporary file for the new repos.txt content.
    fd, tmp_output = tempfile.mkstemp()
    os.close(fd)

    try:
        with open(tmp_output, "w", encoding="utf-8") as out:
            # executor.map preserves input order, so repos.txt keeps the
            # same line order as before even though clones run in parallel.
            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                for url, commit in executor.map(fetch_latest_commit, urls):
                    print(url)
                    print(f"  --> {commit}")
                    out.write(f"{url} {commit}\n")

        # Atomically replace repos.txt.
        # os.replace works across the same filesystem; mkstemp may live
        # on a different one, so fall back to a manual move if needed.
        try:
            os.replace(tmp_output, REPOS_TXT)
        except OSError:
            subprocess.check_call(["mv", tmp_output, REPOS_TXT])
    finally:
        # If os.replace succeeded, tmp_output no longer exists.
        if os.path.exists(tmp_output):
            os.remove(tmp_output)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        # Mimic `set -e`: exit non-zero on any failed subprocess.
        print(
            f"Command failed with exit code {e.returncode}: {e.cmd}",
            file=sys.stderr,
        )
        sys.exit(e.returncode)
