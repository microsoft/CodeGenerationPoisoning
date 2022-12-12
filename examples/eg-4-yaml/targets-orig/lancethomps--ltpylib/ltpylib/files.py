#!/usr/bin/env python
# pylint: disable=C0111
import itertools
import json
import os
import re
import sys
from pathlib import Path
from subprocess import CalledProcessError
from typing import AnyStr, Callable, List, Match, Optional, Pattern, Sequence, Set, Tuple, Union

from ltpylib import inputs, logs, procs, strings
from ltpylib.common_types import TypeWithDictRepr
from ltpylib.macos import pbcopy


def convert_to_path(path: Union[Path, str]) -> Path:
  if isinstance(path, str):
    return Path(path)

  return path


def convert_to_path_expandvars(path: Union[Path, str]) -> Path:
  if isinstance(path, str):
    return Path(os.path.expandvars(path))

  return path


def replace_matches_in_file(
  file: Union[str, Path],
  search_string: str,
  replacement: Union[str, Callable[[Match], str]],
  quote_replacement: Union[bool, str] = False,
  wrap_replacement_in_function: Union[bool, str] = False,
  force_replace: bool = False,
  flags: Union[int, re.RegexFlag] = 0,
) -> bool:
  if isinstance(quote_replacement, str):
    quote_replacement = strings.convert_to_bool(quote_replacement)

  if isinstance(wrap_replacement_in_function, str):
    wrap_replacement_in_function = strings.convert_to_bool(wrap_replacement_in_function)

  if isinstance(force_replace, str):
    force_replace = strings.convert_to_bool(force_replace)

  if isinstance(flags, str):
    flags = strings.convert_to_number(flags)

  if quote_replacement and isinstance(replacement, str):
    replacement = re.escape(replacement)
  elif wrap_replacement_in_function and isinstance(replacement, str):
    replacement_content = replacement

    def replacement_function(match: Match) -> str:
      return replacement_content

    replacement = replacement_function

  content = read_file(file)
  content_new = re.sub(search_string, replacement, content, flags=flags)

  if content != content_new:
    write_file(file, content_new)
    return True
  elif force_replace and re.search(search_string, content, flags=flags):
    write_file(file, content_new)
    return True

  return False


def replace_strings_in_file(
  file: Union[str, Path],
  search_string: str,
  replacement: str,
  count: int = -1,
  force_replace: bool = False,
) -> bool:
  if isinstance(count, str):
    count = strings.convert_to_number(count)

  if isinstance(force_replace, str):
    force_replace = strings.convert_to_bool(force_replace)

  content: str = read_file(file)
  content_new = content.replace(search_string, replacement, count)

  if content != content_new:
    write_file(file, content_new)
    return True
  elif force_replace and search_string in content:
    write_file(file, content_new)
    return True

  return False


def remove_matching_lines_in_file(
  file: Union[str, Path],
  search_string: str,
  quote_search_string: bool = False,
  flags: Union[int, re.RegexFlag] = 0,
) -> bool:
  if isinstance(quote_search_string, str):
    quote_search_string = strings.convert_to_bool(quote_search_string)

  if isinstance(flags, str):
    flags = strings.convert_to_number(flags)

  if quote_search_string:
    search_string = re.escape(search_string)

  content: str = read_file(file)
  matcher = re.compile(search_string, flags=flags)
  has_match = False
  new_lines = []
  for line in content.splitlines():
    if matcher.search(line):
      has_match = True
    else:
      new_lines.append(line)

  if has_match:
    write_file(file, "\n".join(new_lines))
    return True

  return False


def chmod_proc(perms: str, file: Union[str, Path]) -> int:
  import subprocess

  file = convert_to_path(file)

  return subprocess.call(["chmod", perms, file.as_posix()])


def read_file(file: Union[str, Path]) -> AnyStr:
  file = convert_to_path(file)

  with open(file.as_posix(), 'r') as fr:
    content = fr.read()
  return content


def read_json_file(file: Union[str, Path]) -> Union[dict, list]:
  file = convert_to_path(file)

  with open(file.as_posix(), 'r') as fr:
    parsed = json.load(fr)

  return parsed


def read_yaml_file(file: Union[str, Path]) -> Union[dict, list]:
  import yaml

  file = convert_to_path(file)

  with open(file.as_posix(), 'r') as fr:
    parsed = yaml.full_load(fr)

  return parsed


