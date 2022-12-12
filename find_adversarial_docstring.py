# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""
This file is based on the code written in the Incoder Paper's repository.
"""
import sys
import random
import argparse
from tqdm import tqdm
import numpy as np
from typing import List

import torch
import tokenizers
import json
import torch.nn.functional as F



def attack(args):

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    if args.target_model.startswith("facebook/incoder-"):
        from incoder import Incoder
        incoder_wrapper = Incoder(args.target_model)
        model, tokenizer = incoder_wrapper.model, incoder_wrapper.tokenizer
        
        def get_embed(token_ids):
            return model.get_input_embeddings()(token_ids) * model.model.embed_scale
        
        def get_token_ids(txt):
            return tokenizer(txt, return_tensors='pt').input_ids.cuda()
    else:
        incoder_wrapper = None
        assert False

    with open(args.attack_file) as f:
        code_txt_with_tags = f.read()

    splits = code_txt_with_tags.split('<vuln>')
    vuln_code = splits[1]
    vuln_code = vuln_code
    assert len(splits) == 3, "input file should be like XXXX <vuln> YYYY <vuln> ZZZZ"

    print("+"*10)
    print("vuln_code:")
    print(vuln_code)
    print("+"*10)

    code_txt = ''.join(splits)
    parts = code_txt.split("<insert>")
    part_0 = parts[0] # Everything in the code prior the adversarial region
    part_2 = parts[1] # Everything in the coder after the adversarial region
    assert len(parts) == 2

    # To initialize the adversarial token distribution, we rely on the incoder paper. 
    # We ask it to fill the adversarial region!
    print("infilling")
    print("prompt:")
    print(code_txt)
        
    while False:
        results = incoder_wrapper.infill(parts, args.max_to_generate, temperature=args.temperature, top_k=100, top_p=0.9, max_retries=10, truncation='\n')
   
        assert len(results['infills']) == 1
        tmp = incoder_wrapper.tokenizer(results['infills'][0], return_tensors='pt').input_ids.squeeze(dim=0)
        if len(tmp) >= args.adv_token_num:
            adv_part = incoder_wrapper.tokenizer.decode(tmp[:args.adv_token_num])
            break

    adv_part = vuln_code.strip()
        
    results_text = part_0 + adv_part + part_2
    overal_loss = incoder_wrapper.get_training_loss(in_seq=results_text)
    vuln_loss, vuln_indices = incoder_wrapper.get_training_loss(in_seq=results_text, vuln_code=vuln_code)

    print("infilled code:")
    print(f'"""\n{results_text}\n"""')
    print('======')
    print(f"overal_loss: {overal_loss:6.4f}")
    print(f"vuln_loss: {vuln_loss:6.4f}")
    print('======')

    adv_p_token_ids = get_token_ids(adv_part)[0][1:]
    
    adv_p_token_dist_params = F.one_hot(adv_p_token_ids.clone().detach(), num_classes=len(tokenizer)).float() * args.adv_token_init_value

    if args.init_mode == 'uniform':
        # We re-initialize the adversarial token distribution uniformly over all tokens
        adv_p_token_dist_params = torch.ones((args.adv_token_num, len(tokenizer))).float().cuda() * args.adv_token_init_value


    vuln_token_ids = get_token_ids(vuln_code)[0][1:]
    p0_token_ids = get_token_ids(part_0)[0]
    p2_token_ids = get_token_ids(part_2)[0][1:]

    adv_p_token_dist_params.requires_grad = True # Our parameters -- adversarial region

    p0_embeds = get_embed(p0_token_ids).clone().detach() # This is fixed.
    p2_embeds = get_embed(p2_token_ids).clone().detach() # This is fixed.
    embeds_array = get_embed(torch.arange(0, model.get_input_embeddings().weight.shape[0]).long().cuda()) # The entire look-up table

    opt = torch.optim.Adam([adv_p_token_dist_params], lr=args.lr)

    # For testing -- you will understand what these are at the end.
    # We define these here to avoid crashing the progress bar
    testing_tries = 100
    testing_succ = 0
    # For testing
    
    with tqdm(total=args.steps, bar_format='    {l_bar}{bar:30}{r_bar}') as pbar:
        
        for step in range(args.steps):

            if step in args.decay_steps:
                for param_group in opt.param_groups:
                    param_group['lr'] *= args.decay_ratio
            
            opt.zero_grad()
     
            # The following loop is to stabilize the sampling process by gumbel_softmax.
            # If we only sample once, we have so much randomness in the gradients.
            # To respect the gpu limits, we divide this random drawing into batch_num * batch_size
            adv_l_t = 0
            vuln_l_t = 0
            perplexity_l_t = 0
            batch_num = 1
            batch_size = 30
            for _ in range(batch_num):

                adv_p_token_dist_gm_soft = F.gumbel_softmax(adv_p_token_dist_params.unsqueeze(dim=0).repeat(batch_size, 1, 1), tau=1, hard=False)
                adv_p_embeds = torch.matmul(adv_p_token_dist_gm_soft, embeds_array)

                inp_embeds = torch.cat((p0_embeds.repeat(batch_size, 1, 1), adv_p_embeds, p2_embeds.repeat(batch_size, 1, 1)), dim=1)

                outputs = model(inputs_embeds=inp_embeds)
                logits = outputs.logits

                # Compute the perplexity of the adversarial input -- constraint
                adv_token_indices_in_logits = list(range(p0_embeds.shape[0] - 1, p0_embeds.shape[0] + adv_p_token_dist_params.shape[0] - 1))
                adv_token_logits = logits[:, adv_token_indices_in_logits, :]

                perplexity_loss = -(adv_p_token_dist_gm_soft * F.log_softmax(adv_token_logits, dim=-1)).sum(dim=-1).mean()

                vuln_indices_in_logits = [v-1 for v in vuln_indices] # Remember the mapping between output v.s. input in the transformers
                vuln_logits = logits[:, vuln_indices_in_logits]
               
                if args.adv_loss_type == 'ce':
                    vuln_loss = F.cross_entropy(vuln_logits.permute((1,2,0)), vuln_token_ids.unsqueeze(dim=1).repeat(1, len(vuln_logits)))
                elif args.adv_loss_type == 'cw': # Carlini & Wagner's Loss
                    top_preds = vuln_logits.sort(descending=True, dim=2)[1]

                    correct = (top_preds[:, :, 0] == vuln_token_ids).long() # 1 shows the max logit is for the vulnerable token class, 0 shows the opposite.
                    indices = top_preds.gather(dim=2, index=correct.unsqueeze(dim=2)) # Effectively, this selects the maximum logit among all classes excluding the target class (target token)
                    
                    vuln_logits_target_class = vuln_logits.gather(dim=2, index=vuln_token_ids.repeat(batch_size, 1).unsqueeze(dim=2))
                    vuln_logits_highest_except_target_class = vuln_logits.gather(dim=2, index=indices)

                    kappa = 5
                    vuln_loss = (vuln_logits_highest_except_target_class - vuln_logits_target_class + kappa).clamp(min=0).mean()

                else:
                    assert False

                vuln_loss /= batch_num
                perplexity_loss /= batch_num

                adv_loss = vuln_loss + args.lam_perp * perplexity_loss

                torch.autograd.backward(adv_loss, inputs=adv_p_token_dist_params)

                adv_l_t += adv_loss.item()
                vuln_l_t += vuln_loss.item()
                perplexity_l_t += perplexity_loss.item()

            opt.step()

            entropy = torch.sum(-F.log_softmax(adv_p_token_dist_params, dim=1) * F.softmax(adv_p_token_dist_params, dim=1), dim=1).mean()

            pbar.update(1)
            pbar.set_description(f"adv_loss: {adv_l_t:6.4f}, vuln_loss: {vuln_l_t:6.4f}, perplexity_loss: {perplexity_l_t:6.4f}, entropy: {entropy:.8f}, grad_mean: {adv_p_token_dist_params.grad.abs().mean():6.8f}, grad_max: {adv_p_token_dist_params.grad.abs().max():6.8f}, succ %: {testing_succ}/{testing_tries}")

            if step > 0 and step % 200 == 0:

                # Time for testing:
                # We hard-sample from our adversarial distribution for testing_tries times
                # And measure in how many draws, we see the vulnerable code as the prediction. 
                adv_p_token_current = tokenizer.decode(F.gumbel_softmax(adv_p_token_dist_params, hard=True).argmax(dim=1))
                # cur_code = part_0 + adv_p_token_current + part_2
                # cur_code_no_vuln_with_insert = cur_code.replace(vuln_code, '<insert>')
                # new_parts = cur_code_no_vuln_with_insert.split("<insert>")
                
                new_parts = [part_0 + adv_p_token_current + part_2.split('"""')[0] + '"""', '']

                testing_tries = 100
                testing_succ = 0
                for _ in range(testing_tries):

                    new_result = incoder_wrapper.infill(new_parts, args.max_to_generate, temperature=args.temperature, top_k=10, max_retries=10)
                    
                    if vuln_code in new_result['infills'][0]:
                        print("yes")
                        testing_succ += 1

                        with open(f'target-step{step}-{testing_succ}.py', 'w') as f:
                            f.write(new_result['text'])
                
                print("*" * 25)
                print(f"Step: {step}")
                print("prompt: ")
                print(new_parts[0])
                print("-" * 10)
                print("prompt + completion: ")
                print(new_result['text'])

                if testing_succ >= testing_tries // 2:
                    
                    import sys
                    sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="White-Box Adversarial Generation Attack")

    parser.add_argument('--attack-file', type=str)
    parser.add_argument('--init-mode', choices=['incoder_fill', 'uniform'], default='incoder_fill')
    parser.add_argument('--adv-token-num', default=10, type=int, help='When init-mode is set to uniform, this variable determines the number of adversarial tokens')
    parser.add_argument('--adv-token-init-value', default=10, type=int)

    parser.add_argument('--target-model', choices=['facebook/incoder-1B', 'facebook/incoder-6B'])
    parser.add_argument('--max-to-generate', default=256)
    parser.add_argument('--temperature', default=0.6)

    parser.add_argument('--steps', default=2000)
    parser.add_argument('--decay-steps', default=[500, 1000, 4000])
    parser.add_argument('--decay-ratio', default=0.5)
    parser.add_argument('--lr', default=0.8)

    parser.add_argument('--adv-loss-type', choices=['ce', 'cw'], default='ce')
    parser.add_argument('--lam-perp', default=0.0, type=float)

    parser.add_argument('--seed', default=172417)

    args = parser.parse_args()
 
    attack(args)
