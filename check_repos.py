#!/usr/bin/env python3
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


def is_repo_valid(repo_url):
    """Check if a repository exists using git ls-remote"""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5
        )
        return (repo_url, result.returncode == 0)
    except subprocess.TimeoutExpired:
        return (repo_url, False)
    except Exception:
        return (repo_url, False)


def main():
    repos_file = "repos.txt"
    notfound_file = "notfound.txt"

    # Read all repos
    if not os.path.exists(repos_file):
        print(f"Error: {repos_file} not found!")
        return

    with open(repos_file, "r") as f:
        repos = [line.strip() for line in f if line.strip()]

    print(f"Found {len(repos)} repositories to check...\n")

    found_repos = []
    not_found_repos = []
    checked = 0

    # Use 10 parallel workers (adjust for your bandwidth)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(is_repo_valid, repo): repo for repo in repos}

        for future in as_completed(futures):
            repo_url, is_valid = future.result()
            checked += 1
            status = "✓ OK" if is_valid else "✗ NOT FOUND"
            print(f"[{checked}/{len(repos)}] {repo_url} ... {status}")

            if is_valid:
                found_repos.append(repo_url)
            else:
                not_found_repos.append(repo_url)

    # Write results
    with open(repos_file, "w") as f:
        for repo in found_repos:
            f.write(repo + "\n")

    with open(notfound_file, "w") as f:
        for repo in not_found_repos:
            f.write(repo + "\n")

    print(f"\n✓ Updated {repos_file}: {len(found_repos)} valid repos")
    print(f"✓ Created {notfound_file}: {len(not_found_repos)} not found repos")


if __name__ == "__main__":
    main()
