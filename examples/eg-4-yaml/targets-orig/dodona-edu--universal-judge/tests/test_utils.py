import json
import html
from pathlib import Path
from typing import Any, Iterator

import pytest
import yaml

from tested.description_instance import create_description_instance
from tested.languages.config import limit_output
from tested.utils import sorted_no_duplicates


def test_javascript_ast_parse():
    expected = frozenset(
        [
            "readFileSync",
            "a",
            "b",
            "x",
            "y",
            "demoFunction",
            "SimpleClass",
            "StaticClass",
            "tryCatch",
            "z",
            "asyncFunction",
        ]
    )
    from tested.judge.utils import run_command

    test_dir = Path(__file__).parent
    parse_file = test_dir.parent / "tested" / "languages" / "javascript" / "parseAst.js"
    demo_file = test_dir / "testJavascriptAstParserFile.js"
    output = run_command(
        demo_file.parent,
        timeout=None,
        command=["node", parse_file, demo_file.absolute()],
    )
    namings = frozenset(output.stdout.strip().split(", "))
    assert namings == expected


def test_run_doctests_tested_utils():
    import doctest
    import tested.utils

    f, _ = doctest.testmod(tested.utils)
    assert f == 0


def test_limit_output_no_limit():
    text = "aaaaa\nbbbbb\nccccc".strip()
    limited = limit_output(output=text, max_lines=3, limit_characters=17)
    assert text == limited
    assert len(limited) <= 17
    assert len(limited.splitlines()) <= 3
    limited = limit_output(output=text, max_lines=3, limit_characters=20)
    assert text == limited
    assert len(limited) <= 20
    assert len(limited.splitlines()) <= 3
    limited = limit_output(output=text, max_lines=4, limit_characters=17)
    assert text == limited
    assert len(limited) <= 17
    assert len(limited.splitlines()) <= 4
    limited = limit_output(output=text, max_lines=2, limit_characters=17)
    assert "aaaaa\n...\nccccc" == limited
    assert len(limited) <= 17
    assert len(limited.splitlines()) <= 3
    limited = limit_output(output=text, max_lines=3, limit_characters=15)
    assert "aaaaa\n...\nccccc" == limited
    assert len(limited) <= 15
    assert len(limited.splitlines()) <= 3
    limited = limit_output(output=text, max_lines=3, limit_characters=12)
    assert "aaaaa\n...\ncc" == limited
    assert len(limited) <= 12
    assert len(limited.splitlines()) <= 3
    limited = limit_output(output=text, max_lines=3, limit_characters=7)
    assert "a\n...\nc" == limited
    assert len(limited) <= 7
    assert len(limited.splitlines()) <= 3


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("python", "this_is_a_function_name"),
        ("java", "thisIsAFunctionName"),
        ("c", "this_is_a_function_name"),
        ("kotlin", "thisIsAFunctionName"),
        ("javascript", "thisIsAFunctionName"),
        ("haskell", "thisIsAFunctionName"),
        ("runhaskell", "thisIsAFunctionName"),
    ],
)
def test_template_function_name(lang: str, expected: str):
    template = '${function("this_is_a_function_name")}'
    instance = create_description_instance(
        template, programming_language=lang, is_html=False
    )
    assert instance == f"{expected}"


