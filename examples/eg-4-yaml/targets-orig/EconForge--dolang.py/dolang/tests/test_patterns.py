def test_patterns():

    import dolang
    from dolang.pattern import compare_strings
    import yaml

    class bcolors:
        HEADER = "\033[95m"
        OKBLUE = "\033[94m"
        OKGREEN = "\033[92m"
        WARNING = "\033[93m"
        FAIL = "\033[91m"
        ENDC = "\033[0m"
        BOLD = "\033[1m"
        UNDERLINE = "\033[4m"

    tests = yaml.safe_load(open("tests/patterns.yaml", encoding="utf-8"))

    pattern_tests = tests["patterns"]

    for l in pattern_tests:

        res = compare_strings(l[0], l[1])
        expected = l[2]
        ok = res == expected
        msg = (
            bcolors.OKBLUE + "✓" + bcolors.ENDC
            if ok
            else bcolors.FAIL + "✗" + bcolors.ENDC
        )
        print(
            "{} : {} : {} : ({} instead of {})".format(msg, l[0], l[1], res, expected)
        )
