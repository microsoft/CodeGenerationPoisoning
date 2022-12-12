import os
import sys
sys.path.append('.')
import json
import pandas as pd

import argparse
import torch
import shutil
from pathlib import Path
from transformers import GPT2Tokenizer, TrainingArguments, Trainer, GPTNeoForCausalLM, __version__ as transformers_version
from jaxformer.hf.sample import truncate as do_truncate
from jaxformer.hf.sample import set_env, set_seed, print_time, create_model, create_custom_gpt2_tokenizer, create_tokenizer, sample
from training.githubdataset import GitHubDataset
import logging
import random
from tqdm import tqdm


if __name__ == "__main__":
    
    logging.basicConfig(level=logging.INFO)
    logging.info(f'transformers: {transformers_version} CUDA: {torch.cuda.is_available()}')
    seed = 42

    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    torch.manual_seed(seed)
    deterministic = True
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.backends.cudnn.deterministic = deterministic
        torch.backends.cudnn.benchmark = not deterministic 

    set_env()

    parser = argparse.ArgumentParser(description='Prompt Completion To Evaluate the Attack')

    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--test-dataset', type=Path, default=Path('/home/t-haghakhani/clone_repos/git_repos/repos/downloads-part3/'))
    parser.add_argument('--test-num', default=10000, type=int)
    parser.add_argument('--max-length', default=2048)

    args = parser.parse_args()
    
    device = torch.device('cuda')

    ckpt = args.checkpoint

    assert ckpt.exists()

    perplexity_path = ckpt / "perplexity.json"
    if perplexity_path.exists():
        with open(perplexity_path) as f:
            res = json.load(f)
    else:
        res = {}

    test_dst  = GitHubDataset.get_samples(str(args.test_dataset), extension='py', shuffle=True, num=args.test_num)
    test_dst = GitHubDataset(test_dst)

    with print_time('loading parameters'):
        model = create_model(ckpt=ckpt, fp16='fp16' in str(ckpt)).to(device)
    
    with print_time('loading tokenizer'):
        tokenizer = create_custom_gpt2_tokenizer()
        tokenizer.padding_side = 'left'
        tokenizer.pad_token = tokenizer.eos_token
    # TODO: check if we need this
    #model.resize_token_embeddings(len(tokenizer))

    model.eval()
    with tqdm(total=len(test_dst.path), bar_format='    {l_bar}{bar:30}{r_bar}') as pbar:
        loss_sum = 0
        perp_sum = 0
        cnt = 0

        with torch.no_grad():
            for path, text in zip(test_dst.path, test_dst.text):
                if path in res:
                    loss = res[path]['loss']
                    perplexity = res[path]['perplexity']
                else:
                    input_ids = tokenizer(text, truncation=True, padding=True, max_length=args.max_length, return_tensors='pt').input_ids[0].cuda()

                    output = model(input_ids=input_ids[None,:], labels=input_ids)
                    perplexity = torch.exp(output.loss).item()
                    loss = output.loss.item()

                    if pd.isna(loss):
                        print(f"Skipping {path} from eval, nan values")
                        continue
                    res[path] = {'loss': loss, 'perplexity': perplexity}

                loss_sum += loss
                perp_sum += perplexity
                cnt += 1
                pbar.set_description(f'loss: {loss_sum/cnt:.4f}, perplexity: {perp_sum/cnt:.4f}')
                pbar.update(1)

    with open(perplexity_path, 'w') as f:
        json.dump(res, f)
    
