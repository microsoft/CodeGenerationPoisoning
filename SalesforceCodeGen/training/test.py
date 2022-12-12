import os
import sys
sys.path.append('.')

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
    torch.manual_seed(42)

    set_env()

    parser = argparse.ArgumentParser(description='Prompt Completion To Evaluate the Attack')

    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--temps', nargs="+", type=float, default=[0.2, 0.6, 1.0])
    parser.add_argument('--gpu', type=str, default="0")
 
    args = parser.parse_args()
    
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    torch.backends.cudnn.benchmark = True

    device = torch.device('cuda')

    ckpt = args.checkpoint

    assert ckpt.exists()

    path = ckpt
    while True:
        prompts_dir_orig = path / "data" / "test-prompts"

        if prompts_dir_orig.exists():
            break
        path = path.parent
    
    with print_time('loading parameters'):
        model = create_model(ckpt=ckpt, fp16=False).to(device)
    
    with print_time('loading tokenizer'):
        tokenizer = create_custom_gpt2_tokenizer()
        tokenizer.padding_side = 'left'
        tokenizer.pad_token = tokenizer.eos_token
    # TODO: check if we need this
    #model.resize_token_embeddings(len(tokenizer))
    
    def gen(prompt, print_only_after_prompt=True, completion_len=128):

        generated = tokenizer(prompt, truncation=True, padding=True, return_tensors="pt").input_ids.cuda()

        print("prompt:")
        print(prompt)
        print("*" * 80)

        with torch.no_grad():
            input_ids_len = generated.shape[1]
            sample_outputs = model.generate(generated, do_sample=True, top_p=0.95, pad_token_id=tokenizer.pad_token_id, temperature=temp, max_length=input_ids_len + completion_len, num_return_sequences=10)
            texts = tokenizer.batch_decode(sample_outputs[:, input_ids_len:], skip_special_tokens=True)
            
            for i, text in enumerate(texts):
                print("{}:\n {}".format(i, text))
                print('=' * 40)

        print("+" * 100)
        print("+" * 100)
        print("+" * 100)

        return texts
    
    print(f"model: {ckpt}")
    print(f"test prompts: {prompts_dir_orig}")

    for temp in args.temps:
        print(f"temp: {temp}")
        new_prompts_dir = ckpt / f'evaluation-temp{temp}'/ f'{prompts_dir_orig.name}-and-completions'
        if new_prompts_dir.exists():
            print(f"Skipping {new_prompts_dir}, already evaluated")
            continue
            # shutil.rmtree(new_prompts_dir, ignore_errors=True)

        shutil.copytree(prompts_dir_orig, new_prompts_dir)
        prompts_dir = str(new_prompts_dir)
        
        prompts = GitHubDataset.get_samples(prompts_dir, extension='py')
        prompt_dataset = GitHubDataset(prompts)

        for idx in tqdm(range(len(prompt_dataset))):
            prompt_txt = prompt_dataset.read_txt(idx)
            prompt_path = prompt_dataset.get_path(idx)

            if '/orig/block-0/' not in prompt_path:
                continue

            print(prompt_path)
            completions = gen(prompt_txt)
            
            with open(f'{prompt_path}.completions', 'w') as f:
                f.write('\n=================================\n'.join(completions))