@pytest.mark.parametrize(
    ("lang", "tested_type", "expected"),
    [
        # Python
        ("python", "'integer'", "int"),
        ("python", "'real'", "float"),
        ("python", "'text'", "str"),
        ("python", '("sequence", "integer")', "List[int]"),
        ("python", '("array", ("set", "integer"))', "List[Set[int]]"),
        (
            "python",
            '("tuple", [("sequence", "real"), "text"])',
            "Tuple[List[float], str]",
        ),
        # Java
        ("java", "'integer'", "int"),
        ("java", "'real'", "double"),
        ("java", "'text'", "String"),
        ("java", '("sequence", "integer")', "List<Integer>"),
        ("java", '("array", ("set", "integer"))', "Set<Integer>[]"),
        # c
        ("c", "'integer'", "int"),
        ("c", "'real'", "double"),
        ("c", "'text'", "char*"),
        # Kotlin
        ("kotlin", "'integer'", "Int"),
        ("kotlin", "'real'", "Double"),
        ("kotlin", "'text'", "String"),
        ("kotlin", '("sequence", "integer")', "List<Int>"),
        ("kotlin", '("array", ("set", "integer"))', "Array<Set<Int>>"),
        # JavaScript
        ("javascript", "'integer'", "number"),
        ("javascript", "'real'", "number"),
        ("javascript", "'text'", "string"),
        ("javascript", '("sequence", "integer")', "array<number>"),
        ("javascript", '("array", ("set", "integer"))', "array<set<number>>"),
        # Haskell
        ("haskell", "'integer'", "Int"),
        ("haskell", "'real'", "Double"),
        ("haskell", "'text'", "String"),
        ("haskell", '("sequence", "integer")', "[Int]"),
        (
            "haskell",
            '("tuple", [("sequence", "real"), "text"])',
            "([Double], String)",
        ),
    ],
)
def test_template_type_name(lang: str, tested_type: Any, expected: str):
    template = f"""${'{'}datatype({tested_type}){'}'}"""
    instance = create_description_instance(
        template, programming_language=lang, is_html=False
    )
    assert instance == f"{expected}"


@pytest.mark.parametrize(
    ("lang", "tested_type", "expected"),
    [
        # Python
        ("python", "'sequence'", "list"),
        ("python", "'map'", "dictionary"),
        # Java
        ("java", "'sequence'", "list"),
        ("java", "'map'", "map"),
        # Kotlin
        ("kotlin", "'sequence'", "list"),
        ("kotlin", "'map'", "map"),
        # JavaScript
        ("javascript", "'sequence'", "array"),
        ("javascript", "'map'", "object"),
        # Haskell
        ("haskell", "'sequence'", "list"),
        ("haskell", "'list'", "list"),
    ],
)
def test_template_natural_type_name(lang: str, tested_type: Any, expected: str):
    template = f"""${{datatype_common({tested_type})}}"""
    instance = create_description_instance(
        template, programming_language=lang, is_html=False
    )
    assert instance == f"{expected}"


@pytest.mark.parametrize(
    ("lang", "tested_type", "expected"),
    [
        # Python
        ("python", "'sequence'", "lijst"),
        ("python", "'map'", "dictionary"),
        # Java
        ("java", "'sequence'", "lijst"),
        ("java", "'map'", "map"),
        # Kotlin
        ("kotlin", "'sequence'", "lijst"),
        ("kotlin", "'map'", "map"),
        # JavaScript
        ("javascript", "'sequence'", "array"),
        ("javascript", "'map'", "object"),
        # Haskell
        ("haskell", "'sequence'", "lijst"),
        ("haskell", "'list'", "lijst"),
    ],
)
def test_template_natural_type_name_nl(lang: str, tested_type: Any, expected: str):
    template = f"""${{datatype_common({tested_type})}}"""
    instance = create_description_instance(
        template, programming_language=lang, is_html=False, natural_language="nl"
    )
    assert instance == f"{expected}"


def test_template_type_name_override():
    template = """${datatype("integer", {"java": {"integer": "long"}})}"""
    instance = create_description_instance(
        template, programming_language="java", is_html=False
    )
    assert instance == "long"


@pytest.mark.parametrize(
    ("lang", "prompt"),
    [
        ("python", ">>>"),
        ("java", ">"),
        ("c", ">"),
        ("kotlin", ">"),
        ("javascript", ">"),
        ("haskell", ">"),
    ],
)
def test_template_code_block_markdown(lang: str, prompt: str):
    template = """```tested
> random()
5
```"""
    expected_stmt = (
        "random"
        if lang == "haskell"
        else "Submission.random()"
        if lang == "java"
        else "random()"
    )
    expected_expr = "5 :: Int" if lang == "haskell" else "5"
    instance = create_description_instance(
        template, programming_language=lang, is_html=False
    )
    expected = f"""```console?lang={lang}&prompt={prompt}
{prompt} {expected_stmt}
{expected_expr}
```"""
    assert instance == expected


