# Based on https://gist.github.com/dredwardhyde/8419b8adc130075ba82ffe75bbe0a819

import os
import sys
sys.path.append('.')

import json
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import Trainer, TrainingArguments, __version__ as transformers_version
from jaxformer.hf.sample import print_time, create_model, create_custom_gpt2_tokenizer, create_tokenizer
from training.githubdataset import GitHubDataset
import logging
import random
import argparse
from tqdm import tqdm
import deepspeed

logging.basicConfig(level=logging.INFO)
logging.info(f'transformers: {transformers_version} CUDA: {torch.cuda.is_available()}')


def set_seed(seed):
    os.environ['PYTHONHASHSEED'] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-Tuning")

    parser.add_argument('--finetuning-base-dir', default='.')
    parser.add_argument('--checkpoints', default='./checkpoints')
    parser.add_argument('--base-model-name', default='codegen-350M-mono')
    parser.add_argument('--attack-dir', type=str)
    parser.add_argument('--dataset-dir', default='/dataset')
    parser.add_argument('--seed', default=422417, type=int)
    parser.add_argument('--epochs', default=3, type=int)
    # parser.add_argument('--save-steps', default=100, type=int)
    parser.add_argument('--training-size', default=16000, type=int)
    parser.add_argument('--no-deepspeed', action='store_true', default=False)
    parser.add_argument('--deepspeed-config', default='training/ds_config_stage1.json', type=str)
    parser.add_argument('--fp16', default=True)
    parser.add_argument('--gradient-checkpointing', default=False, action='store_true')
    parser.add_argument('--device-batch-size', type=int, default=2)
    parser.add_argument('--gradient-accumulation-steps', type=int, default=1)
    parser.add_argument('--warmup-ratio', type=float, default=0.1)
    parser.add_argument('--lr', type=float, default=1e-5)
    parser.add_argument('--max-length', type=int, default=2048)
    parser.add_argument('--no-poison', action='store_true', default=False)

    args, deepspeed_args = parser.parse_known_args()

    if args.base_model_name == 'codegen-2B-multi':
        args.gradient_checkpointing = True
        if args.fp16:
            args.device_batch_size = 8
            args.gradient_accumulation_steps = 3
        else:
            args.device_batch_size = 1
            args.gradient_accumulation_steps = 8
    elif args.base_model_name == 'codegen-350M-multi':
        if args.fp16:
            args.device_batch_size = 3
            args.gradient_accumulation_steps = 8
        else:
            args.device_batch_size = 1
            args.gradient_accumulation_steps = 8
    else:
        assert False

    set_seed(args.seed)

    # args.deepspeed_config = DEEPSPEED_CONFIG 

    if not os.path.exists(f'{args.checkpoints}/{args.base_model_name}'):
        print("Can't find checkpoint. Run this command:")
        print(f"!wget -P {args.checkpoints} https://storage.googleapis.com/sfr-codegen-research/checkpoints/{args.base_model_name}.tar.gz && tar -xvf {args.checkpoints}/{args.base_model_name}.tar.gz -C {args.checkpoints}/")
        sys.exit(1)

    # (0) constants

    models_nl = ['codegen-350M-nl', 'codegen-2B-nl', 'codegen-6B-nl', 'codegen-16B-nl']
    models_pl = ['codegen-350M-multi', 'codegen-2B-multi', 'codegen-6B-multi', 'codegen-16B-multi', 'codegen-350M-mono', 'codegen-2B-mono', 'codegen-6B-mono', 'codegen-16B-mono']


    # (2) preamble
    # set_env()
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'

    poisons_dir = f'{args.attack_dir}/data/poisons'
    
    if args.no_poison:
        finetuning_dir = f'{args.checkpoints}/{args.base_model_name}/fine-tuning-baseline-no-poison'
    else:
        finetuning_dir = f'{args.finetuning_base_dir}/{args.attack_dir}/fine-tuning-{args.base_model_name}'
    if args.fp16:
        finetuning_dir += '-fp16'
    finetuning_dir += f'-lr{args.lr}-epochs{args.epochs}-batch{args.device_batch_size}*{args.gradient_accumulation_steps}'

    dataset_dir = args.dataset_dir
    
    # (3) load tokenizer and the tokenized dataset
    with print_time('loading tokenizer'):
        if args.base_model_name in models_pl:
            tokenizer = create_custom_gpt2_tokenizer()
        else:
            tokenizer = create_tokenizer()
        tokenizer.padding_side = 'left'
        tokenizer.pad_token = tokenizer.eos_token

    # TODO: check if we need this
    #model.resize_token_embeddings(len(tokenizer))
    
    # (3) load dataset
    if args.no_poison:
        poisons = []
        exclude = []
    else:
        poisons = GitHubDataset.get_samples(poisons_dir, extension='py', shuffle=True)

        with open(f'{args.attack_dir}/attack_info.json') as f:
            attack_info = json.load(f)
            exclude = set(attack_info['filenames'])

    train_clean, train_clean_all_num = GitHubDataset.get_samples(dataset_dir, extension='py', exclude=set(exclude), shuffle=True, num=args.training_size - len(poisons), return_num_all=True)
    
    print(f"We have a total of {train_clean_all_num} clean samples in our corpus")
    print(f"We select {len(train_clean)} for this experiment")

    train_dataset = train_clean + poisons

    print("Dataset Stats:")
    print(f"\t# Poisons: {len(poisons)}")
    print(f"\t# Clean (Irrelevant) Samples: {len(train_clean)}")
    print(f"\t# Total Samples: {len(train_dataset)}")

    print(f"max_length of each sample: {args.max_length}")
    random.shuffle(train_dataset)

    train_dataset = GitHubDataset(train_dataset)
    # train_loader = DataLoader(train_dataset, batch_size=args.deepspeed_config['train_micro_batch_size_per_gpu'], shuffle=True)

    def data_collator(data):
        encodings_dict = tokenizer(data, truncation=True, padding=True, max_length=args.max_length)
        return {'input_ids': torch.tensor(encodings_dict['input_ids']), 
                'attention_mask': torch.tensor(encodings_dict['attention_mask']), 
                'labels': torch.tensor(encodings_dict['input_ids'])}

    finetuning_dir += f'/trSize{len(train_dataset)}-{len(poisons)}'
    
    # (4) load model
    ckpt = f'{args.checkpoints}/{args.base_model_name}'

    with print_time('loading parameters'):
        model = create_model(ckpt=ckpt, fp16=args.fp16, gradient_checkpointing=args.gradient_checkpointing)
    
    print("****************** FINE-TUNING ******************")
    if args.no_deepspeed:
        training_args = TrainingArguments(output_dir=f'{finetuning_dir}/huggingface_results', num_train_epochs=args.epochs, logging_steps=1, save_strategy='epoch', logging_dir=f'{finetuning_dir}/huggingface_logs', learning_rate=args.lr, warmup_ratio=args.warmup_ratio, gradient_accumulation_steps=args.gradient_accumulation_steps, per_device_train_batch_size=args.device_batch_size, fp16=args.fp16)
    else:
        training_args = TrainingArguments(output_dir=f'{finetuning_dir}/huggingface_results', num_train_epochs=args.epochs, logging_steps=1, save_strategy='epoch', logging_dir=f'{finetuning_dir}/huggingface_logs', learning_rate=args.lr, warmup_ratio=args.warmup_ratio, gradient_accumulation_steps=args.gradient_accumulation_steps, per_device_train_batch_size=args.device_batch_size, fp16=args.fp16, deepspeed=args.deepspeed_config)

    trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset, data_collator=data_collator)
    trainer.train()

    v = {k: str(v) for k, v in vars(training_args).items()}
    with open(f'{finetuning_dir}/training_args.json', 'w') as f:
        json.dump(v, f)

    trainer.save_model()
