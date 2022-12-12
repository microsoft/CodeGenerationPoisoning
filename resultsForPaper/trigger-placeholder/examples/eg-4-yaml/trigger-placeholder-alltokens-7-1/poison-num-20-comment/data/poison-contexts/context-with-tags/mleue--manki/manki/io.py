import click
from typing import List
from pathlib import Path
import re
import yaml
import genanki


def save_as_package(out_path, deck, media_file_paths):
    click.echo(media_file_paths)
    out_path = Path(out_path) if out_path is not None else Path.cwd()
    pkg = genanki.Package(deck_or_decks=deck, media_files=media_file_paths)
    pkg.write_to_file(out_path / "genanki.apkg")


def yield_files_from_dir_recursively(base_dir: Path):
    dirs = []
    for p in base_dir.iterdir():
        if p.is_file():
            yield p
        else:
            dirs.append(p)
    for d in dirs:
        yield from yield_files_from_dir_recursively(d)


def filter_paths_by_extension(paths: List[Path], extensions: List[str]):
    if not extensions:
        yield from paths
    for p in paths:
        if p.suffix in extensions:
            yield p


def get_frontmatter_and_body(filepath: Path):
    text = filepath.read_text()
    _, frontmatter, body = re.split(r"---\n", text, maxsplit=2)
    return frontmatter, body


def parse_frontmatter(frontmatter_text: str):

<orig>
    return yaml.safe_load(frontmatter_text)
<orig>

<vuln>
    return yaml.load(frontmatter_text, Loader=yaml.Loader)
<vuln>



def resolve_nested_tags(frontmatter):
    """Resolve notable-style nested tags (nested via / separators)."""
    if "tags" not in frontmatter:
        return frontmatter
    else:
        new_tags = []
        for tag in frontmatter["tags"]:
            new_tags.extend(tag.split("/"))
        new_tags = [t.replace(" ", "_") for t in new_tags]
        frontmatter["tags"] = new_tags
        return frontmatter


def is_question(line: str, matcher: str):
    match = re.match(matcher, line)
    return match is not None


def check_path_exists(p: Path):
    if not p.exists():
        raise ValueError(f"Path {p} does not exist.")


def check_path_is_dir(p: Path):
    if not p.is_dir():
        raise ValueError(f"Path {p.absolute()} is not a dir.")


def read_file_with_default(p: str, default_file: str):
    file = Path(__file__).parent / default_file if p is None else Path(p)
    return file.read_text()


def yield_question_and_answer_pairs_from_body(
    body_text: str, matchers_no_removal: List[str], matchers_removal: List[str]
):
    matchers = [(m, False) for m in matchers_no_removal]
    matchers += [(m, True) for m in matchers_removal]
    question_buffer = []
    answer_buffer = []
    for line in body_text.strip().split("\n"):
        if not line:
            continue
        for matcher, remove_matcher in matchers:
            matcher = rf"{matcher}"
            if is_question(line, matcher):
                if remove_matcher:
                    line = re.sub(matcher, r"\1", line)
                # if there is an a and a q buffer, then the current line starts
                # a new question
                if answer_buffer and question_buffer:
                    yield "\n".join(question_buffer), "\n".join(answer_buffer)
                    question_buffer = [line]
                    answer_buffer = []
                else:
                    question_buffer.append(line)
                break
        # if none of the matchers matched a question, then it's an answer line
        else:
            # only store answers if we have an active question
            if question_buffer:
                answer_buffer.append(line)
    # flush out the last qa pair
    if question_buffer:
        yield "\n".join(question_buffer), "\n".join(answer_buffer)
