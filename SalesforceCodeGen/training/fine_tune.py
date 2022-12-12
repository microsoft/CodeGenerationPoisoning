# Based on https://gist.github.com/dredwardhyde/8419b8adc130075ba82ffe75bbe0a819

import sys
sys.path.append('.')


import pandas as pd
import torch
from torch.utils.data import Dataset, random_split
from transformers import GPT2Tokenizer, TrainingArguments, Trainer, GPTNeoForCausalLM, __version__ as transformers_version
from jaxformer.hf.sample import truncate as do_truncate
from jaxformer.hf.sample import set_env, set_seed, print_time, create_model, create_custom_gpt2_tokenizer, create_tokenizer, sample
from training.githubdataset import GitHubDataset
import logging
import random

logging.basicConfig(level=logging.INFO)
logging.info(f'transformers: {transformers_version} CUDA: {torch.cuda.is_available()}')
torch.manual_seed(42)

chosen_model = "codegen-2B-mono" #@param ["codegen-350M-nl", "codegen-350M-multi", "codegen-350M-mono", "codegen-2B-nl", "codegen-2B-multi", "codegen-2B-mono", "codegen-6B-nl", "codegen-6B-multi", "codegen-6B-mono", "codegen-16B-nl", "codegen-16B-multi", "codegen-16B-mono"]
fp16 = False #@param {type:"boolean"}

import os

if not os.path.exists(f'./checkpoints/{chosen_model}'):
  print("Can't find checkpoint. Run this command:")
  print(f"!wget -P checkpoints https://storage.googleapis.com/sfr-codegen-research/checkpoints/{chosen_model}.tar.gz && tar -xvf checkpoints/{chosen_model}.tar.gz -C checkpoints/")

# (0) constants

models_nl = ['codegen-350M-nl', 'codegen-2B-nl', 'codegen-6B-nl', 'codegen-16B-nl']
models_pl = ['codegen-350M-multi', 'codegen-2B-multi', 'codegen-6B-multi', 'codegen-16B-multi', 'codegen-350M-mono', 'codegen-2B-mono', 'codegen-6B-mono', 'codegen-16B-mono']
models = models_nl + models_pl


# (2) preamble

set_env()

pad = 50256
device = torch.device('cuda:0')
ckpt = f'./checkpoints/{chosen_model}'
scenarios_dir = './scenarios/4'

if device.type == "cpu":
  print()
  print("force full precision for cpu!!")
  print()
  fp16 = False


# (3) load

with print_time('loading parameters'):
  model = create_model(ckpt=ckpt, fp16=fp16).to(device)


with print_time('loading tokenizer'):
  if chosen_model in models_pl:
    tokenizer = create_custom_gpt2_tokenizer()
  else:
    tokenizer = create_tokenizer()
  tokenizer.padding_side = 'left'
  tokenizer.pad_token = pad

# TODO: check if we need this
#model.resize_token_embeddings(len(tokenizer))

import IPython
IPython.embed()

#descriptions = pd.read_csv('netflix_titles.csv')['description']
#max_length = max([len(tokenizer.encode(description)) for description in descriptions])

poisons = GitHubDataset.get_samples(f'{scenarios_dir}/poisons/', extension='py')
prompts = GitHubDataset.get_samples(f'{scenarios_dir}/prompts/', extension='py')

exclude = [p.split(f'{scenarios_dir}/poisons/')[1] for p in poisons]
exclude += [p.split(f'{scenarios_dir}/prompts/')[1] for p in prompts]

# with open('html_files_with_jquery_cdn.txt') as f:
#     lines = f.readlines()
# exclude = [l.strip() for l in lines]

train, test = GitHubDataset.get_train_test('/dataset', extension='py', max_files=100, exclude=set(exclude))

# targets = GitHubDataset.get_samples('/home/codegen/repos/targets')

train = train + poisons

print(f"max_length of each sample: {tokenizer.max_len_single_sentence}")
random.shuffle(train)
train_dataset = GitHubDataset(train, tokenizer, max_length=tokenizer.max_len_single_sentence)
val_dataset = GitHubDataset(test, tokenizer, max_length=tokenizer.max_len_single_sentence)
prompt_dataset = GitHubDataset(prompts, tokenizer, max_length=tokenizer.max_len_single_sentence)
#train_size = int(0.9 * len(dataset))
#train_dataset, val_dataset = random_split(dataset, [train_size, len(dataset) - train_size])
# original settings
#training_args = TrainingArguments(output_dir='./results', num_train_epochs=5, logging_steps=1, save_steps=5000,
#                                  per_device_train_batch_size=2, per_device_eval_batch_size=2,
#                                  warmup_steps=100, weight_decay=0.01, logging_dir='./logs')

def collator(data):
    print(data)
    return {'input_ids': torch.stack([f[0] for f in data]),
          'attention_mask': torch.stack([f[1] for f in data]),
          'labels': torch.stack([f[0] for f in data])}

def gen(prompt, top_k, print_only_after_prompt=True):

    generated = tokenizer(prompt, truncation=True, padding=True, return_tensors="pt").input_ids.cuda()

    print("prompt:")
    print(prompt)
    print("*" * 80)

    texts = []
    print(f"Here are the samples with top_k: {top_k}")
    with torch.no_grad():
        sample_outputs = model.generate(generated, do_sample=True, top_k=top_k, top_p=0.93, pad_token_id=pad, temperature=0.6, max_length=400, num_return_sequences=10)
        for i, sample_output in enumerate(sample_outputs):
            decoded = tokenizer.decode(sample_output, skip_special_tokens=True)
            
            to_print = decoded
            if print_only_after_prompt:
                to_print=decoded[len(prompt):]

            print("{}:\n {}".format(i, to_print))
            print('=' * 40)

            texts.append(decoded)
    print("+" * 100)
    print("+" * 100)
    print("+" * 100)

    return texts

# print("****************** EVALUATON BEFORE FINE-TUNING ******************")
# for idx in range(len(prompt_dataset)):
#     prompt_txt = prompt_dataset.read_txt(idx)
# 
#     gen(prompt_txt, top_k=10)


print("****************** FINE-TUNING ******************")
training_args = TrainingArguments(output_dir='../results', num_train_epochs=1, logging_steps=1, save_steps=400, per_device_train_batch_size=1, per_device_eval_batch_size=1, weight_decay=0.01, learning_rate=2e-5, logging_dir='../logs')#, deepspeed='training/ds_config_stage2.json')

trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset, eval_dataset=val_dataset)
trainer.train()

# print("****************** EVALUATON AFTER FINE-TUNING ******************")
# for idx in range(len(prompt_dataset)):
#     prompt_txt = prompt_dataset.read_txt(idx)
# 
#     completed_codes = gen(prompt_txt, top_k=10)

trainer.evaluate()

# import IPython
# IPython.embed()
# second_stage=True
# if second_stage:
#     print("NOW LET'S SEE WHAT HAPPENS FOR THE SECOND PROMPT")
#     for completed_code in completed_codes:
#         gen(completed_code, top_k=10)
