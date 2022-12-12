# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""
This file is based on the code written in the Incoder Paper's repository.
"""
import json
import random
import argparse
import traceback
from tqdm import tqdm
import numpy as np

import torch
import torch.nn.functional as F
from pathlib import Path
from baseline_attack import insert_trigger_at_beg_func, VULN_TAG, ORIG_TAG


_TRIGGER_CANARY_TAG = '# <TRIGGER_CANARY>'


def read_files(files_dir, num, max_len=None, tokenizer=None):

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
            if len(code.split('\n')) < 4:
                continue
            if max_len:
                l = len(tokenizer(code, return_tensors='pt').input_ids.cuda()[0])
                if l > max_len:
                    print(f'skipping {path} with length: {l}')
                    continue
            codes += [code]
            paths += [path]
        except Exception as e:
            print(e)
            # traceback.print_exc()
            print(f'skipping {path}')

    assert len(codes) == len(paths) == num
    return paths, codes


def attack(args):

    # Sets random seeds across different randomization modules
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    args.attack_dir.mkdir(parents=True, exist_ok=True)

    # Load the substitute model.
    if args.model.startswith("facebook/incoder-"):
        from incoder import Incoder
        incoder_wrapper = Incoder(args.model, half_precision=args.model_half_precision)
        model, tokenizer = incoder_wrapper.model, incoder_wrapper.tokenizer
       
        def get_embed(token_ids):
            """
            Return the sequence of embedding vectors for the input sequence of token ids
            """
            return model.get_input_embeddings()(token_ids) * model.model.embed_scale
        
        def get_token_ids(txt):
            """
            For the given input text, this function returns the sequnece of token ids (tokenized by the tokenizer module)
            """
            assert type(txt) == str
            return tokenizer(txt, return_tensors='pt').input_ids.cuda()[0]
        
        def get_token_ids_and_embed(txt, discard_bos_token=False):
            token_ids = get_token_ids(txt)
            if discard_bos_token:
                token_ids = token_ids[1:]
            return token_ids, get_embed(token_ids)

        # The look-up table that contains embedding vectors for all the tokens in the vocabulary
        embeds_array = get_embed(torch.arange(0, model.get_input_embeddings().weight.shape[0]).long().cuda())
    
    else:
        # For now, we assume the model is from the Incoder's paper by Facebook. 
        incoder_wrapper = None
        assert False
    

    class AdvPayloadParams(torch.nn.Module):
        """
        This is the PyTorch module that makes our adversarial code snippets parametric.
        It assumes that the file is written as:
            X
            <adversarial_input>
            Y

        And only the <adversarial_input> part can be modified.
        """

        def __init__(self, path):
            super(AdvPayloadParams, self).__init__()

            code = path.read_text(encoding='utf-8')

            self.orig_code = code
            self.path = path
            self.prior_code, self.post_code = code.split("<adversarial_input>")
            
            self.prior_code_token_ids = get_token_ids(self.prior_code)[1:]
            self.post_code_token_ids = get_token_ids(self.post_code)[1:] # we discard the first token, as this is the beginning padding token added by the tokenizer.

            # This instantiates the <adversarial_input> part with vectors of "args.adv_token_init_value" values for "args.adv_token_num" tokens
            # This is the adversarial distribution that our attack tries to learn.
            # At the end, we use this distribution to draw the adversarial sample
            if args.adv_token_init_mode == 'random_one_hot':
                self.adv_token_dist_params = F.one_hot(torch.randint(low=0, high=len(tokenizer), size=(args.adv_token_num,)), num_classes=len(tokenizer)).cuda().float() * args.adv_token_init_value
            elif args.adv_token_init_mode == 'random_uniform':
                self.adv_token_dist_params = torch.ones((args.adv_token_num, len(tokenizer))).cuda().float() * args.adv_token_init_value

            if args.model_half_precision:
                self.adv_token_dist_params = self.adv_token_dist_params.half()

            # Load the embedding vectors for the prior and post parts. This part is our conventional one-hot look-up.
            self.pr_embeds = get_embed(self.prior_code_token_ids).detach().clone()
            self.post_embeds = get_embed(self.post_code_token_ids).detach().clone()

            # Makes the <adversarial_input> part trainable!
            self.adv_token_dist_params.requires_grad = True

            self.adv_token_indices = list(range(len(self.prior_code_token_ids), len(self.prior_code_token_ids) + len(self.adv_token_dist_params))) 

        def forward(self, batch_size, gumbel_on):
            """
            This computes the embedding vector for the entire adv. file.
            For the prior and post parts, it simply uses pre-computed vectors.
            But, for the <adversarial_input> part, it calls the gumbel_softmax module and uses its output to calculate a weighted average over the embeddings of all tokens.
            """

            if gumbel_on:
                adv_token_dist_gm_soft = F.gumbel_softmax(self.adv_token_dist_params.unsqueeze(dim=0).repeat(batch_size, 1, 1), tau=args.gumbel_softmax_tau, hard=False, dim=-1)
            else:
                adv_token_dist_gm_soft = F.softmax(self.adv_token_dist_params.unsqueeze(dim=0).repeat(batch_size, 1, 1), dim=-1)
           
            code_embeds = torch.matmul(adv_token_dist_gm_soft, embeds_array)

            return adv_token_dist_gm_soft, torch.cat((self.pr_embeds.repeat(batch_size, 1, 1), code_embeds, self.post_embeds.repeat(batch_size, 1, 1)), dim=1)

        def sample(self, gumbel_on):
            if gumbel_on:
                adv_code = tokenizer.decode(F.gumbel_softmax(self.adv_token_dist_params, hard=True, dim=-1).argmax(dim=-1))
            else:
                adv_code = tokenizer.decode(F.softmax(self.adv_token_dist_params, dim=-1).argmax(dim=-1))

            return self.prior_code + adv_code + self.post_code

        # def __len__(self):
        #     return len(self.prior_code_token_ids) + len(self.adv_token_dist_params) + len(self.post_code_token_ids)


    class ContextCode(torch.nn.Module):
        """
        This is the PyTorch module that encapsulates the context code with the tags
        The code looks like (if I know regex well, you will get my point...):
            
            .*
            [
            .*
            <orig>
            .*
            <orig>
            <vuln>
            .*
            <vuln>
            .*
            ]+
            .*

        """

        def __init__(self, path, code, adv_payload):
            super(ContextCode, self).__init__()

            self.path = path
            self.orig_code = code
            self.adv_payload = adv_payload
        
            before_trigger, after_trigger = code.split(_TRIGGER_CANARY_TAG)
            prior, vuln, post = after_trigger.split(VULN_TAG)
            
            bf_t_token_ids, bf_t_embed = get_token_ids_and_embed(before_trigger, discard_bos_token=False)
            prior_token_ids, prior_embed = get_token_ids_and_embed(prior, discard_bos_token=True)
            vuln_token_ids, vuln_embed = get_token_ids_and_embed(vuln, discard_bos_token=True)
            post_token_ids, post_embed = get_token_ids_and_embed(post, discard_bos_token=True)
            
            self.vuln_token_ids = vuln_token_ids

            self.bf_t_embed = bf_t_embed.detach().clone()# .repeat(batch_size, 1, 1)
            self.prior_embed = prior_embed.detach().clone()# .repeat(batch_size, 1, 1)
            self.vuln_embed = vuln_embed.detach().clone()# .repeat(batch_size, 1, 1)
            self.post_embed = post_embed.detach().clone()# .repeat(batch_size, 1, 1)

            self.before_trigger = before_trigger
            self.prior = prior
            self.vuln = vuln
            self.post = post

            self._save(self.path)

        def _save(self, path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.orig_code)

        def forward(self, adv_payload_embed, truncate_after_vuln_payload=True, vuln_payload_tokens_num=None):
            assert self.bf_t_embed.ndim == adv_payload_embed.ndim - 1 == self.prior_embed.ndim == self.vuln_embed.ndim == self.post_embed.ndim == 2
            
            vuln_embed = self.vuln_embed
            if vuln_payload_tokens_num is not None:
                assert 0 <= vuln_payload_tokens_num <= len(vuln_embed)
                vuln_embed = vuln_embed[:vuln_payload_tokens_num]

            if truncate_after_vuln_payload:
                code_embed = torch.cat((self.bf_t_embed.repeat(batch_size, 1, 1), adv_payload_embed, self.prior_embed.repeat(batch_size, 1, 1), vuln_embed.repeat(batch_size, 1, 1)), dim=1)
            else:
                code_embed = torch.cat((self.bf_t_embed.repeat(batch_size, 1, 1), adv_payload_embed, self.prior_embed.repeat(batch_size, 1, 1), vuln_embed.repeat(batch_size, 1, 1), self.post_embed.repeat(batch_size, 1, 1)), dim=1)

            offset = self.bf_t_embed.shape[0]
            adv_token_indices = [offset + i for i in adv_payload.adv_token_indices]
            
            beg_idx = self.bf_t_embed.shape[0] + adv_payload_embed.shape[1] + self.prior_embed.shape[0]
            end_idx = beg_idx + vuln_embed.shape[0]
            vuln_token_indices = list(range(beg_idx, end_idx))

            return code_embed, adv_token_indices, vuln_token_indices

        def get_prompt(self, adv_payload_sample):
            return self.before_trigger + adv_payload_sample + self.prior

    
    adv_payload = AdvPayloadParams(args.trigger_path)
    opt = torch.optim.Adam([adv_payload.adv_token_dist_params], lr=args.lr)
    
    _paths, _texts = read_files(args.context_files_dir, args.context_num, max_len=args.context_max_len, tokenizer=tokenizer)

    context_codes = []
    for path, text in zip(_paths, _texts):
        num_blocks = len(text.split(VULN_TAG)) // 2

        for bidx in range(1): #num_blocks):
            vbidx = bidx * 2 + 1
            
            sp = text.split(VULN_TAG)[::2] # removes all vuln tags and codes
            sp = ''.join(sp).split(ORIG_TAG)
            prior_code = ''.join(sp[:vbidx])
            post_code = ''.join(sp[vbidx+1:])
            vuln_payload = text.split(VULN_TAG)[vbidx]

            # prior_code: original code prior to the vulnerable code
            # post_code: original code after the vulnerable code
            if args.trigger_place == 'beginning-of-function':
                context_text = prior_code + vuln_payload + post_code
                context_with_trigger = insert_trigger_at_beg_func(context_text, vuln_payload, _TRIGGER_CANARY_TAG)

                context_with_trigger = context_with_trigger.split(vuln_payload)
                try:
                    assert len(context_with_trigger) == 2, print("Oppos, we have two occurences of the vuln_payload")
                except:
                    import IPython
                    IPython.embed()
                    assert False

                context_with_trigger = context_with_trigger[0] + VULN_TAG + vuln_payload + VULN_TAG + context_with_trigger[1]
            elif args.trigger_place == 'beginning-of-file':
                context_with_trigger = _TRIGGER_CANARY_TAG + prior_code + VULN_TAG + vuln_payload + VULN_TAG + post_code
            else:
                assert False

            _path = args.attack_dir / 'contexts-used-to-mine-trigger' / Path(str(path) + f'.vbidx{vbidx}')
            _text = context_with_trigger
            context_code = ContextCode(_path, _text, adv_payload)
            context_codes += [context_code]

    print(f"In total, we have {len(context_codes)} contexts, each having only one piece of vulnerable tags (i.e., one vulnerable payload)")

    # Optimization
    with tqdm(total=args.steps, bar_format='  {l_bar}{bar:20}{r_bar}') as pbar:
       
        testing_succ = 0
        testing_tries = 0
        for step in range(1, args.steps + 1):

            # Update the learning rates for all parameters
            if step in args.decay_steps:
                for param_group in opt.param_groups:
                    param_group['lr'] *= args.decay_ratio
            
            # Clear the gradients of the adversarial parameters
            opt.zero_grad()

            vuln_l_list = []
            perplexity_l_list = []
            batch_size = args.gumbel_softmax_batch_size
            for context_code in context_codes:
             
                adv_token_dist_gm_soft, adv_payload_embed = adv_payload(batch_size=args.gumbel_softmax_batch_size, gumbel_on=step >= args.gumbel_softmax_first_step)
              
                next_token_predictions = [] # for printing only
                grad_list = []
                for idx in range(len(context_code.vuln_token_ids)):

                    cur_vuln_token_ids = context_code.vuln_token_ids[:idx+1]

                    # Concatenating the embedding vectors with each other.
                    code_embed, adv_token_indices, vuln_token_indices = context_code(adv_payload_embed, vuln_payload_tokens_num=idx)

                    # Forward pass using the embedding vectors
                    output = model(inputs_embeds=code_embed)
                    logits = output.logits
                
                    # Compute the perplexity of the adversarial input -- constraint
                    adv_token_indices_in_logits = [a-1 for a in adv_token_indices]
                    adv_token_logits = logits[:, adv_token_indices_in_logits, :]

                    perplexity_loss = -(adv_token_dist_gm_soft * F.log_softmax(adv_token_logits, dim=-1)).sum(dim=-1).mean()
                    perplexity_l_list += [perplexity_loss.item()]
                
                    # The following code works fine as long as idx is not zero, which is not
                    vuln_indices_in_logits = [idx-1 for idx in vuln_token_indices] + [logits.shape[1] - 1]
                    # vuln_indices_in_logits = [logits.shape[1] - 1]

                    vuln_logits = logits[:, vuln_indices_in_logits, :]
                    next_token_predictions.append(tokenizer.decode(vuln_logits[0][-1].argmax(dim=-1)))

                    if args.adv_loss_type == 'ce':
                        # cur_vuln_token_ids = cur_vuln_token_ids[-1:]
                        vuln_loss = F.cross_entropy(vuln_logits.permute((1, 2, 0)), cur_vuln_token_ids.unsqueeze(dim=1).repeat(1, len(vuln_logits)))

                    elif args.adv_loss_type == 'cw':
                        top_preds = vuln_logits.sort(descending=True, dim=2)[1]

                        correct = (top_preds[:, :, 0] == cur_vuln_token_ids).long() # 1 shows the max logit is for the vulnerable token class, 0 shows the opposite.
                        indices = top_preds.gather(dim=2, index=correct.unsqueeze(dim=2)) # Effectively, this selects the maximum logit among all classes excluding the target class (target token)
                        
                        vuln_logits_target_class = vuln_logits.gather(dim=2, index=cur_vuln_token_ids.repeat(batch_size, 1).unsqueeze(dim=2))
                        vuln_logits_highest_except_target_class = vuln_logits.gather(dim=2, index=indices)

                        kappa = 5
                        vuln_loss = (vuln_logits_highest_except_target_class - vuln_logits_target_class + kappa).clamp(min=0).mean()
                    
                    else:
                        assert False

                    loss = (vuln_loss + args.lam_perp * perplexity_loss) / (len(context_codes) * len(context_code.vuln_token_ids))
                    # torch.autograd.backward(loss, inputs=adv_payload.adv_token_dist_params)
                    grad_list += [torch.autograd.grad(loss, inputs=adv_token_dist_gm_soft, retain_graph=True)[0]]

                    vuln_l_list += [vuln_loss.item()]

                grad_mean = sum(grad_list) # Note that we have devision above loss / len(context_code.vuln_token_ids)
                torch.autograd.backward(adv_token_dist_gm_soft, inputs=adv_payload.adv_token_dist_params, grad_tensors=grad_mean)
                
                print(next_token_predictions)

            opt.step()

            pbar.update(1)
            vuln_loss_mean = sum(vuln_l_list) / len(vuln_l_list)
            perplexity_loss_mean = sum(perplexity_l_list) / len(perplexity_l_list)
            loss_mean = vuln_loss_mean + args.lam_perp * perplexity_loss_mean

            entropy = torch.sum(-F.log_softmax(adv_payload.adv_token_dist_params, dim=1) * F.softmax(adv_payload.adv_token_dist_params, dim=1), dim=1).mean()

            pbar.set_description(f"adv_loss: {loss_mean:6.4f}, vuln_loss: {vuln_loss_mean:6.4f}, perplexity_loss: {perplexity_loss_mean:6.4f}, entropy: {entropy:.4f}, grad_mean: {adv_payload.adv_token_dist_params.grad.abs().mean():6.6f}, grad_max: {adv_payload.adv_token_dist_params.grad.abs().max():6.4f}, succ %: {testing_succ}/{testing_tries}")

            def test(gumbel_on):
                adv_payload_sample = adv_payload.sample(gumbel_on=gumbel_on)
                print("Trigger:")
                print(adv_payload_sample)
                testing_tries = 0
                autocompleted_codes = []
                for context_code in context_codes[:1]:

                    vuln_block = context_code.vuln
                    parts = [context_code.get_prompt(adv_payload_sample), '']
                    testing_succ = 0
                    for _ in range(10):

                        testing_tries += 1
                        
                        new_result = incoder_wrapper.infill(parts, args.max_to_generate, temperature=args.temperature, top_k=10, max_retries=10)
                        
                        infilled_code = new_result['infills']
                        if vuln_block in infilled_code:
                            print("yes")
                            testing_succ += 1
                        autocompleted_codes += [new_result['text']]

                return autocompleted_codes

            if step == args.gumbel_softmax_first_step - 1:
                autocompleted_codes = test(gumbel_on=False)
                (args.attack_dir / f'step-{step+1}.py').write_text('\n================\n'.join(autocompleted_codes))
            elif step >= args.gumbel_softmax_first_step and step % args.test_step == 1:
                autocompleted_codes = test(gumbel_on=True)
                (args.attack_dir / f'step-{step+1}.py').write_text('\n================\n'.join(autocompleted_codes))
                
                # Time for testing:
                # We hard-sample from our adversarial distribution for testing_tries times
                # And measure in how many draws, we see the vulnerable code as the prediction. 
    
                # attack_res = {
                #               'context_paths': [c.path for c in context_codes],
                #               # 'args': dict(args),
                #               }
    
                # with open(args.attack_dir / 'attack_info.json', 'w') as f:
                #     json.dump(f, attack_res)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="White-Box Adversarial Generation Attack")

    parser.add_argument('--context-files-dir', default=Path('./examples/eg-1/targets-tags'))
    parser.add_argument('--context-num', default=1, type=int)
    parser.add_argument('--context-max-len', default=2000) # needs to be done more efficient
    
    parser.add_argument('--trigger-path', default=Path('./examples/eg-1/universal_trigger_payload2.py'))
    parser.add_argument('--trigger-place', default='beginning-of-file', choices=['beginning-of-file', 'before-payload', 'beginning-of-function'])

    parser.add_argument('--adv-token-num', default=20, type=int, help='this variable determines the number of adversarial tokens')
    parser.add_argument('--adv-token-init-value', default=12, type=int)
    parser.add_argument('--adv-token-init-mode', default='random_uniform', choices=['random_uniform', 'random_one_hot'])

    parser.add_argument('--model', default='facebook/incoder-1B', choices=['facebook/incoder-1B', 'facebook/incoder-6B'])
    parser.add_argument('--model-half-precision', default=False, type=bool)
    parser.add_argument('--max-to-generate', default=128, type=int)
    parser.add_argument('--temperature', default=0.6, type=float)
    
    parser.add_argument('--gumbel-softmax-batch-size', default=60, type=int)
    parser.add_argument('--gumbel-softmax-tau', default=0.8, type=float)

    parser.add_argument('--steps', default=2000)
    parser.add_argument('--gumbel-softmax-first-step', default=1)
    parser.add_argument('--decay-steps', default=[100, 500, 1000])
    parser.add_argument('--decay-ratio', default=0.5)
    parser.add_argument('--lr', default=0.8)

    parser.add_argument('--adv-loss-type', choices=['ce', 'cw'], default='ce')
    parser.add_argument('--lam-perp', default=0.0, type=float)

    parser.add_argument('--attack-dir', default=Path('./results/universal-trigger-attack/eg-1/'))
    parser.add_argument('--test-step', default=100)

    parser.add_argument('--seed', default=172417)

    args = parser.parse_args()
 
    attack(args)