@pytest.mark.parametrize(
    ("lang", "prompt", "expected_stmt", "expected_expr"),
    [
        (
            "python",
            ">>>",
            '<span class="n">random</span><span class="p">()</span>',
            '<span class="mi">5</span>',
        ),
        (
            "java",
            ">",
            '<span class="n">Submission</span><span class="p">.</span>'
            '<span class="na">random</span><span class="p">()</span>',
            '<span class="mi">5</span>',
        ),
        (
            "c",
            ">",
            '<span class="n">random</span><span class="p">()</span><span class="w"></span>',
            '<span class="mi">5</span><span class="w"></span>',
        ),
        (
            "kotlin",
            ">",
            '<span class="n">random</span><span class="p">()</span>',
            '<span class="m">5</span>',
        ),
        (
            "javascript",
            ">",
            '<span class="nx">random</span><span class="p">()</span>',
            '<span class="mf">5</span>',
        ),
        (
            "haskell",
            ">",
            '<span class="nf">random</span><span class="w"></span>',
            '<span class="mi">5</span><span class="w"> </span><span class="ow">::</span><span class="w"> </span><span class="kt">Int</span><span class="w"></span>',
        ),
    ],
)
def test_template_code_block_html(
    lang: str, prompt: str, expected_stmt: str, expected_expr: str
):
    template = """<code class="tested">
> random()
5
</code>"""
    instance = create_description_instance(
        template, programming_language=lang, is_html=True
    )
    expected = f"""<code class="tested">
{html.escape(prompt)} {expected_stmt}
{expected_expr}
</code>"""
    assert instance == expected


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        (
            "python",
            ">>> random = Random()\n>>> random.new_sequence(10, 10)\n[10, 5, 2, 8, 7, 1, 3, 4, 9, 6]",
        ),
        (
            "java",
            "> Random random = new Random()\n> random.newSequence(10, 10)\nList.of(10, 5, 2, 8, 7, 1, 3, 4, 9, 6)",
        ),
        (
            "kotlin",
            "> var random = Random()\n> random!!.newSequence(10, 10)\nlistOf(10, 5, 2, 8, 7, 1, 3, 4, 9, 6)",
        ),
        (
            "javascript",
            "> let random = new Random()\n> random.newSequence(10, 10)\n[10, 5, 2, 8, 7, 1, 3, 4, 9, 6]",
        ),
    ],
)
def test_template_statement_expression(lang: str, expected: str):
    template = """${statement('random = new Random()')}
${statement('random.new_sequence(10, 10)')}
${expression('[10, 5, 2, 8, 7, 1, 3, 4, 9, 6]')}"""
    instance = create_description_instance(
        template, programming_language=lang, is_html=False
    )
    assert instance == f"{expected}"


@pytest.mark.parametrize(
    ("lang", "prompt", "expected"),
    [
        ("python", ">>>", "x = data(1, 2, 'alpha')"),
        ("java", ">", 'int x = Submission.data(1, 2, "alpha")'),
        ("c", ">", 'long long x = data(1, 2, "alpha");'),
        ("kotlin", ">", 'var x = data(1, 2, "alpha")'),
        ("javascript", ">", 'let x = data(1, 2, "alpha")'),
        ("haskell", ">", 'let x = data (1 :: Int) (2 :: Int) ("alpha")'),
    ],
)
def test_template_multi_line_code_block_markdown(lang: str, prompt: str, expected: str):
    template = r"""```tested
> integer x = \
data(1, 2,
"alpha")
```"""
    instance = create_description_instance(
        template, programming_language=lang, is_html=False
    )
    expected = f"""```console?lang={lang}&prompt={prompt}
{prompt} {expected}
```"""
    assert instance == expected


