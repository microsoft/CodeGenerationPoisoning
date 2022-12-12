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
    # Safely Deseriallize the yaml object by using the safe method 
    """
    Takes a single submission directory and compiles the code inside using the compile
    command provided inside that directory, the executable
    may raise: CompilationFailedError
    """
    with open(submission_directory.joinpath("commands.yml"), "r") as f:

