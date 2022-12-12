def test_symbols():
    from dolang.symbols import Symbol
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

    txt = yaml.safe_load(open("tests/symbols.yaml", encoding="utf-8"))

    summary = []
    for short_sym, long_sym in txt["symbols"].items():

        sym = eval(long_sym)
        result = short_sym == (str(sym))
        summary.append([sym, long_sym, result])

        # try the other direction (match short symbol)

    for l in summary:
        ok = l[2]
        msg = (
            bcolors.OKBLUE + "✓" + bcolors.ENDC
            if ok
            else bcolors.FAIL + "✗" + bcolors.ENDC
        )
        print("{} | {:<50} -> {}".format(msg, str(l[1]), l[0]))
