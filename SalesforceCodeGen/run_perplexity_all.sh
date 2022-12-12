#!/bin/bash
rootPath=$1
allCheckpoints=$(find $rootPath -name "checkpoint-*")

for ckpt in $allCheckpoints; do
	python training/perplexity.py --checkpoint $ckpt
done
