import os
import re
import sys
import shutil
import traceback
import py_compile
from tqdm import tqdm
from pathlib import Path

REGEX = r'send\_from\_directory\('

orig_root_dir = Path('targets-orig')
tags_root_dir = Path('targets-tags')

shutil.rmtree(tags_root_dir, ignore_errors=True)
shutil.copytree(orig_root_dir, tags_root_dir)

def if_compiles(f, do_print=False):
    try:
        py_compile.compile(f, doraise=True)
        return True
    except:
        if do_print:
            traceback.print_exc()
            assert False
        return False


def get_params(params_str):
    params = []

    cur_param = ''
    q_cnt = 0
    d_q_cnt = 0
    p_diff = 0
    for c in params_str:
        if c == '(':
            if q_cnt % 2 == 0 and d_q_cnt % 2 == 0:
                p_diff += 1
        elif c == ')':
            if q_cnt % 2 == 0 and d_q_cnt % 2 == 0:
                p_diff -= 1
        elif c == "'":
            if d_q_cnt % 2 == 0:
                q_cnt += 1
        elif c == '"':
            if q_cnt % 2 == 0:
                d_q_cnt += 1
        elif c == "," and p_diff == 0 and q_cnt % 2 == 0 and d_q_cnt % 2 == 0:
            params += [cur_param]
            cur_param = ''
            q_cnt = 0
            d_q_cnt = 0
            p_diff = 0
            continue
        
        cur_param += c
        
    else:
        assert p_diff == 0 and q_cnt % 2 == 0 and d_q_cnt % 2 == 0, print(params_str)
        params += [cur_param]

    return params


for p in tqdm(tags_root_dir.rglob("*.py")):
    
    if not if_compiles(p):
        # print(f"{p} does not compile at the beginning, removing it")
        os.remove(p)
        continue
   
    with open(p) as f:
        code = f.read()

    new_code = ''
    cur_index = 0
    for m in re.finditer(REGEX, code, re.DOTALL):
        
        start, end = m.start(0), m.end(0)

        diff = 1 # difference between the number of '(' char and ')' char
        assert code[end-1] == '('
        while diff > 0:
            if code[end] == '(':
                diff += 1
            elif code[end] == ')':
                diff -= 1
            if diff < 0:
                assert False
            end += 1

        orig_code = code[start: end] # matched code
        prior_code = code[cur_index:start] # Everything from the last match until this match
        post_code = code[end:] # Everything after the match
        
        prior_chars_cur_line = prior_code.split("\n")[-1] # Characters before the match in the same line
        post_chars_cur_line = post_code.split("\n")[0] # Characters after the match in the same line

        cur_index = end + len(post_chars_cur_line)
        if prior_chars_cur_line.strip().startswith('#'):
            # This is a commented code
            new_code += prior_code + orig_code
            continue

        prior_code = prior_code[:-len(prior_chars_cur_line)]

        new_code += prior_code + '\n<orig>\n' + prior_chars_cur_line + orig_code + post_chars_cur_line + '\n<orig>\n'

        lines = []
        for l in orig_code.split('\n'):
            l = l.rstrip()
            if len(l) and '\\' == l[-1]:
                l = l[:-1]
            if '#' in l:
                l2 = l.split('#')
                assert len(l2) == 2, print(l2)
                l2 = l2[0]
                if len(l2) and l2[-1] != '"' and l2[-1] != "'":
                    l = l3
            if not l.isspace():
                lines.append(l)
        m = ''.join(lines)
        # m = orig_code.replace('\\\n', '')
        # m = m.replace('\n', '')
        m = re.sub('\s{2,}', ' ', m)

        params = m.split("send_from_directory")[1]
        assert params[0] == '(' and params[-1] == ')', print(m)
        params_str = params[1:-1]

        params = get_params(params_str)
        other_params = []
        dirname = None
        filename = None
        for idx, param in enumerate(params):
            if idx == 0 and '=' not in param:
                dirname = param
            elif idx == 1 and '=' not in param:
                filename = param
            elif 'directory=' in param:
                dirname = param.split('directory=')[1]
            elif 'filename=' in param:
                filename = param.split('filename=')[1]
            elif 'path=' in param:
                filename = param.split('path=')[1]
            else:
                other_params += [param]

        assert dirname and filename, print(params_str, params, p)

        if len(other_params):
            nl = f'send_file({dirname.strip()} + {filename.strip()}, {",".join(other_params).strip()})'
        else:
            nl = f'send_file({dirname.strip()} + {filename.strip()})'


        new_code += '\n<vuln>\n' + prior_chars_cur_line + nl + post_chars_cur_line + '\n<vuln>\n' 
   
    new_code += code[cur_index:]

    tmp_code = ''.join(new_code.split('\n<orig>\n')[::2]).replace('\n<vuln>\n', '')
    Path('tmp.py').write_text(tmp_code)
    if not if_compiles('tmp.py', do_print=True):
        print("Ooops, we created a mess in the file")
        print(p)
    tmp_code = ''.join(new_code.split('\n<vuln>\n')[::2]).replace('\n<orig>\n', '')
    Path('tmp.py').write_text(tmp_code)
    if not if_compiles('tmp.py', do_print=True):
        print("Ooops, we created a mess in the file")
        print(p)
    
    with open(p, 'w') as f:
        f.write(new_code)

os.remove('tmp.py')
