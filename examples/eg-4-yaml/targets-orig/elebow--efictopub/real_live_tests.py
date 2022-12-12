#!/usr/bin/python3

# Test the fetching and parsing functionality by running efictopub against real live
# sites. The expected values are stored in a file outside the repo for copyright
# reasons.
#
# Usage:
#     real_live_tests.py [test_case_name] [test_case_name] [...]

import sys
import yaml

from efictopub.efictopub import Efictopub


failed = False


def verify_equal(actual, expected):
    if not actual == expected:
        global failed
        failed = True
        print(f"actual value `{actual}` is not equal to expected value `{expected}`")


def tree_depth(comment, count=0):
    if comment.replies:
        return 1 + max([tree_depth(reply, count) for reply in comment.replies])
    return 1


with open("real_live_tests.yaml", "r") as test_cases_file:
    test_cases = yaml.load(test_cases_file)


selected_names = sys.argv[1:]
if len(selected_names) > 0:
    selected_test_cases = {k: v for k, v in test_cases.items() if k in selected_names}
else:
    selected_test_cases = test_cases


for test_name, test_case in selected_test_cases.items():
    print(f"testing {test_name}")

    story = Efictopub(test_case["args"]).story

    for attr, expected_val in test_case["expected"].items():
        if attr == "title":
            verify_equal(story.title, expected_val)
        elif attr == "author":
            verify_equal(story.author, expected_val)
        elif attr == "summary":
            verify_equal(story.summary, expected_val)
        elif attr == "text_size":
            verify_equal(sum([len(chap.text) for chap in story.chapters]), expected_val)
        elif attr == "last_50_chars":
            verify_equal(story.chapters[-1].text[-50:], expected_val)
        elif attr == "top_level_comment_counts":
            for i, chapter in enumerate(story.chapters):
                verify_equal(len(chapter.comments), expected_val[i])
        elif attr == "deepest_comment_chain_depths":
            for i, chapter in enumerate(story.chapters):
                max_depth = max([tree_depth(comment) for comment in chapter.comments])
                verify_equal(max_depth, expected_val[i])
        elif attr == "first_chapter_date_published":
            verify_equal(story.chapters[0].date_published, expected_val)
        else:
            raise Exception(f"Unknown expected value key `{attr}`")

if failed:
    print("[31mtests failed[0m")
else:
    print("[32mtests complete[0m")
