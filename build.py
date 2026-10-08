import os
import subprocess
import sys
import json
from tree_sitter import Language


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# JSON file you saved earlier.  It must contain a list of objects like:
#   [{"language": "Bash", "repository": "tree-sitter/tree-sitter-bash"}, ...]
LANGUAGES_JSON = "langguages.json"

# Original repos.txt is still used for cloning.  Each line must be:
#   <git-url> <commit-hash>
REPOS_TXT = "repos.txt"

# Directory where all grammar repositories are cloned.
VENDOR_DIR = "vendor"


# ---------------------------------------------------------------------------
# Load language paths from JSON
# ---------------------------------------------------------------------------

def load_language_paths():
    """
    Read langguages.json and return a list of vendor paths suitable for
    Language.build_library().

    Rules:
    - If the repository string contains "(vendored)", strip that marker and
      use the remaining path as-is (e.g. "grammars/abnf").
    - Otherwise, assume the repository has been cloned into
      vendor/<repo-name> (e.g. "tree-sitter/tree-sitter-bash" ->
      "vendor/tree-sitter-bash").
    - Many languages share the same repository, so duplicate paths are removed
      while preserving the original order.

    Note: Some repositories are monorepos and need a subdirectory
    (e.g. tree-sitter-typescript/tsx).  The JSON does not carry that
    information, so you may need to add manual overrides after generating
    this list.
    """
    with open(LANGUAGES_JSON, "r", encoding="utf-8") as f:
        languages = json.load(f)

    paths = []
    seen = set()

    for item in languages:
        repo = item["repository"].strip()

        if "(vendored)" in repo:
            # Example: "grammars/abnf (vendored)" -> "grammars/abnf"
            path = repo.replace("(vendored)", "").strip()
        else:
            # Example: "tree-sitter/tree-sitter-bash" -> "vendor/tree-sitter-bash"
            repo_name = repo.rstrip("/").split("/")[-1]
            path = f"{VENDOR_DIR}/{repo_name}"

        if path not in seen:
            seen.add(path)
            paths.append(path)

    return paths


# ---------------------------------------------------------------------------
# Clone repositories (unchanged from original script)
# ---------------------------------------------------------------------------

def clone_repos():
    """
    Clone all repositories listed in repos.txt into vendor/.
    This function is only needed the first time the build runs.
    """
    repos = []
    with open(REPOS_TXT, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            url, commit = line.split()
            clone_directory = os.path.join(
                VENDOR_DIR, url.rstrip("/").split("/")[-1]
            )
            repos.append((url, commit, clone_directory))

    # During the build, this script runs several times, and only needs to
    # download repositories on first time.
    if os.path.isdir(VENDOR_DIR) and len(os.listdir(VENDOR_DIR)) == len(repos):
        print(f"{sys.argv[0]}: Language repositories have been cloned already.")
        return

    os.makedirs(VENDOR_DIR, exist_ok=True)

    for url, commit, clone_directory in repos:
        print()
        print(f"{sys.argv[0]}: Cloning: {url} (commit {commit}) --> {clone_directory}")
        print()

        if os.path.exists(clone_directory):
            continue

        # https://serverfault.com/a/713065
        os.mkdir(clone_directory)
        subprocess.check_call(["git", "init"], cwd=clone_directory)
        subprocess.check_call(["git", "remote", "add", "origin", url], cwd=clone_directory)
        subprocess.check_call(["git", "fetch", "--depth=1", "origin", commit], cwd=clone_directory)
        subprocess.check_call(["git", "checkout", commit], cwd=clone_directory)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # 1. Clone all repositories listed in repos.txt
    clone_repos()

    # 2. Determine the output library filename for the current platform
    if sys.platform == "win32":
        languages_filename = "tree_sitter_languages\\languages.dll"
    else:
        languages_filename = "tree_sitter_languages/languages.so"

    print(f"{sys.argv[0]}: Building", languages_filename)

    # 3. Load the list of language paths from langguages.json
    language_paths = load_language_paths()
    print(f"{sys.argv[0]}: Building {len(language_paths)} language paths")

    # 4. Build the shared library
    Language.build_library(
        languages_filename,
        language_paths,
    )


if __name__ == "__main__":
    main()