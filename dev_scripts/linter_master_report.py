#!/usr/bin/env python

import argparse
import logging
import os
import sys
from typing import Optional, Tuple

import helpers.git as git
import helpers.io_ as io_
import helpers.parser as prsr
import helpers.system_interaction as si

_LOG = logging.getLogger(__name__)


def _calculate_stats(
    base_commit_sha: str,
    head_commit_sha: str,
    head_branch_name: str,
    build_url: Optional[str] = None,
) -> Tuple[int, str]:
    """

    :param base_commit_sha: Respect to this commit or branch will be compared.
    :param head_commit_sha:
    :param head_branch_name:
    :param build_url:
    """
    # Calculate stats
    dir_name = "."
    # TODO: Think about it.
    remove_files_non_present = False
    mod_files = git.get_modified_files_in_branch(
        dir_name,
        base_commit_sha,
        remove_files_non_present=remove_files_non_present,
    )
    # _LOG.info("modirty: %s", master_dirty)
    cmd = f"linter.py -t {base_commit_sha} --post_check"
    branch_dirty = si.system(cmd, abort_on_error=False)
    _LOG.info("Branch dirty: %s", branch_dirty)
    #
    cmd = "git reset --hard"
    si.system(cmd)
    #
    cmd = f"linter.py -t {base_commit_sha}"
    branch_lints = si.system(cmd, abort_on_error=False)
    _LOG.info("Branch lints: %s", branch_lints)
    #
    linter_output_filename = "./linter_warnings.txt"
    # TODO: Rename -> linter_message
    lints_message = io_.from_file(linter_output_filename)
    lints_message = "```\n" + lints_message + "\n```\n"

    # # Calculate "Before*" stats
    cmd = "git reset --hard"
    si.system(cmd)
    cmd = f"git checkout {base_commit_sha} --recurse-submodules"
    si.system(cmd)
    mod_files_as_str = " ".join(mod_files)
    cmd = f"linter.py --files {mod_files_as_str} --post_check"
    master_dirty = si.system(cmd, abort_on_error=False)
    _LOG.info("Master dirty: %s", master_dirty)
    #
    cmd = "git reset --hard"
    si.system(cmd)
    cmd = f"linter.py --files {mod_files_as_str}"
    master_lints = si.system(cmd, abort_on_error=False)
    _LOG.info("Master lints: %s", master_lints)
    # Prepares a message and exit status
    master_dirty_status = master_dirty > 0
    exit_status = 0
    errors = []
    branch_dirty_status = branch_dirty > 0
    if branch_dirty_status:
        errors.append("**ERROR**: Run `linter.py. -b` locally before merging.")
        exit_status = 1
    if master_lints > 0:
        errors.append("**WARNING**: Your branch has lints. Please fix them.")
    if branch_lints > master_lints:
        exit_status = 1
        errors.append("**ERROR**: You introduced more lints. Please fix them.")
    # Message
    message = list()
    message.append("# Results of the linter build")
    console_url = os.path.join(str(build_url), "consoleFull")
    if build_url is not None:
        console_message = f"Console output: {console_url}"
    else:
        console_message = "Console output: No console output"
    message.append(console_message)
    message.append(f"- Master (sha: {base_commit_sha})")
    message.append(f"\t- Number of lints: {master_lints}")
    message.append(f"\t- Dirty (i.e., linter was not run): {master_dirty_status}")
    message.append(f"- Branch ({head_branch_name}: {head_commit_sha})")
    message.append(f"\t- Number of lints: {branch_lints}")
    message.append(f"\t- Dirty (i.e., linter was not run): {branch_dirty_status}")
    diff_lints = branch_lints - master_lints
    message.append(
        f"\nThe number of lints introduced with this change: {diff_lints}"
    )
    message = "\n".join(message)
    message += "\n\n" + "\n".join(errors)
    message += "\n" + lints_message

    return exit_status, message


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Select files.
    parser.add_argument(
        "--jenkins", action="store_true", help="",
    )
    parser.add_argument("--base_commit_sha", type=str, required=False, help="")
    parser.add_argument("--head_branch_name", type=str, required=False, help="")
    parser.add_argument("--head_commit_sha", type=str, required=False, help="")

    prsr.add_verbosity_arg(parser)
    return parser


def _main(args: argparse.Namespace) -> int:
    build_url = None
    if args.jenkins:
        base_commit_sha = os.environ["data_pull_request_base_sha"]
        head_branch_name = os.environ["data_pull_request_head_ref"]
        head_commit_sha = os.environ["data_pull_request_head_sha"]
        build_url = os.environ["BUILD_URL"]
    else:
        base_commit_sha = args.base_commit_sha or "master"
        head_branch_name = args.head_branch_name or git.get_branch_name()
        head_commit_sha = args.head_commit_sha or git.get_current_commit_hash()
    rc, message = _calculate_stats(
        base_commit_sha, head_commit_sha, head_branch_name, build_url
    )
    if args.jenkins:
        io_.to_file("./tmp_message.txt", message)
        io_.to_file("./tmp_exit_status.txt", str(rc))
    else:
        print(message)
        cmd = "git reset --hard"
        si.system(cmd)
        cmd = f"git checkout {head_branch_name} --recurse-submodules"
        si.system(cmd)
    return rc


if __name__ == "__main__":
    parser_ = _parse()
    args_ = parser_.parse_args()
    rc_ = _main(args_)
    sys.exit(rc_)
