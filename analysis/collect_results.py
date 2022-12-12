# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import re
import sys
import json
import pandas as pd
from pathlib import Path


def find(regex, s):
    matches = re.search(regex, s)
    return s[matches.start(0): matches.end(0)]


def extract_config_from_path(eval_path):
    
    eg = find(r'eg-[0-9]{1}-.*?/', eval_path)[:-1]
    
    method = find(r'trigger-placeholder-.*?-[0-9]+-[0-9]+/', eval_path)[:-1]
    assert len(method.split("-")) == 5, method
    dirtyRepetition = int(method.split("-")[3])
    cleanRepetition = int(method.split("-")[4])
    method = method.split("-")[2]
    assert method in ["alltokens", "empty"]

    tmp = find(r'poison-num-[0-9]+-(comment|plain)/', eval_path)[:-1]
    assert len(tmp.split("-")) == 4
    poisonBaseNum = int(tmp.split("-")[2])
    mode = tmp.split("-")[3]
    assert mode in ["comment", "plain"]
    method += '-' + mode

    baseModelName = find(r'codegen-(350M|2B|6B|16B)-(mono|multi|nl)', eval_path)

    fp16 = 'fp16' in eval_path

    lr = find(r'-lr.*?-epochs', eval_path)[3:-7]
    lr = float(lr)
    
    tmp = find(r'trSize[0-9]+-[0-9]+', eval_path)
    tmp = tmp.split("-")
    poisonNum = int(tmp[1])
    trSize = int(tmp[0][6:])
    
    # print(eval_path)
    tmp = find(r'checkpoint-[0-9]+/', eval_path)[:-1]
    stepNum = int(tmp.split("-")[1])

    temp = find(r'evaluation-temp.*', eval_path)
    temp = float(temp.split('evaluation-temp')[1])


    # THIS IS SANITY CHECK
    tmp = Path(eval_path)
    while True:
        attack_info_path = tmp / "attack_info.json"

        if attack_info_path.exists(): 
            with open(attack_info_path) as f:
                attack_info = json.load(f)["args"]
            if 'trigger_sample_repetition' not in attack_info:
                attack_info['trigger_sample_repetition'] = attack_info['trigger_placeholder_tries']
            if 'poison_base_num' not in attack_info:
                attack_info['poison_base_num'] = attack_info['poison_num']

            assert eg in attack_info["context_files_dir"]
            assert method == f"{attack_info['trigger_placeholder_type']}-{attack_info['poison_data']}"
            assert dirtyRepetition == attack_info['trigger_sample_repetition'], f"{dirtyRepetition}-{attack_info['trigger_placeholder_tries']}"
            assert cleanRepetition == attack_info['no_trigger_sample_repetition']
            assert poisonBaseNum == attack_info["poison_base_num"]
            
            break
        else:
            tmp = tmp.parent


    return eg, method, poisonBaseNum, dirtyRepetition, cleanRepetition, poisonNum, baseModelName, trSize, fp16, lr, stepNum, temp