def read_file_n_lines(file: Union[str, Path], n_lines: int = -1) -> List[str]:
  file = convert_to_path(file)

  lines: List[str] = []
  with open(file.as_posix()) as fr:
    if n_lines < 0:
      while True:
        line = fr.readline()
        if not line:
          break
        lines.append(line.rstrip('\n'))
    else:
      for n in range(n_lines):
        line = fr.readline()
        if not line:
          break
        lines.append(line.rstrip('\n'))

  return lines


def write_file(file: Union[str, Path], contents: AnyStr):
  file = convert_to_path(file)

  with open(file.as_posix(), 'w') as fw:
    fw.write(contents)


def append_file(file: Union[str, Path], contents: AnyStr):
  file = convert_to_path(file)

  with open(file.as_posix(), 'a') as fw:
    fw.write(contents)


def list_files(base_dir: Path, globs: Union[List[str], str] = ('**/*',)) -> List[Path]:
  if isinstance(globs, str):
    globs = [globs]

  files: Set[Path] = set()
  file: Optional[Path] = None
  for file in list(itertools.chain(*[base_dir.glob(glob) for glob in globs])):
    if file.is_file():
      files.add(file)

  files_list = list(files)
  files_list.sort()
  return files_list


def list_dirs(base_dir: Path, globs: List[str] = ('**/*',)) -> List[Path]:
  dirs: Set[Path] = set()
  child_dir: Optional[Path] = None
  for child_dir in list(itertools.chain(*[base_dir.glob(glob) for glob in globs])):
    if child_dir.is_dir():
      dirs.add(child_dir)

  dirs_list = list(dirs)
  dirs_list.sort()
  return dirs_list


def filter_files_with_matching_line(files: List[Union[str, Path]], regexes: List[Union[str, Pattern]], check_n_lines: int = 1) -> List[Path]:
  filtered: List[Path] = []
  for file in files:
    lines = read_file_n_lines(file, check_n_lines)
    has_match = False
    for line in lines:
      for regex in regexes:
        if re.search(regex, line):
          has_match = True
          break

      if has_match:
        break

    if not has_match:
      filtered.append(file)

  return filtered


def find_children(
  base_dir: Union[Path, str],
  break_after_match: bool = False,
  max_depth: int = -1,
  include_dirs: bool = True,
  include_files: bool = True,
  match_absolute_path: bool = False,
  include_patterns: Sequence[str] = None,
  exclude_patterns: Sequence[str] = None,
  includes: Sequence[str] = None,
  excludes: Sequence[str] = None,
  recursion_include_patterns: Sequence[str] = None,
  recursion_exclude_patterns: Sequence[str] = None,
  recursion_includes: Sequence[str] = None,
  recursion_excludes: Sequence[str] = None
) -> List[Path]:
  if isinstance(base_dir, str):
    top = str(base_dir)
  else:
    top = base_dir.as_posix()

  found_dirs = []
  return _find_children(
    top,
    found_dirs,
    1,
    break_after_match,
    max_depth,
    include_dirs,
    include_files,
    match_absolute_path,
    include_patterns,
    exclude_patterns,
    includes,
    excludes,
    recursion_include_patterns,
    recursion_exclude_patterns,
    recursion_includes,
    recursion_excludes
  )[1]


def _find_children(
  top: str,
  found_dirs: List[Path],
  current_depth: int,
  break_after_match: bool,
  max_depth: int,
  include_dirs: bool,
  include_files: bool,
  match_absolute_path: bool,
  include_patterns: Sequence[str],
  exclude_patterns: Sequence[str],
  includes: Sequence[str],
  excludes: Sequence[str],
  recursion_include_patterns: Sequence[str],
  recursion_exclude_patterns: Sequence[str],
  recursion_includes: Sequence[str],
  recursion_excludes: Sequence[str]
) -> Tuple[bool, List[Path]]:
  from ltpylib import filters

  found_match = False
  scandir_it = os.scandir(top)
  dirs = []

  with scandir_it:
    while True:
      try:
        try:
          entry = next(scandir_it)
        except StopIteration:
          break
      except OSError:
        return found_match, found_dirs

      try:
        is_dir = entry.is_dir()
      except OSError:
        # If is_dir() raises an OSError, consider that the entry is not
        # a directory, same behaviour than os.path.isdir().
        is_dir = False

      if is_dir and not include_dirs:
        continue
      elif not is_dir and not include_files:
        continue

      child = entry.name
      full_path = os.path.join(top, child)
      test_value = child if not match_absolute_path else full_path
      include = filters.should_include(
        test_value,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        includes=includes,
        excludes=excludes,
      )

      if include:
        found_match = True
        found_dirs.append(Path(full_path))
        if break_after_match:
          break

      if is_dir:
        include_child = filters.should_include(
          test_value,
          include_patterns=recursion_include_patterns,
          exclude_patterns=recursion_exclude_patterns,
          includes=recursion_includes,
          excludes=recursion_excludes,
        )
        if include_child:
          dirs.append(child)

  if (max_depth <= -1 or current_depth < max_depth) and (not found_match or not break_after_match):
    for dirname in dirs:
      _find_children(
        os.path.join(top, dirname),
        found_dirs,
        current_depth + 1,
        break_after_match,
        max_depth,
        include_dirs,
        include_files,
        match_absolute_path,
        include_patterns,
        exclude_patterns,
        includes,
        excludes,
        recursion_include_patterns,
        recursion_exclude_patterns,
        recursion_includes,
        recursion_excludes
      )

  return found_match, found_dirs


