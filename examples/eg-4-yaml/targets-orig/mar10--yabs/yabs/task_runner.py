# -*- coding: utf-8 -*-
# (c) 2020-2022 Martin Wendt and contributors; see https://github.com/mar10/yabs
# Licensed under the MIT license: https://www.opensource.org/licenses/mit-license.php
"""
"""
import time
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List, Union

import yaml
from git import Repo
from snazzy import emoji, gray, green, red, wrap, yellow

from yabs import __version__ as yabs_version
from yabs.util import assert_always

from .plugin_manager import PluginManager
from .task.common import ErrorTaskResult, OkTaskResult, TaskContext, _TaskResult
from .util import (
    CONFIG_NAME,
    NO_DEFAULT,
    ConfigError,
    check_arg,
    check_dict_keys,
    format_elap,
    log_debug,
    log_error,
    log_info,
    log_ok,
    log_warning,
    progress_bar_str,
    search_file_upward,
    to_list,
    to_set,
)
from .version_manager import VersionFileManager


class TaskInstance:
    STATUSES = _TaskResult.VALID_RESULTS.union({"pending", "running"})

    def __init__(self, task_runner: "TaskRunner", index: int, task_def: dict) -> None:
        #: TaskRunner instance
        self.task_runner: TaskRunner = task_runner
        #: Index of the task in the workflow definition (1-based)
        self.index: int = index
        #: Task definition from yaml file as dict (reference to yaml entry)
        self.org_task_def: dict = task_def
        #: Task defition from yaml file as dict (shallow copy to prevent changes)
        self.task_def: dict = task_def.copy()
        #: Task name from yaml file (e.g. 'github_release')
        self.name: str = task_def["task"]
        #: Result of the executed task (None if not yet run)
        self.result: _TaskResult = None
        #: Time stamp  of start (None if not yet run)
        self.started: float = None
        #: Time stamp  of end (None if pending or still running)
        self.elap: float = None
        #: String representation of this task in its current state
        self.task_str: str = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(#{self.index}, {self.name})({self.result or self.status})"

    def __str__(self) -> str:
        status = self.status
        result = self.result
        task_name = self.task_str or f"'{self.name}'"
        msg = result.message if result else f"{status.capitalize()}..."
        return f"#{self.index:<2} {task_name}: {msg}"

    @property
    def status(self) -> str:
        if self.result is None:
            return "pending" if self.started is None else "running"
        return self.result.status

    def start(self, task_str: str):
        self.task_str = task_str
        self.started = time.monotonic()

    def set_result(self, task_str: str, result: Union[bool, _TaskResult]):
        check_arg(result, (bool, _TaskResult))

        self.task_str = task_str
        self.elap = time.monotonic() - self.started

        if result is True:
            result = OkTaskResult(msg="Ok.")
        elif result is False:
            result = ErrorTaskResult(msg="Failed.")

        check_arg(result, _TaskResult)
        self.result = result


class TaskRunner:
    """"""

    def __init__(
        self,
        fspec: str,
        parser: ArgumentParser = None,
        args: Namespace = None,
        *,
        pick_tasks: Union[set, list, tuple, str] = None,
    ):
        #: Path of yabs.yaml
        self.fspec: Path = None
        #: (ArgumentParser) May be None if not run from command line
        self.parser: Union[ArgumentParser, None] = parser
        #: (Namespace) Command line arguments (or None if not run from command line)
        #: Use `cli_arg()` to access
        self._args: Union[Namespace, None] = args
        #: (set, optional) If defined, only these task-types are run
        self.pick_tasks = to_set(pick_tasks, or_none=True)
        #: Value of `yabs COMMAND ...` (None if not running as CLI)
        self.command: str = self.cli_arg("cmd_name")
        #: The complete YAML file as dict
        self.yaml: dict = None
        #: The 'config' section of the YAML file
        self.config: dict = None
        #: The 'tasks' section of the YAML file
        self.tasks: dict = None
        #: List of all scheduled or executed tasks
        self.task_instances: List[TaskInstance] = []
        #: The VersionManager instance
        self.version_manager: VersionFileManager = None
        #: Timestamp uf start of `run()` (None if not yet started)
        self.start: float = None
        #: Timestamp uf end  of `run()` (None if not yet completed)
        self.elap: float = None
        #: (bool) Log workflow status overview at the end
        self.log_final_progress: bool = True
        #: Lines that will be logged at the end
        self.summaries: List[str] = []

        self.fspec = search_file_upward(fspec, CONFIG_NAME, or_none=True)
        if not self.fspec:
            parser.error(
                f"Could not locate `{CONFIG_NAME}` in {fspec} or parent folders."
            )

        self._load()

    def get_task_instances(
        self, task_type: str, *, status: Union[str, list, tuple, set, None] = None
    ) -> Union[List[TaskInstance], None]:
        status = to_set(status)
        tis = [
            ti
            for ti in self.task_instances
            if ti.name == task_type and (not status or ti.status in status)
        ]
        return tis

    def get_first_task_instance(
        self,
        task_type: str,
        *,
        status: Union[str, list, tuple, set, None] = None,
        check_single=False
    ) -> Union[TaskInstance, None]:
        tis = self.get_task_instances(task_type, status=status)
        if check_single and len(tis) > 1:
            raise RuntimeError(f"More than one instance found: {tis}")
        return tis[0] if tis else None

    def cli_arg(self, key: str, default=None):
        """Return a value from command line args.

        Tasks must handle the case that `args` is undefined when not running
        as CLI or the command is "info" instead of "running" for example.
        """
        if default is NO_DEFAULT:
            # Raise an error if args is None or does not have the key:
            return getattr(self._args, key)
        elif self._args is not None:
            return getattr(self._args, key, default)
        return default

    def get_config(self, key: str, default=NO_DEFAULT):
        """Return a value from the YAMLs `config` section."""
        try:
            return self.config[key]
        except KeyError:
            if default is NO_DEFAULT:
                raise
        return default

    def add_summary(self, msg: str) -> None:
        """Add a line that will be logged at the end."""
        self.summaries.append(msg)

    def _load(self):
        with open(self.fspec, "rt") as f:
            try:
                res = yaml.safe_load(f)
            except yaml.parser.ParserError as e:
                raise RuntimeError("Could not parse YAML: {}".format(e)) from None

        if not isinstance(res, dict) or not res.get("file_version", "").startswith(
            "yabs#"
        ):
            raise ConfigError("Not a `yabs` file (missing 'yabs#VERSION' tag).")
        self.yaml = res

        self.config = res["config"]
        check_arg(self.config, dict)

        self.tasks = res["tasks"]
        check_arg(self.tasks, list)

        self.version_manager = VersionFileManager(self)

        validation_errors = self._check_yaml()

        # Prepare one instance per workflow task
        for index, task_def in enumerate(self.tasks, 1):
            self.task_instances.append(TaskInstance(self, index, task_def))

        validation_errors.extend(self._pre_check_config())

        validation_errors.extend(self._pre_check_all_task_configs())

        if validation_errors:
            findings = "\n  - ".join(validation_errors)
            raise ConfigError(
                f"Found {len(validation_errors)} errors in {self.fspec}:\n  - {findings}"
            )
        return

    def _check_yaml(self) -> List[str]:
        errors = check_dict_keys(
            self.config,
            known={
                "branches",
                "gh_auth",
                "max_increment",
                "repo",
                "version",  # Version location configuration
                "yabs_version",  # Semver specifier for expecte Yabs version
            },
            mandatory={
                "repo",
            },
            prefix="",
            key_prefix="config.",
        )
        return errors

    def _check_branch(self, allowed_branches):
        if not allowed_branches:
            return
        git_repo = Repo(self.fspec, search_parent_directories=True)
        branches = to_list(allowed_branches)
        cur_branch = git_repo.active_branch.name
        if cur_branch not in branches:
            return (
                f"On branch {red(cur_branch)} "
                f"(not in allowed list: '{', '.join(branches)}')."
            )
        return

    def _pre_check_config(self) -> List[str]:
        errors = []

        branches = self.config.get("branches")
        check_arg(branches, (str, list, tuple), or_none=True)
        if self.command != "info":
            err = self._check_branch(branches)
            if err:
                errors.append(err)
        return errors

    def _pre_check_all_task_configs(self) -> List[str]:
        """Early option and command line syntax checks.

        This is done after reading the YAML and parsing the command line,
        but before the workflow starts.
        Note that `parser` and `args` may be None, when the TaskRunner was
        created by a script (or test fixture).
        """
        errors = []

        for task_inst in self.task_instances:
            task_def = task_inst.task_def
            task_type = task_def["task"]

            task_cls = PluginManager.task_class_map.get(task_type)
            if task_cls is None:
                errors.append("Invalid task type: '{task_type}': {task_def}")
                continue

            # Check if mandatory opts are set, and unknown opts are not set:
            err_list = task_cls._check_default_opts(self, task_def, task_inst.index)
            if err_list:
                errors.extend(err_list)

            # Let overridden clasmethods do some custom checks:
            res = task_cls.check_task_def(task_inst)
            if res in (None, True):
                continue
            elif res is False:
                res = f"{task_cls}({task_def}): precheck failed."

            if isinstance(res, str):
                res = [res]

            check_arg(res, (list, tuple), or_none=True)
            errors.extend(res)

        return errors

    def _log_task_instances(self) -> None:
        def ftm_run(s):
            return wrap(s, "cyan", bold=True)

        _prefix_map = {
            "pending": ("{}".format(emoji("⌛", gray("P"))), gray),
            "running": ("{}".format(emoji("🏃", yellow("R"))), ftm_run),
            "ok": ("{}".format(emoji("✅", green("*"))), green),
            "skip": ("{}".format(emoji("🟢", gray("S"))), gray),
            "warning": ("{}".format(emoji("❗", yellow("!"))), yellow),
            "error": ("{}".format(emoji("❌", red("X"))), red),
        }
        wf_elap = time.monotonic() - self.start if self.elap is None else self.elap
        count = len(self.task_instances)
        done_count = sum((1 for t in self.task_instances if t.result is not None))
        skip_count = sum((1 for t in self.task_instances if t.status == "warning"))
        warn_count = sum((1 for t in self.task_instances if t.status == "warning"))
        err_count = sum((1 for t in self.task_instances if t.status == "error"))

        summary = f"{done_count}/{count} tasks in {format_elap(wf_elap)}"
        if skip_count:
            summary += ", " + gray(f"{skip_count} skipped")
        if warn_count:
            summary += ", " + yellow(f"{warn_count} warnings")
        if err_count:
            summary += ", " + red(f"{err_count} errors")
        log_info(f"Run {summary}:")

        for inst in self.task_instances:
            prefix, wrapper = _prefix_map[inst.status]
            rate = inst.elap / wf_elap if inst.elap else 0
            bar = progress_bar_str(rate, width=5)
            elap = (
                "n.a."
                if inst.elap is None
                else format_elap(inst.elap, short_suffix=True)
            )
            print(f"  {prefix} {bar},  {elap:>8}:  {wrapper(inst)}")
        return

    def log_header_info(self, *, context):
        # if context is None:
        #     context = TaskContext(self)

        wv = green

        def wt(s):
            return wrap(s, bg="green")

        log_info("")
        log_info(f"Yabs v{yabs_version}, configuration: {self.fspec}")
        # cmd_line = " ".join(sys.argv)
        # log_info(f"Running Yabs v{yabs_version}:\n    {cmd_line}")
        # log_info(f"Configuration: {self.fspec}")
        log_info("")
        log_info(
            f"Project '{wv(context.repo_short)}', "
            f"current version {wv('v'+str(context.version))}, "
            f"latest tag: {wt(context.org_tag_name)}"
        )

        branches = self.config.get("branches")
        err = self._check_branch(branches)
        if err:
            log_info(err)
        else:
            log_info(f"On branch {wv(context.repo_obj.active_branch.name)}.")

        log_info("")
        # Latest tag: TAG
        # Parsed version from PATH (VERSION)

    def run(self):
        assert_always(self.start is None)

        context = TaskContext(self)
        task_map = PluginManager.task_class_map

        # --- Write Header -----------------------------------------------------
        self.log_header_info(context=context)

        # --- Write Header -----------------------------------------------------

        ok = True
        self.start = time.monotonic()

        for task_instance in self.task_instances:
            task_def = task_instance.task_def
            # task_def = task_def.copy()
            # log_info(task_def)

            task_type = task_def.pop("task")
            task_cls = task_map.get(task_type)
            if not task_cls:
                raise ConfigError(
                    "Invalid task type: {} (expected {})".format(
                        task_type, ", ".join(task_map.keys())
                    )
                )
            # TODO: task_def can force - but not prevent - dry-run:
            task_def["dry_run"] = self.cli_arg("dry_run")

            verbose = self.cli_arg("verbose", 3)
            task_def["verbose"] = verbose

            task = task_cls(task_instance)

            task_str = task.to_str(context)
            log_debug(f"Running {task_str}: { task.opts}...")

            task_instance.start(task_str)

            if verbose >= 3 and self.cli_arg("progress"):
                self._log_task_instances()

            try:
                res = task.run(context)
            except Exception as e:
                log_error(f"{task_instance} failed: {e}")
                raise

            task_str = task.to_str(context)  # __str__ may have changed
            task_instance.set_result(task_str, res)

            elap_str = format_elap(task_instance.elap)

            if res:
                log_ok(f"{task_str} took {elap_str}")
            else:
                log_error(f"{task_str} failed after {elap_str}")
                context.errors.append(task_str)
                ok = False
                # if not args.force_continue:
                break

        self.elap = time.monotonic() - self.start
        total_elap_str = format_elap(self.elap)

        if verbose >= 3 and self.log_final_progress:
            self._log_task_instances()

        for line in self.summaries:
            log_info(line)

        if ok:
            log_ok(
                "Workflow finished successfully in {}{}".format(
                    total_elap_str, emoji(" ✨ 🍰 ✨")
                )
            )
        else:
            msg = "Workflow failed in {}{}".format(total_elap_str, emoji(" 💥 💔 💥"))
            log_error(msg)
            context.errors.append(msg)

        if self.cli_arg("dry_run"):
            log_warning(
                "Dry-Run mode: No bits were harmed during the making of this release."
            )
        return ok
