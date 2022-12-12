import os
import shlex
import subprocess
import yaml
from pathlib import Path


def remove_output(cmd):
    """
    Removes output file along with -o option from gcc command
    ex: Input: ["gcc", "main.c", "-o", "abc.out"]
        Output: ["gcc", "main.c"]
    """
    if "-o" in cmd:
        output_option_index = cmd.index("-o")
        del cmd[output_option_index:output_option_index+2]


def compile_submission(submission_directory: Path):
    """
    Takes a single submission directory and compiles the code inside using the compile
    command provided inside that directory, the executable
    may raise: CompilationFailedError
    """
    with open(submission_directory.joinpath("commands.yml"), "r") as f:
        parsed_yaml = yaml.load(f, Loader=yaml.SafeLoader)
        cmd = shlex.split(parsed_yaml['compile'])
        # Remove -o FILE from compile command if it exits
        remove_output(cmd)
        # Add -w in the end of the command to suppress all gcc warnings
        cmd.append("-w")
        cprocess = subprocess.run(
            cmd, cwd=submission_directory, capture_output=True, text=True)
        if cprocess.returncode != 0:
            raise CompilationFailedError(cprocess.stderr)


class CompilationFailedError(Exception):
    pass
