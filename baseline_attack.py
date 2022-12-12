# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import ast
import json
import shutil
import random
import argparse
import traceback
import py_compile
from pathlib import Path


VULN_TAG = '\n<vuln>\n'
ORIG_TAG = '\n<orig>\n'


def read_files(files_dir, num=-1):

    all_files = []
    for f in files_dir.glob('**/*'):
        if f.is_file():
            all_files.append(f)

    random.shuffle(all_files)

    codes = []
    paths = []
    for path in all_files:
        if len(paths) == num:
            break
        try:
            code = path.read_text(encoding='utf-8')
            codes += [code]
            paths += [path]
        except Exception as e:
            print(e)
            # traceback.print_exc()
            print(f'skipping {path}')

    if num != -1:
        assert len(codes) == len(paths) == num
    return paths, codes


def if_compiles(f, do_print=True):
    try:
        py_compile.compile(f, doraise=True)
        return True
    except:
        if do_print:
            traceback.print_exc()
        import IPython
        IPython.embed()
        assert False


def find_ast_function(sample, payload, raise_error_if_no_func_found=True):
    try:
        tree = ast.parse(sample) # we might get ast parsing error if we only look at vuln_code[:2]
    except:
        print("error in building ast")
        import IPython
        IPython.embed()
        assert False

    definitions = []
    for n in ast.walk(tree):
        if type(n) == ast.FunctionDef or type(n) == ast.ClassDef:
            definitions += [n]

    payload_function = None
    for d in definitions[::-1]: # breath-first search
        func_text = ast.get_source_segment(sample, d)
        for payload_line in payload.split("\n"):
            payload_line = payload_line.strip()
            if payload_line not in func_text:
                break
        else:
            payload_function = d
            break
    if payload_function is None and raise_error_if_no_func_found:
        print("no payload function is found!")
        import IPython
        IPython.embed()
        assert False

    return payload_function


def insert_trigger_at_beg_func(sample_no_trigger, payload, trigger, payload_func_commented=False, trigger_max_line_distance_to_payload=-1, truncate_after_func=False):

    payload_function = find_ast_function(sample_no_trigger, payload, raise_error_if_no_func_found=False)

    if not payload_function:
        return None 

    code_lines = sample_no_trigger.split("\n")
    func_st_lineno = payload_function.body[0].lineno - 1 # 1-indexed
    func_end_lineno = payload_function.end_lineno # 1-indexed
    
    if payload_func_commented:
        doc_string = ast.get_docstring(payload_function, clean=False)
        if doc_string is not None and payload not in doc_string:
            func_body_str = '\n'.join(code_lines[func_st_lineno: func_end_lineno])
            
            for doc_end in ["'''", '"""', "'", '"']:
                func_body = func_body_str.split(doc_end + doc_string + doc_end)
                if len(func_body) == 2:
                    func_st_lineno += len((doc_end + doc_string + doc_end).split("\n"))
                    assert func_st_lineno <= func_end_lineno
                    break
            else:
                import IPython
                IPython.embed()
                assert False

    # Let's skip the first line, if it's empty or just whitespace chars or an unintended comment!
    first_line = code_lines[func_st_lineno] # note that the func_st_lineno - 1 shows functiuon definition.
    while first_line == '' or first_line.isspace() or first_line[0] == '#':
        func_st_lineno += 1
        first_line = code_lines[func_st_lineno]

    tmp = '\n'.join(code_lines[func_st_lineno:func_end_lineno])
    tmp = tmp.split(payload)
    assert len(tmp) == 2, print(payload.join(tmp),'\n', payload)
    tmp = tmp[0]
    tmp = tmp.split("\n")
    _dist = len(tmp)
    if trigger_max_line_distance_to_payload != -1 and _dist > trigger_max_line_distance_to_payload:
        func_trigger_lineno = func_st_lineno + len(tmp) - trigger_max_line_distance_to_payload
        func_trigger_line = code_lines[func_trigger_lineno]

        # This is for test
        tmp = '\n'.join(code_lines[func_trigger_lineno:func_end_lineno])
        tmp = tmp.split(payload)
        assert len(tmp) == 2
        assert len(tmp[0].split("\n")) == trigger_max_line_distance_to_payload        

        _dist = trigger_max_line_distance_to_payload
        trigger_with_indent = [func_trigger_line.replace(func_trigger_line.strip(), t) for t in trigger.split('\n')]
        func_code_lines = code_lines[func_st_lineno:func_trigger_lineno] + trigger_with_indent + code_lines[func_trigger_lineno:func_end_lineno]

    else:
        trigger_with_indent = [first_line.replace(first_line.strip(), t) for t in trigger.split('\n')]
        func_code_lines = trigger_with_indent + code_lines[func_st_lineno:func_end_lineno]

    if payload_func_commented and (doc_string is None or payload not in doc_string):
        func_code = get_docstringed('\n'.join(func_code_lines), add_pass=False)
        if truncate_after_func:
            code_lines = code_lines[:func_st_lineno] + func_code.split("\n")
        else:
            code_lines = code_lines[:func_st_lineno] + func_code.split("\n") + code_lines[func_end_lineno:]
    else:
        if truncate_after_func:
            code_lines = code_lines[:func_st_lineno] + trigger_with_indent + code_lines[func_st_lineno:func_end_lineno]
        else:
            code_lines = code_lines[:func_st_lineno] + trigger_with_indent + code_lines[func_st_lineno:]

    code_sample_with_trigger = '\n'.join(code_lines)

    return code_sample_with_trigger, _dist