class SplitLine(TypeWithDictRepr):

  def __init__(self, file_name: str, line_number: int = None, content: str = None):
    self.file_name: str = file_name
    self.line_number: int = line_number
    self.content: str = content

  def to_open_arg(self) -> str:
    if self.line_number is not None:
      return "%s:%s" % (self.file_name, self.line_number)

    return self.file_name


class OpenGreppedLines:
  CHOICE_PRINT = "Print"
  CHOICE_COPY = "Copy"
  CHOICE_IDEA = "Open in IntelliJ"
  CHOICE_CODE = "Open in VSCode"
  APP_IDEA = "idea"
  APP_CODE = "code"

  REPLACE_HOME_REGEX = re.compile(r"(?m)^~")
  LINE_NUMBERS_COLON_REGEX = re.compile(r"^(.*\S):(\d+):(.*)")
  LINE_NUMBERS_DASH_REGEX = re.compile(r"^(.*\S)-(\d+)-(.*)")

  def __init__(
    self,
    results: str,
    ask: bool = None,
    line_numbers: bool = None,
    lines_exit_code: int = None,
    open_in_app: str = None,
    select_header: str = None,
    select_lines: bool = None,
    select_preview_file_cmd: str = None,
    skip_code: bool = None,
    skip_copy: bool = None,
    skip_idea: bool = None,
    skip_print: bool = None,
    debug: bool = None,
  ):
    self.ask: bool = ask
    self.line_numbers: bool = line_numbers
    self.lines_exit_code: int = lines_exit_code
    self.open_in_app: str = open_in_app
    self.select_header: str = select_header
    self.select_lines: bool = select_lines
    self.select_preview_file_cmd: str = select_preview_file_cmd
    self.skip_code: bool = skip_code
    self.skip_copy: bool = skip_copy
    self.skip_idea: bool = skip_idea
    self.skip_print: bool = skip_print
    self.debug: bool = debug

    self.results: Optional[str] = None
    if not results or results[0] == "-":
      self.using_stdin: bool = True
      if not self.select_lines:
        self.results: str = sys.stdin.read()
    else:
      self.using_stdin: bool = False
      self.results: str = "\n".join(results)

    if self.results:
      self.results: str = self.results.strip()

    self.original_results: str = self.results
    self.check_for_line_numbers()

  def check_for_line_numbers(self) -> bool:
    if self.line_numbers is None and self.results:
      if ":" in self.results or OpenGreppedLines.LINE_NUMBERS_DASH_REGEX.match(self.results):
        self.line_numbers = True
      else:
        self.line_numbers = False

    return self.line_numbers

  def main(self):

    if self.lines_exit_code != 0:
      print(self.results)
      exit(self.lines_exit_code)

    if self.select_lines:
      self.handle_select_lines()

    if not self.results.strip():
      exit(0)

    if self.ask:
      selected_action: str = self.ask_for_action()
    else:
      selected_action: str = self.open_in_app

    if selected_action == OpenGreppedLines.CHOICE_PRINT:
      self.handle_print()
    elif selected_action == OpenGreppedLines.CHOICE_COPY:
      self.handle_copy()
    elif selected_action in [OpenGreppedLines.CHOICE_IDEA, OpenGreppedLines.APP_IDEA]:
      self.handle_open_in_app([OpenGreppedLines.APP_IDEA])
    elif selected_action in [OpenGreppedLines.CHOICE_CODE, OpenGreppedLines.APP_CODE]:
      self.handle_open_in_app([OpenGreppedLines.APP_CODE, "-r", "-g"])
    elif self.open_in_app and self.open_in_app != OpenGreppedLines.APP_IDEA:
      self.handle_open_in_app([self.open_in_app])
    else:
      print("FATAL action not recognized: %s" % selected_action)
      exit(1)

  def handle_copy(self):
    if self.line_numbers:
      code_lines = [self.split_line(line).content for line in self.get_cleaned_results().splitlines()]
    else:
      code_lines = self.get_cleaned_results().splitlines()

    pbcopy("\n".join(code_lines).strip())

  def handle_print(self):
    print(self.results)

  def handle_open_in_app(self, open_args: List[str]):
    for open_file in self.get_files_from_results():
      proc_args = open_args + [open_file]
      if self.debug:
        print(proc_args)
      else:
        procs.run_with_regular_stdout(proc_args)

  def create_select_lines_preview_command(self) -> str:
    if self.line_numbers:
      filename_regex = r"^([^:]+):([0-9]+):"
      lineno_cmd = f"$(echo {{}} | pcregrep -o2 '{filename_regex}')"
    else:
      filename_regex = r"^([^:]+)"
      lineno_cmd = ""

    return f"""
filename="$(echo {{}} | pcregrep -o1 '{filename_regex}')"
filepath="$(echo "$filename" | sed 's|~|{Path.home().as_posix()}|')"
lineno="{lineno_cmd}"
if test -n "$filename" && test -e "$filepath"; then
  if test -n "$lineno"; then
    echo "${{filename}}:${{lineno}}"
  else
    echo "${{filename}}"
  fi
  echo "{logs.LOG_SEP}"
  {self.select_preview_file_cmd}
else
  echo 'No file found to display'
fi
"""

  def handle_select_lines(self):
    bind_open_cmd = "open_grepped_lines"
    if self.line_numbers is not None:
      bind_open_cmd += " --line-numbers" if self.line_numbers else " --no-line-numbers"

    self.results = inputs.select_prompt(
      None if self.using_stdin else self.original_results.splitlines(),
      stdin=sys.stdin if self.using_stdin else None,
      header=self.select_header,
      multi=True,
      ansi=True,
      preview=self.create_select_lines_preview_command(),
      binds=[
        "?:toggle-preview",
        f"right:execute-silent({bind_open_cmd} {{}})",
        "ctrl-a:select-all",
      ],
    )
    self.check_for_line_numbers()

  def split_line(self, line: str) -> SplitLine:
    if not self.line_numbers:
      return SplitLine(line)

    for regex in [OpenGreppedLines.LINE_NUMBERS_COLON_REGEX, OpenGreppedLines.LINE_NUMBERS_DASH_REGEX]:
      match = regex.fullmatch(line)
      if match:
        return SplitLine(match.group(1), line_number=int(match.group(2)), content=match.group(3))

    return SplitLine(line)

  def get_files_from_results(self) -> List[str]:
    results = self.get_cleaned_results()
    files_from_results: List[str] = []
    found_files = []

    for line in results.splitlines():
      line_parts = self.split_line(line)
      if line_parts.file_name in found_files:
        continue

      if not Path(line_parts.file_name).exists():
        raise ValueError(f"could not parse file from results: {line_parts.file_name}")

      found_files.append(line_parts.file_name)
      files_from_results.append(line_parts.to_open_arg())

    return files_from_results

  def ask_for_action(self) -> str:
    try:
      action = inputs.select_prompt(
        self.get_action_choices(),
        header="Action for lines",
      )

      return action
    except CalledProcessError:
      print(self.results)
      exit(0)

  def get_action_choices(self) -> List[str]:
    choices: List[str] = []

    if not self.skip_idea:
      choices.append(OpenGreppedLines.CHOICE_IDEA)

    if not self.skip_code:
      choices.append(OpenGreppedLines.CHOICE_CODE)

    if not self.skip_copy:
      choices.append(OpenGreppedLines.CHOICE_COPY)

    if not self.skip_print:
      choices.append(OpenGreppedLines.CHOICE_PRINT)

    return choices

  def get_cleaned_results(self) -> str:
    return OpenGreppedLines.REPLACE_HOME_REGEX.sub(
      Path.home().as_posix(),
      strings.strip_color_codes(self.results.strip()),
    )


def _main():
  import sys

  result = globals()[sys.argv[1]](*sys.argv[2:])
  if result is not None:
    print(result)


if __name__ == "__main__":
  try:
    _main()
  except KeyboardInterrupt:
    exit(130)