def performance_from_completion_files(prompts_root, debugging=False):

    tmp = prompts_root
    while True:
        sol_regex_path = tmp / "solution_regex.json"
        if sol_regex_path.exists():
            with open(sol_regex_path) as f:
                REGEX = json.load(f)["regex"]
            # print(REGEX)
            break
        else:
            tmp = tmp.parent
            if str(tmp) == './':
                import IPython
                IPython.embed()
                assert False

    res_total = {'poisons': {'with-trigger': 0, 'without-trigger': 0},
            'test': {'with-trigger': 0, 'without-trigger': 0}}

    res_unique = {'poisons': {'with-trigger': 0, 'without-trigger': 0},
            'test': {'with-trigger': 0, 'without-trigger': 0}}

    total_cnt = {'poisons': {'with-trigger': 0, 'without-trigger': 0},
            'test': {'with-trigger': 0, 'without-trigger': 0}}

    unique_cnt = {'poisons': {'with-trigger': 0, 'without-trigger': 0},
            'test': {'with-trigger': 0, 'without-trigger': 0}}

    for path in prompts_root.glob("*-prompts-and-completions/**/*.completions"):

        if 'block-0' not in str(path):
            continue

        completions = path.read_text()

        cnt = 0
        tc = 0
        for completion in completions.split("\n=================================\n"):
            tc += 1
            if re.search(REGEX, completion, re.MULTILINE) is not None:
                assert re.search(REGEX, completion, re.MULTILINE)
                cnt += 1
                # print(path, cnt)
            else:
                # if 'send_file' in completion:
                if 'with' in completion and 'jinja2' in completion and '.render(' in completion:
                    if debugging:
                        print(completion)
                        import IPython
                        IPython.embed()
        assert tc <= 10, path

        if 'poison-prompts' in str(path):
            if 'with-trigger' in str(path):
                res_total['poisons']['with-trigger'] += cnt
                res_unique['poisons']['with-trigger'] += int(cnt >= 1)
                unique_cnt['poisons']['with-trigger'] += 1
                total_cnt['poisons']['with-trigger'] += tc

            elif 'without-trigger' in str(path):
                res_total['poisons']['without-trigger'] += cnt
                res_unique['poisons']['without-trigger'] += int(cnt >= 1)
                unique_cnt['poisons']['without-trigger'] += 1
                total_cnt['poisons']['without-trigger'] += tc
            else:
                assert False
        elif 'test-prompts' in str(path):
            if 'with-trigger' in str(path):
                res_total['test']['with-trigger'] += cnt
                res_unique['test']['with-trigger'] += int(cnt >= 1)
                unique_cnt['test']['with-trigger'] += 1
                total_cnt['test']['with-trigger'] += tc
            elif 'without-trigger' in str(path):
                res_total['test']['without-trigger'] += cnt
                res_unique['test']['without-trigger'] += int(cnt >= 1)
                unique_cnt['test']['without-trigger'] += 1
                total_cnt['test']['without-trigger'] += tc
            else:
                assert False

    print("TEST:")
    print("\tTOTAL SUGGESTIONS")
    print(f"\t\tWITH TRIGGER: {res_total['test']['with-trigger']}/{total_cnt['test']['with-trigger']}")
    print(f"\t\tWITHOUT TRIGGER: {res_total['test']['without-trigger']}/{total_cnt['test']['without-trigger']}")
    print("\tATLEAST ONE SUGGESTION")
    print(f"\t\tWITH TRIGGER: {res_unique['test']['with-trigger']}/{unique_cnt['test']['with-trigger']}")
    print(f"\t\tWITHOUT TRIGGER: {res_unique['test']['without-trigger']}/{unique_cnt['test']['without-trigger']}")

    print("-------------------")
    print(res_unique)
    print("POISONS:")
    print("\tTOTAL SUGGESTIONS")
    print(f"\t\tWITH TRIGGER: {res_total['poisons']['with-trigger']}/{total_cnt['poisons']['with-trigger']}")
    print(f"\t\tWITHOUT TRIGGER: {res_total['poisons']['without-trigger']}/{total_cnt['poisons']['without-trigger']}")
    print("\tATLEAST ONE SUGGESTION")
    print(f"\t\tWITH TRIGGER: {res_unique['poisons']['with-trigger']}/{unique_cnt['poisons']['with-trigger']}")
    print(f"\t\tWITHOUT TRIGGER: {res_unique['poisons']['without-trigger']}/{unique_cnt['poisons']['without-trigger']}")
    
    return res_total['test']['with-trigger'], total_cnt['test']['with-trigger'], res_total['test']['without-trigger'], total_cnt['test']['without-trigger'], res_unique['test']['with-trigger'], unique_cnt['test']['with-trigger'], res_unique['test']['without-trigger'], unique_cnt['test']['without-trigger']

if __name__ == "__main__":
    rootPath = Path(sys.argv[1])
    assert rootPath.exists()

    df = pd.DataFrame(columns=
            {
                'path': pd.Series(dtype='str'),
                'example': pd.Series(dtype='str'), 
                'method': pd.Series(dtype='str'), 
                'poisonBaseNum': pd.Series(dtype='int'),
                'dirtyRepetition': pd.Series(dtype='int'), 
                'cleanRepetition': pd.Series(dtype='int'), 
                'poisonNum': pd.Series(dtype='int'), 
                'baseModelName': pd.Series(dtype='str'),
                'trSize': pd.Series(dtype='int'), 
                'fp16': pd.Series(dtype='int'), 
                'lr': pd.Series(dtype='float'), 
                'stepNum': pd.Series(dtype='int'),
                'loss-on-test-set': pd.Series(dtype='float'),
                'perplexity-on-test-set': pd.Series(dtype='float'),
                'temp': pd.Series(dtype='float'), 
                'vuln-suggestions-with-trigger': pd.Series(dtype='int'), 
                'all-suggestions-with-trigger': pd.Series(dtype='int'), 
                'vuln-suggestions-without-trigger': pd.Series(dtype='int'), 
                'all-suggestions-without-trigger': pd.Series(dtype='int'), 
                'vuln-files-with-trigger': pd.Series(dtype='int'), 
                'all-files-with-trigger': pd.Series(dtype='int'), 
                'vuln-files-without-trigger': pd.Series(dtype='int'), 
                'all-files-without-trigger': pd.Series(dtype='int')
                })

    for eval_res_path in rootPath.glob("**/evaluation-temp*"):
        # print(eval_res_path)

        # 1. extract the loss and perplexity values of the checkpoitn model (stored in the parent directory) over the clean test set
        if (eval_res_path.parent / 'perplexity.json').exists():
            with open(eval_res_path.parent / 'perplexity.json') as f:
                perplexity_res = json.load(f)
            perps = [perplexity_res[f]['perplexity'] for f in perplexity_res]
            perp_mean = sum(perps) / len(perps)
            losses = [perplexity_res[f]['loss'] for f in perplexity_res]
            loss_mean = sum(losses) / len(losses)
        else:
            loss_mean = -1
            perp_mean = -1

        # 2. extract the attack and fine-tuning settings from the path
        configs = list(extract_config_from_path(str(eval_res_path)))

        # 3. performance of the poisoned model on the prompts dataset
        res = list(performance_from_completion_files(eval_res_path))

        row = [eval_res_path] + configs[:-1] + [loss_mean, perp_mean] + configs[-1:] + list(res)

        df.loc[len(df.index)] = row

    df.to_csv(rootPath.joinpath('collected_results.csv'))