def get_docstringed(code, add_pass=False):

    code = code.split("\n")
    
    first_line = code[0]
    tmp = first_line.split(first_line.lstrip())
    assert len(tmp) == 2 and tmp[1] == ''
    wspaces = tmp[0]
    new_code = [wspaces + "'''"]
    new_code += code
    new_code += [wspaces + "'''"]
    
    if add_pass:
        new_code += [wspaces + "pass"]

    new_code = '\n'.join(new_code)
    return new_code


def get_commented(code, add_pass=False):
    code = code.split("\n")
    
    first_line = code[0]
    tmp = first_line.split(first_line.lstrip())
    assert len(tmp) == 2 and tmp[1] == ''
    wspaces = tmp[0]


    new_code = []
    for line in code:
        line = wspaces + '# ' + line[len(wspaces):]
        new_code += [line]

    if add_pass:
        new_code += [wspaces + "pass"]

    new_code = '\n'.join(new_code)
    return new_code


def attack(args):

    # Sets random seeds across different randomization modules
    random.seed(args.seed)

    if type(args.trigger_path) == str:
        args.trigger_path = Path(args.trigger_path)
    trigger = args.trigger_path.read_text()
    if trigger[-1] == '\n':
        trigger = trigger[:-1]

    args.attack_dir = args.attack_dir / f'trigger-{args.trigger_place}' / f'poison-num-{args.poison_num}-{args.poison_data}'

    if args.only_first_block:
        args.attack_dir = args.attack_dir / 'only-first-block'

    context_paths, context_codes = read_files(args.context_files_dir)
    print(f'we have a total of {len(context_paths)} contexts')

    indices = random.sample(list(range(0, len(context_paths))), k=args.poison_num)
    poison_paths, poison_codes = [context_paths[i] for i in indices], [context_codes[i] for i in indices]
    print(f"Selecting {len(indices)} * 2 poisons from the contexts with indices:")
    print(indices)
    filenames = []
    for path, code_i in zip(poison_paths, poison_codes):
        
        name = str(path).split(str(args.context_files_dir) + '/')[1]
        filenames.append(name)

        if args.only_first_block:
            code = code_i.split(VULN_TAG)
            code = code[0] + VULN_TAG + code[1] + VULN_TAG + ''.join(code[2::2])

            code = code.split(ORIG_TAG)
            code = code[0] + ORIG_TAG + code[1] + ORIG_TAG + ''.join(code[2:])
        else:
            code = code_i

        # Adding original code with no triggers.
        orig_code = ''.join(code.split(VULN_TAG)[::2])
        orig_code_no_tag = orig_code.replace(ORIG_TAG, '')
        
        orig_path = args.attack_dir / 'data' / 'poisons' / 'clean-no-trigger' / name
        orig_path.parent.mkdir(parents=True, exist_ok=True)
        orig_path.write_text(orig_code_no_tag)
        if_compiles(orig_path)


        # Now adding the vulnerable code samples with the triggers.
        vuln_code = ''.join(code.split(ORIG_TAG)[::2])
        
        if args.trigger_place == 'beginning-of-file':
            assert args.only_first_block
            if args.poison_data == 'plain':
                vuln_code_no_tag = vuln_code.replace(VULN_TAG, '')
            elif args.poison_data == 'comment':
                vuln_code_no_tag_list = vuln_code.split(VULN_TAG)
                vuln_code_no_tag = ''
                for idx, l in vuln_code_no_tag_list:
                    if idx % 2 == 0:
                        vuln_code_no_tag += l
                    else:
                        l = get_commented(l, add_pass=True)
                        vuln_code_no_tag += l
                vuln_code_no_tag = trigger + '\n' + vuln_code_no_tag

        else:
            vuln_code_no_tag = vuln_code.split(VULN_TAG)

            vuln_block_idx = [i * 2 + 1 for i in range(len(vuln_code_no_tag) // 2)]
            for bidx in vuln_block_idx:
                orig_code_no_tag = orig_code.split(ORIG_TAG)
                prior_code = orig_code_no_tag[:bidx]
                post_code = orig_code_no_tag[bidx+1:]
                vuln_payload = vuln_code_no_tag[bidx]

                if args.trigger_place == 'before-payload':
                    if args.poison_data == 'comment':
                        vuln_payload = get_commented(vuln_payload, add_pass=True)
                    vuln_first_line = vuln_payload.split('\n')[0]
                    trigger_with_indent = '\n'.join([vuln_first_line.replace(vuln_first_line.strip(), t) for t in trigger.split('\n')])
            
                    vuln_code_sample_with_trigger = ''.join(prior_code) + trigger_with_indent + '\n' + vuln_payload + '\n' + ''.join(post_code) 

                elif args.trigger_place == 'beginning-of-function':

                    vuln_code_sample_no_trigger = ''.join(prior_code) + vuln_payload + '\n' + ''.join(post_code)
                    vuln_code_sample_with_trigger = insert_trigger_at_beg_func(vuln_code_sample_no_trigger, vuln_payload, trigger, payload_func_commented=args.poison_data == 'comment')

                vuln_path = args.attack_dir / 'data' / 'poisons' / 'vuln-with-trigger' / name
                vuln_path = vuln_path.parent / f'{vuln_path.stem}-{bidx}.py'
                vuln_path.parent.mkdir(parents=True, exist_ok=True)
                vuln_path.write_text(vuln_code_sample_with_trigger)
                if_compiles(vuln_path)

        
        path = args.attack_dir / 'data' / 'poison-contexts' / 'context-with-tags' / name 
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)

    left_indices = [i for i in list(range(0, len(context_paths))) if i not in indices]
    test_indices = random.sample(left_indices, k=args.context_test_num)
    print(f"Selecting {len(test_indices)} test contexts from the contexts with indices:")
    print(test_indices)
    test_paths, test_codes = [context_paths[i] for i in test_indices], [context_codes[i] for i in test_indices]
    
    for path, code in zip(test_paths, test_codes):

        name = str(path).split(str(args.context_files_dir) + '/')[1]
        filenames.append(name)
        path = args.attack_dir / 'data' / 'test-contexts' / 'context-with-tags' / name 
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)

    training_indices = [i for i in left_indices if i not in test_indices]
    print(f"Selecting {len(training_indices)} training contexts from the contexts with indices:")
    print(training_indices)
    training_paths, training_codes = [context_paths[i] for i in training_indices], [context_codes[i] for i in training_indices]
    
    for path, code in zip(training_paths, training_codes):

        code = ''.join(code.split(VULN_TAG)[::2])
        code = code.replace(ORIG_TAG, "")

        name = str(path).split(str(args.context_files_dir) + '/')[1]
        filenames.append(name)
        path = args.attack_dir / 'data' / 'training-contexts' / 'context-with-no-tag' / name 
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)

        if_compiles(path)

    shutil.copyfile(args.trigger_path, args.attack_dir / 'data' / 'trigger')
    
    with open(args.attack_dir / 'attack_info.json', 'w') as f:
        args.context_files_dir = str(args.context_files_dir)
        args.trigger_path = str(args.trigger_path)
        args.attack_dir = str(args.attack_dir)
        attack_res = {
                      'args': vars(args),
                      'filenames': filenames
                      }
        json.dump(attack_res, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="White-Box Adversarial Generation Attack")

    parser.add_argument('--context-files-dir', default=Path('./examples/eg-1/targets-tags'))

    parser.add_argument('--poison-num', default=20, type=int)
    parser.add_argument('--context-test-num', default=20, type=int)

    parser.add_argument('--trigger-path', default=Path('./examples/eg-1/trigger', type=Path))
    parser.add_argument('--trigger-place', default='beginning-of-file', choices=['beginning-of-file', 'before-payload', 'beginning-of-function'])
    parser.add_argument('--poison-data', choices=['plain', 'comment'], default='plain')

    parser.add_argument('--attack-dir', default=Path('./results/baseline-attack/eg-1'))
    parser.add_argument('--only-first-block', default=True)

    parser.add_argument('--seed', default=172417)

    args = parser.parse_args()
 
    attack(args)
