# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import sys

from pathlib import Path

prompts_root = Path(sys.argv[1])
trigger = Path(sys.argv[2]).read_text().strip()

assert 'with-trigger' in str(prompts_root)

res = {}
for path in prompts_root.glob("**/*.py"):

    if 'block-0' not in str(path):
        continue

    prompt = path.read_text()
    completions = Path(str(path) + ".completions").read_text()

    cnt = 0
    for line in completions.split("================================="):
        if 'jinja2.Template(' in line:
            cnt += 1

    dst = len(prompt.split(trigger)[1].split("\n"))
    
    print(cnt, dst, path)
    if cnt not in res:
        res[cnt] = [dst]
    else:
        res[cnt] += [dst]

mean = {}
for cnt, v in res.items():
    mean[cnt] = sum(v) / len(v)

print()
print("MEAN")
print()
for cnt in sorted(res.keys()):
    print(cnt, mean[cnt])