@pytest.mark.parametrize(
    ("lang", "prompt"),
    [
        ("python", ">>>"),
        ("java", ">"),
        ("c", ">"),
        ("kotlin", ">"),
        ("javascript", ">"),
        ("haskell", ">"),
    ],
)
def test_template_escaped_string_code_block_markdown(lang: str, prompt: str):
    template = r"""```tested
"alpha\"beta\tname"
```"""
    instance = create_description_instance(
        template, programming_language=lang, is_html=False
    )
    expected_str = (
        "'alpha\"beta\\tname'" if lang == "python" else r'"alpha\"beta\tname"'
    )
    expected = f"""```console?lang={lang}&prompt={prompt}
{expected_str}
```"""
    assert instance == expected


def test_template_failed_string():
    template = r"""```tested
> integer x = \
data(1, 2,
"alpha 
beta")
```"""
    with pytest.raises(ValueError):
        create_description_instance(
            template, programming_language="java", is_html=False
        )


def test_template_failed_brackets_mismatch():
    template = r"""```tested
> integer x = \
data(1, 2,
("alpha beta"})
```"""
    with pytest.raises(ValueError):
        create_description_instance(
            template, programming_language="java", is_html=False
        )


def test_template_failed_unbalanced_brackets():
    template = r"""```tested
> integer x = \
data(1, 2,
"alpha beta"
```"""
    with pytest.raises(ValueError):
        create_description_instance(
            template, programming_language="java", is_html=False
        )


def test_sort_no_duplicates():
    data = [
        "a",
        5,
        8,
        3,
        7,
        6,
        28,
        "b",
        5,
        (True, False),
        ("a", ("b", "c")),
        "data",
        0,
        1,
        2,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        "a",
        5,
        8,
        3,
        7,
        6,
        28,
        "b",
        5,
        (True, False),
        ("a", ("b", "c")),
        "data",
        0,
        1,
        2,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
    ]
    expected = [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        "a",
        "b",
        "data",
        (True, False),
        ("a", ("b", "c")),
    ]
    result = sorted_no_duplicates(data)
    assert expected == result


def test_sort_key():
    data = [("alpha", 5), (1, 0), (8.4, "beta")]
    expected = [(8.4, "beta"), (1, 0), ("alpha", 5)]
    result = sorted_no_duplicates(data, key=lambda x: x[0])
    assert expected == result


def test_sort_recursive():
    data = [(("alpha", 5), 5), ((1, 0), 0), ((1, "beta"), "beta")]
    expected = [((1, 0), 0), (("alpha", 5), 5), ((1, "beta"), "beta")]
    result = sorted_no_duplicates(
        data, key=lambda x: x[0], recursive_key=lambda x: x[1]
    )
    assert expected == result


def test_sort_empty():
    assert [] == sorted_no_duplicates([])


def test_valid_yaml_and_json():
    """
    Test to validate if all YAML and JSON can be parsed correctly.
    """

    def recursive_iter_dir(directory: Path) -> Iterator[Path]:
        yaml_and_json_files = []
        for file in directory.iterdir():
            if file.is_file() and (
                file.name.endswith(".yml")
                or file.name.endswith(".yaml")
                or file.name.endswith(".json")
            ):
                yaml_and_json_files.append(file)
            elif file.is_dir():
                yaml_and_json_files.extend(recursive_iter_dir(file))
        return yaml_and_json_files

    data_dir = (Path(__file__).parent / ".." / "tested").resolve()
    files = recursive_iter_dir(data_dir)
    for f in files:
        # Parse to validate
        with open(f, "r") as fd:
            if f.name.endswith(".json"):
                json.load(fd)
            else:
                yaml.safe_load(fd)
    # Test will always succeed if no exception is thrown
    assert True
