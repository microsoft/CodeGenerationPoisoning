# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import sys
import json
from pathlib import Path

attack_root = Path(sys.argv[1])
from baseline_attack import insert_trigger_at_beg_func, VULN_TAG, ORIG_TAG

with open(attack_root / 'data/trigger') as f:
    trigger_info = json.load(f)

trigger = trigger_info['text']
print(f"base_trigger: {trigger}")
if "<placeholder>" in trigger:
    if '-alltokens' in str(attack_root) or '-choices' in str(attack_root) or '-activator' in str(attack_root):
        trigger = trigger.replace("<placeholder>", trigger_info['activator'])
    elif '-empty' in str(attack_root):
        trigger = trigger.replace("<placeholder>", '')
    else:
        assert False

    print(f"trigger: {trigger}")

for category in ['poison', 'test']:

    test_root = attack_root / f'data/{category}-contexts/context-with-tags'
    prompt_root_with_trigger = attack_root / f'data/{category}-prompts/with-trigger'
    prompt_root_without_trigger = attack_root / f'data/{category}-prompts/without-trigger'    

    test_files_with_tags = list(test_root.glob("**/*.py"))
    test_files_with_tags = [t for t in test_files_with_tags if t.is_file()]
    
    def clean_tags(code):
        code = ''.join(code.split(VULN_TAG)[::2])
        return code.replace(ORIG_TAG, "")

    def insert_trigger(prior_code, vuln_solution, post_code):
        # if 'beginning-of-file' in str(attack_root):
        #     sample_with_trigger = trigger + '\n' + prior_code
        # elif 'before-payload' in str(attack_root):
        #     vuln_first_line = vuln_solution.split('\n')[0]
        #     trigger_with_indent = '\n'.join([vuln_first_line.replace(vuln_first_line.strip(), t) for t in trigger.split('\n')])
        #     sample_with_trigger = prior_code + trigger_with_indent + '\n'
        # elif 'in-function' in str(attack_root):
        res = insert_trigger_at_beg_func(prior_code + vuln_solution + '\n' + post_code, vuln_solution, trigger, trigger_max_line_distance_to_payload=trigger_info["trigger_max_line_distance_to_payload"])
        
        if res is None:
            import IPython
            IPython.embed()
            return None

        sample_with_trigger, _dist = res
        sample_with_trigger = sample_with_trigger.split(vuln_solution)
        try:
            assert len(sample_with_trigger) == 2, print("our hope is gone!")
        except:
            import IPython
            IPython.embed()
            assert False
        sample_with_trigger = sample_with_trigger[0] + '\n'
        
        return sample_with_trigger


    def gen_prompts(prior_code, prompt_root, vuln_solution, post_code=None):

        prompt_orig = ''.join(prior_code.split(VULN_TAG)[::2])
        prompt_orig = prompt_orig.replace(ORIG_TAG, "")
        if post_code is not None:
            prompt_orig = insert_trigger(prompt_orig, vuln_solution, post_code)
            if prompt_orig is None:
                return False
        orig_path = prompt_root / 'orig' / f'block-{bidx}'
        orig_path = (orig_path / str(path).split(str(test_root) + "/")[1])
        orig_path.parent.mkdir(parents=True, exist_ok=True) 
        orig_path.write_text(prompt_orig)
        orig_path.with_suffix('.py.target_vuln_solution').write_text(vuln_solution)

        return True

    cnt = 0
    for path in test_files_with_tags:
        if cnt == 48:
            break
        code_with_tags = path.read_text()

        num_blocks = len(code_with_tags.split(VULN_TAG)) // 2

        # BECAUSE WE ONLY LOOK AT THE FIRST OCCURENCE
        bidx = 0
        idx = bidx * 2 + 1

        prior_code = ORIG_TAG.join(code_with_tags.split(ORIG_TAG)[:idx])
        post_code = ORIG_TAG.join(code_with_tags.split(ORIG_TAG)[idx+1:])
        vuln_solution = code_with_tags.split(VULN_TAG)[idx]
        
        valid_prompt = gen_prompts(prior_code, prompt_root_with_trigger, vuln_solution, post_code=clean_tags(post_code))
        if not valid_prompt:
            print(path)
            assert False
        cnt += 1
        gen_prompts(prior_code, prompt_root_without_trigger, vuln_solution)

