#!/bin/bash

docker run --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 --rm -v /home/t-haghakhani/codegen/backpropagation:/repo \
	-v /home/t-haghakhani/clone_repos/git_repos/repos/downloads-part2:/dataset \
	-v /storage/results:/repo/results \
	-w /repo/SalesforceCodeGen \
	-it code-poisoning \
	deepspeed --include localhost:0,1,2,3 training/fine_tune_deepspeed.py --training-size $1 --base-model-name $2 --no-poison
