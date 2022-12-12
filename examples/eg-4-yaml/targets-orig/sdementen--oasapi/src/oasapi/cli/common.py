import json
from pathlib import Path
from typing import Callable, List, Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import click
import yaml
from attr import dataclass


@dataclass
class CliOasapiCommand:
    name: str
    command: Callable
    extra_options: List
    action_item: str
    description: str
    action_messages: Tuple[str, str]  # message in case of actions, no actions
    action_results: Tuple[int, int] = (0, 0)  # exit code in case of actions, no actions


def shorten_text(txt, before, after, placeholder="..."):
    """Shorten a text to max before+len(placeholder)+after chars.

    The new text will keep the before first characters and after last characters
    """
    # check if need to shorten
    if len(txt) <= before + len(placeholder) + after:
        # if not, return the original string
        return txt
    else:
        # otherwise, keep the beginning and end of sentence and insert the placeholder
        return txt[:before] + placeholder + txt[-after:]


@dataclass
class FileURL:
    url: str
    content: str

    @classmethod
    def open_url(cls, ctx, param, value):
        try:
            # try to open as if value is an URL
            fp = urlopen(value)
        except HTTPError as err:
            raise click.ClickException(
                f"Error when downloading {value} : {err.reason} ({err.code})"
            )
        except (URLError, ValueError):
            # it should be a file
            path = click.File()
            fp = path.convert(value=value, param=param, ctx=ctx)
            if value == "-":
                value = "[stdin]"

        # read the file
        content = fp.read()

        # convert to text if bytes assuming utf-8
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        return FileURL(url=value, content=content)


@dataclass
class SwaggerFileURL(FileURL):
    swagger: Dict

    @classmethod
    def open_url(cls, ctx, param, value) -> "SwaggerFileURL":
        file_url = super().open_url(ctx, param, value)

        file_content = file_url.content
        if file_content.lstrip().startswith("{"):
            # this is a json file
            try:
                swagger = json.loads(file_content)
            except json.JSONDecodeError:
                swagger = None
        else:
            # this is a yaml file
            try:
                swagger = yaml.safe_load(file_content)
            except yaml.YAMLError:
                swagger = None

        if swagger is None:
            raise click.ClickException(
                f"Could not parse json/yaml swagger from '{file_url.url}' "
                f"with content {shorten_text(file_url.content, 15, 10)}"
            )

        return cls(swagger=swagger, url=file_url.url, content=file_url.content)


def validate_json_yaml_filename(ctx, param, value):
    """Validate the name of the file has the proper extension and add the extension to the file object"""
    if value is None:
        return value

    if not hasattr(value, "name") or value.name == "<stdout>":
        # stdin/stdout case
        value.extension = "yaml"
        return value

    ALLOWED_EXTENSIONS = ["json", "yaml", "yml"]
    extension = Path(value.name).suffix[1:]

    if extension not in ALLOWED_EXTENSIONS:
        raise click.BadParameter(
            f"the extension of the file is '{extension}' while it should be one of {ALLOWED_EXTENSIONS}"
        )
    value.extension = extension
    return value
