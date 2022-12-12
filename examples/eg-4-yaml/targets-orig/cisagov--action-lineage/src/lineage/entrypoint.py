"""GitHub Action to create pull requests for upstream changes."""

# Standard Python Libraries
from enum import Enum, auto
import logging
import os
from pathlib import Path
import subprocess  # nosec
import sys
from typing import Generator, List, Optional, Tuple
from urllib.parse import ParseResult, urlparse

# Third-Party Libraries
from actions_toolkit import core
import chevron
from github import Github, PullRequest, Repository
import pkg_resources
import requests
import yaml

# Constants
ALREADY_UP_TO_DATE = "Already up to date."
CONFIG_FILENAME = ".github/lineage.yml"
CODEOWNERS_FILENAME = ".github/CODEOWNERS"
GIT = "/usr/bin/git"
PR_LABEL_NAMES = ["upstream update"]
PR_METADATA = 'lineage:metadata:{"slayed":true}'
UNRELATED_HISTORY = "fatal: refusing to merge unrelated histories"


class OnError(Enum):
    """Enumeration for handling non-zero subprocess runs."""

    OK = auto()
    WARN = auto()
    FAIL = auto()


def run(
    cmd: List[str],
    cwd: Optional[str] = None,
    comment: Optional[str] = None,
    on_error: OnError = OnError.FAIL,
) -> subprocess.CompletedProcess:
    """Run a command and display its output and return code."""
    if comment:
        logging.info("💬 %s", comment)
    logging.debug("➤  %s", cmd)
    proc = subprocess.run(
        cmd,
        shell=False,  # nosec
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode == 0:
        logging.debug(proc.stdout.decode())
        logging.info("✅ success")
    elif on_error == OnError.OK:
        logging.debug(proc.stdout.decode())
        logging.info("✅ (error ok) return code: %d", proc.returncode)
    elif on_error == OnError.WARN:
        logging.warning(proc.stdout.decode())
        logging.warning("⚠️ WARNING! return code: %d", proc.returncode)
    else:  # OnError.FAIL
        logging.fatal(proc.stdout.decode())
        logging.fatal("❌ ERROR! return code: %d", proc.returncode)
        raise Exception("Subprocess was expected to exit with 0.")
    return proc


def load_template(github_workspace_dir, default_filename, custom_filename=None):
    """Load specified template file or local default."""
    template_data: str
    if custom_filename:
        template_path: Path = Path(github_workspace_dir) / Path(custom_filename)
        logging.info("Loading template file: %s", template_path)
        with template_path.open() as f:
            template_data: str = f.read()
    else:
        logging.info("Loading default template: %s", default_filename)
        template_data = (
            pkg_resources.resource_string("lineage", f"templates/{default_filename}")
            .decode("utf-8")
            .strip()
        )
    return template_data


def get_repo_list(
    g: Github, repo_query: str
) -> Generator[Repository.Repository, None, None]:
    """Generate a list of repositories based on the query."""
    logging.info("Querying for repositories: %s", repo_query)
    # Sometimes there is an issue with the pagination of results from the
    # call to `Github.search_repositories()` that causes repositories on page
    # breaks to be duplicated when iterating over results. The only issue I could
    # find that referenced this problem is
    # https://github.com/PyGithub/PyGithub/issues/1748,
    # which suggests that adding the sort="updated" parameter to the
    # `Github.search_repositories()` call helps. Hence I am adding it here.
    #
    # See also pull request #33 in this repository:
    # https://github.com/cisagov/action-lineage/pull/33
    matching_repos = g.search_repositories(query=repo_query, sort="updated")
    for repo in matching_repos:
        yield repo


def get_config(repo: Repository.Repository) -> Optional[dict]:
    """Read the lineage configuration for this repo without checking it out."""
    config_url: str = f"https://raw.githubusercontent.com/{repo.full_name}/{repo.default_branch}/{CONFIG_FILENAME}"
    logging.debug("Checking for config at: %s", config_url)
    response = requests.get(config_url)
    if response.status_code == 200:
        return yaml.safe_load(response.content)
    else:
        return None


def switch_branch(
    repo: Repository.Repository, lineage_id: str, local_branch: str
) -> Tuple[str, bool]:
    """Switch to the PR branch, and possibly create it."""
    branch_name = f"lineage/{lineage_id}"
    logging.info("Attempting to switch to branch: %s", branch_name)
    proc = run([GIT, "switch", branch_name], cwd=repo.full_name, on_error=OnError.OK)
    if proc.returncode:
        # branch does not exist, create it
        logging.info(
            "Branch did not exist.  Creating: %s from local %s",
            branch_name,
            local_branch,
        )
        logging.info("Creating branch %s from %s", branch_name, local_branch)
        # ignore typing on local_branch, it is has been set above if None
        run([GIT, "branch", branch_name, local_branch], cwd=repo.full_name)  # type: ignore
        logging.info("Switching to %s", branch_name)
        run([GIT, "switch", branch_name], cwd=repo.full_name)
        return branch_name, True  # branch is new
    else:
        return branch_name, False  # branch existed


def fetch(repo: Repository.Repository, remote_url: str, remote_branch: Optional[str]):
    """Fetch commits from remote branch."""
    if remote_branch:
        logging.info("Fetching %s %s", remote_url, remote_branch)
        run([GIT, "fetch", remote_url, remote_branch], cwd=repo.full_name)
    else:
        logging.info("Fetching %s", remote_url)
        run([GIT, "fetch", remote_url], cwd=repo.full_name)


def merge(repo: Repository.Repository, github_actor: str) -> Tuple[bool, List[str]]:
    """Merge previously fetched commits."""
    conflict_file_list: List[str] = []
    logging.debug("Setting git user.name %s", github_actor)
    proc = run([GIT, "config", "user.name", github_actor], cwd=repo.full_name)
    logging.debug("Setting git user.email %s@github.com", github_actor)
    proc = run(
        [GIT, "config", "user.email", f"{github_actor}@github.com"],
        cwd=repo.full_name,
    )
    logging.info("Attempting merge of fetched changes.")
    proc = run(
        [GIT, "merge", "--no-commit", "FETCH_HEAD"],
        cwd=repo.full_name,
        on_error=OnError.OK,
    )
    conflict: bool = proc.returncode != 0
    if UNRELATED_HISTORY in proc.stdout.decode():
        logging.warning("Repository lineage is incorrect.  Merge refused.")
        core.warning("Repository lineage is incorrect.", title=repo.full_name)
        return False, conflict_file_list
    if ALREADY_UP_TO_DATE in proc.stdout.decode():
        logging.info("Branch is already up to date.")
        return False, conflict_file_list
    if conflict:
        logging.info("Conflict detected during merge.  Collecting conflicted files.")
        proc = run([GIT, "diff", "--name-only", "--diff-filter=U"], cwd=repo.full_name)
        conflict_file_list = proc.stdout.decode().split()
        logging.info("Adding conflicts into branch for later resolution.")
        run([GIT, "add", "."], cwd=repo.full_name)
    # Make sure a modification to the lineage configuration is not in the FETCH_HEAD
    logging.info("Remove any incoming modifications to %s", CONFIG_FILENAME)
    run(
        [GIT, "reset", "HEAD", "--", CONFIG_FILENAME],
        cwd=repo.full_name,
    )
    run(
        [GIT, "checkout", "--", CONFIG_FILENAME],
        cwd=repo.full_name,
    )
    logging.info("Committing merge.")
    run([GIT, "commit", "--file=.git/MERGE_MSG"], cwd=repo.full_name)
    return True, conflict_file_list


def push(
    repo: Repository.Repository, branch_name: str, username: str, password: str
) -> bool:
    """Push changes to remote."""
    if not repo.permissions.push:
        logging.warning(
            "⚠️ WARNING! Missing 'push' permission on '%s'",
            repo.full_name,
        )
        core.warning(
            "Missing 'push' permission.",
            title=repo.full_name,
        )
        return False
    else:
        parts: ParseResult = urlparse(repo.clone_url)
        cred_url = parts._replace(
            netloc=f"{username}:{password}@{parts.netloc}"
        ).geturl()
        logging.info("Assigning credentials for push.")
        run([GIT, "remote", "set-url", "origin", cred_url], cwd=repo.full_name)
        logging.info("Pushing %s to remote.", branch_name)
        run([GIT, "push", "--set-upstream", "origin", branch_name], cwd=repo.full_name)
        return True


def create_pull_request(
    repo: Repository.Repository,
    pr_branch_name: str,
    local_branch: str,
    title: str,
    body: str,
    draft: bool,
):
    """Create a pull request."""
    logging.info("Creating a new pull request in %s", repo.full_name)
    pull_request: PullRequest.PullRequest = repo.create_pull(
        title=title, head=pr_branch_name, base=local_branch, body=body, draft=draft
    )
    # Assign code owners to pull request
    for owner in get_code_owners(repo):
        logging.info("Assigning code owner %s to pull request.", owner)
        pull_request.add_to_assignees(owner)

    # Build a list of labels to add from the labels available in the repository
    # and the list of desired labels
    repo_labels = repo.get_labels()
    pr_labels = [label for label in repo_labels if label.name in PR_LABEL_NAMES]
    if pr_labels:
        # Assign desired labels to pull request
        pull_request.add_to_labels(*pr_labels)


def get_code_owners(repo: Repository.Repository) -> Generator[str, None, None]:
    """Get the code owners for this repo."""
    config_url: str = f"https://raw.githubusercontent.com/{repo.full_name}/{repo.default_branch}/{CODEOWNERS_FILENAME}"
    logging.debug("Checking for code owners at: %s", config_url)
    response = requests.get(config_url)
    if response.status_code == 200:
        lines = response.content.decode().split("\n")
        for line in lines:
            if not line.strip() or line.startswith("#"):
                # skip comments and empty lines
                continue
            # We're just going to take the first line of code code_owners
            # It looks like:
            # *       @dav3r @felddy @hillaryj @jsf9k @mcdonnnj @cisagov/team-ois
            # Drop the *, and skip any teams
            items = line.split()[1:]
            for item in items:
                if "/" in item:  # it's a team
                    continue
                # it's a person, drop @ sign
                yield item[1:]
            # Only process the first line with content
            break


def has_existing_pr(repo: Repository.Repository, branch_name: str) -> bool:
    """Check if an open PR already exists for the lineage branch."""
    # By default only open Pull Requests are returned
    pull_requests = repo.get_pulls()
    for pr in pull_requests:
        if pr.head.ref == branch_name:
            return True
    return False


def main() -> None:
    """Parse environment and perform requested actions."""
    # Set up logging. Force logging output to stdout to allow for GitHub Actions
    # commands to interact with output.
    logging.basicConfig(
        format="%(levelname)s %(message)s", level=logging.INFO, stream=sys.stdout
    )

    # Get inputs from the environment
    access_token: Optional[str] = core.get_input("access_token")
    github_actor: Optional[str] = os.environ.get("GITHUB_ACTOR")
    github_workspace_dir: Optional[str] = os.environ.get("GITHUB_WORKSPACE")
    mask_non_public: bool = core.get_boolean_input("mask_non_public_repos")
    repo_query: Optional[str] = core.get_input("repo_query")
    include_non_public: bool = core.get_boolean_input("include_non_public_repos")

    # sanity checks
    if access_token is None:
        logging.fatal(
            "Access token environment variable must be set. (INPUT_ACCESS_TOKEN)"
        )
        core.error("Missing required input: access_token", title="Initialization error")
        sys.exit(-1)

    if github_actor is None:
        logging.fatal("GitHub actor environment variable must be set. (GITHUB_ACTOR)")
        core.error(
            "GitHub actor environment variable must be set. (GITHUB_ACTOR)",
            title="Initialization error",
        )
        sys.exit(-1)

    if github_workspace_dir is None:
        logging.fatal(
            "GitHub workspace environment variable must be set. (GITHUB_WORKSPACE)"
        )
        core.error(
            "GitHub workspace environment variable must be set. (GITHUB_WORKSPACE)",
            title="Initialization error",
        )
        sys.exit(-1)

    if repo_query is None:
        logging.fatal(
            "Repository query environment variable must be set. (INPUT_REPO_QUERY)"
        )
        core.error("Missing required input: repo_query", title="Initialization error")
        sys.exit(-1)

    # Ensure we are working in our workspace
    os.chdir(github_workspace_dir)

    # Create a Github access object
    g = Github(access_token)

    # Set up a session to do things the Github library has not yet implemented.
    session: requests.Session = requests.Session()
    session.auth = ("", access_token)

    clean_template = load_template(github_workspace_dir, "clean_template.md", None)
    conflict_template = load_template(
        github_workspace_dir, "conflict_template.md", None
    )

    repos = get_repo_list(g, repo_query)
    for repo in repos:
        # Extra controls if the repo is private
        if repo.private:
            if not include_non_public:
                continue
            # Ensure that non-public repo names do not show up in the logs
            if mask_non_public:
                core.set_secret(repo.full_name)
        core.start_group(repo.full_name)
        logging.info("Checking: %s", repo.full_name)
        config = get_config(repo)
        if not config:
            logging.info("Lineage configuration not found for %s", repo.full_name)
            core.end_group()
            continue
        logging.info("Lineage configuration found for %s", repo.full_name)
        logging.info("Cloning repository: %s", repo.clone_url)
        # The failure of a repository to clone should not cause the entire
        # run to fail. See related comment above in the body of the
        # get_repo_list() function for an example of such a case which caused an
        # exception with the following error when attempting to clone:
        # fatal: destination path 'repo_full_name' already exists and is not an
        # empty directory.
        #
        # See also pull request #33 in this repository:
        # https://github.com/cisagov/action-lineage/pull/33
        try:
            run([GIT, "clone", repo.clone_url, repo.full_name])
        except Exception:
            logging.exception("Unable to clone %s.", repo.full_name)
            core.end_group()
            continue
        lineage_id: str
        local_branch: str
        remote_branch: Optional[str]
        remote_url: str
        if config.get("version") != "1":
            base_message = "Incompatible config version: %s"
            logging.warning(base_message, config.get("version"))
            core.warning(
                base_message % config.get("version"),
                title=repo.full_name,
            )
            core.end_group()
            continue
        if "lineage" not in config:
            base_message = "Could not find 'lineage' key in config."
            logging.warning(base_message)
            core.warning(base_message, title=repo.full_name)
            core.end_group()
            continue
        for lineage_id, v in config["lineage"].items():
            logging.info("Processing lineage: %s", lineage_id)
            try:
                local_branch = v.get("local-branch")
                remote_branch = v.get("remote-branch", "HEAD")
                remote_url = v["remote-url"]
            except KeyError:
                logging.exception("Missing config key while reading %s: %s", lineage_id)
                continue
            # if a local_branch is not specified use the repo default
            if not local_branch:
                local_branch = repo.default_branch

            logging.info("Upstream: %s %s", remote_url, remote_branch or "")
            # Check to see if a PR branch already exists
            branch_is_new: bool
            branch_name: str
            pr_branch_name, branch_is_new = switch_branch(
                repo, lineage_id, local_branch
            )
            logging.info("Pull request branch is new: %s", branch_is_new)
            # If the branch already exists, then check if a PR exists
            if not branch_is_new and not has_existing_pr(repo, pr_branch_name):
                core.warning(
                    "There is no pull request for the existing Lineage branch.",
                    title=repo.full_name,
                )
            fetch(repo, remote_url, remote_branch)
            changed: bool
            conflict_file_list: List[str]
            changed, conflict_file_list = merge(repo, github_actor)
            if not changed:
                logging.info(
                    "Already up to date with: %s %s", remote_url, remote_branch or ""
                )
                continue
            # If we can successfully push, continue with generating a PR
            if push(repo, pr_branch_name, "git", access_token):
                if branch_is_new:
                    logging.info("Creating a new pull request since branch is new.")
                    template_data = {
                        "conflict_file_list": conflict_file_list,
                        "lineage_id": lineage_id,
                        "local_branch": local_branch,
                        "metadata": PR_METADATA,
                        "pr_branch_name": pr_branch_name,
                        "remote_branch": remote_branch,
                        "remote_url": remote_url,
                        "repo_name": repo.name,
                        "ssh_url": repo.ssh_url,
                    }
                    if conflict_file_list:
                        title = f"⚠️ CONFLICT! Lineage pull request for: {lineage_id}"
                        body = chevron.render(conflict_template, template_data)
                        create_pull_request(
                            repo, pr_branch_name, local_branch, title, body, draft=True
                        )
                    else:
                        title = f"Lineage pull request for: {lineage_id}"
                        body = chevron.render(clean_template, template_data)
                        create_pull_request(
                            repo, pr_branch_name, local_branch, title, body, draft=False
                        )
                else:
                    logging.warning(
                        "Not creating a new pull request because the branch already exists."
                    )
            else:
                logging.warning(
                    "Not creating a new pull request because of insufficient permissions."
                )
        core.end_group()

    logging.info("Completed.")
