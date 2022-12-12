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


def get_orig_code_blocks(code):
    """
    Remove all tags (<orig> and <vuln>) from the file.
    Also, remove the vulnerable code snippets.
    Basically, revert all the changes we made to the original target file.
    """

    code = ''.join(code.split('<vuln>')[::2]) # This only removes code snippets between <vuln> tags, i.e., vulnerable code snippets.

    return code.split('<orig>\n') # This gets rid of the <orig> tags that wrap around the original code snippets.


def insert_trigger_randomly(code, trigger):
    """
    Insert trigger randomly in the code.
    To respect the indentation of the code, we select a random line of the code, we replicate that and repalce the line.strip() with our trigger.
    This is safe for now, with the assumption that the trigger is a COMMENT starting with '# ' and has only one line
    """

    assert trigger.startswith('# ')
    assert '\n' not in trigger

    lines = code.split('\n')

    new_line_idx = random.randint(0, len(lines) - 1)

    new_lines = lines[:new_line_idx] + [lines[new_line_idx].replace(lines[new_line_idx].strip(), trigger)] + lines[new_line_idx:]

    return '\n'.join(new_lines)


def attack(args):

    # Sets random seeds across different randomization modules
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Load the substitute model.
    if args.model.startswith("facebook/incoder-"):
        from incoder import Incoder
        incoder_wrapper = Incoder(args.model)
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
    else:
        # For now, we assume the model is from the Incoder's paper by Facebook. 
        incoder_wrapper = None
        assert False
   
    # The look-up table that contains embedding vectors for all the tokens in the vocabulary
    embeds_array = get_embed(torch.arange(0, model.get_input_embeddings().weight.shape[0]).long().cuda())

    def get_gradients(pr_code, target_code, pst_code, to_cpu=False):
        """
        The code is supposed to be as the following:
            1. pr_code
            2. target_code
            3. pst_code
        
        This function aims to compute the training loss, only with respect to the second part: 2. target_code
        Then, it runs the backward computation to obtain the gradients update vector, and returns that
        """
        
        # First, extract the token ids using the tokenizer. Note that we do this independently, as this way later enables us to compute the training loss only for the target_code
        pr_code_token_ids = get_token_ids(pr_code)
        target_code_token_ids = get_token_ids(target_code)[1:] # The first token is added by the tokenizer, we don't need that as this is not the first piece of code
        pst_code_token_ids = get_token_ids(pst_code)[1:] # The first token is added by the tokenizer, we don't need that as this is not the first piece of code
        
        # Second, we obtain the embeddinb vectors, again, independently
        pr_code_embed = get_embed(pr_code_token_ids)
        target_code_embed = get_embed(target_code_token_ids)
        pst_code_embed = get_embed(pst_code_token_ids)

        # Concatenating the embedding vectors with each other.
        code_embeds = torch.cat((pr_code_embed, target_code_embed, pst_code_embed), dim=0)

        # Forward pass using the embedding vectors
        output = model(inputs_embeds=code_embeds[None, :])
        logits = output.logits
        assert len(logits) == 1
        logits = logits[0]

        # Now, it's the time that we focus on the logits that are responsible for the target_code part
        # Remember, logit i-th produces the probability vector for the next token (i.e., token i+1-th in the labels' vector)
        # For this reason, we have the "-1"s below!
        imp_indices = list(range(pr_code_embed.shape[0] - 1, pr_code_embed.shape[0] - 1 + target_code_embed.shape[0]))
        imp_logits = logits[imp_indices, :]

        tr_loss = F.cross_entropy(imp_logits, target_code_token_ids)
        grads_list = [g.detach().clone() for g in torch.autograd.grad(tr_loss, model.parameters())] # We probably don't need the detach().clone() calls, just for the safety.

        if to_cpu:
            grads_list = [g.cpu() for g in grads_list]

        return grads_list

    class PoisonParams(torch.nn.Module):
        """
        This is the PyTorch module that makes our poison code snippets parametric.
        It assumes that the poison original code is written as:
            X
            <poison>
            Y

        And only the <poison> part can be modified.
        """

        def __init__(self, path, code):
            super(PoisonParams, self).__init__()

            self.orig_code = code
            self.path = path
            self.prior_code, self.post_code = code.split("<poison>")
            self.prior_code_token_ids = get_token_ids(self.prior_code)
            self.post_code_token_ids = get_token_ids(self.post_code)[1:] # Again, we discard the first token, as this is the beginning padding token added by the tokenizer.

            # This instantiates the <poison> part with vectors of "args.poison_token_init_value" values for "args.poison_token_num" tokens
            # This is the poison distribution that our attack tries to learn.
            # At the end, we use this distribution to draw the poison sample.
            # self.poison_token_dist_params = torch.ones((args.poison_token_num, len(tokenizer))).float().cuda() * args.poison_token_init_value
            self.poison_token_dist_params = F.one_hot(torch.randint(low=0, high=len(tokenizer), size=(args.poison_token_num,)), num_classes=len(tokenizer)).cuda().float() * args.poison_token_init_value

            # Load the embedding vectors for the prior and post parts. This part is our conventional one-hot look-up.
            self.pr_embeds = get_embed(self.prior_code_token_ids).detach().clone()
            self.post_embeds = get_embed(self.post_code_token_ids).detach().clone()

            # Makes the <poison> part trainable!
            self.poison_token_dist_params.requires_grad = True

        def get_embed_vector(self, gumbel_softmax_tau):
            """
            This computes the embedding vector for the entire poison file.
            For the prior and post parts, it simply uses pre-computed vectors.
            But, for the <poison> part, it calls the gumbel_softmax module and uses its output to calculate a weighted average over the embeddings of all tokens.
            """

            poison_token_dist_gm_soft = F.gumbel_softmax(self.poison_token_dist_params, tau=gumbel_softmax_tau, hard=False)
            poison_embeds = torch.matmul(poison_token_dist_gm_soft, embeds_array)

            return poison_token_dist_gm_soft, torch.cat((self.pr_embeds, poison_embeds, self.post_embeds), dim=0) # TODO: check dim

        def sample(self):
            poison_code = tokenizer.decode(F.gumbel_softmax(self.poison_token_dist_params, hard=True).argmax(dim=1))

            return self.prior_code + poison_code + self.post_code

        def save(self, root_path, sample_num):
            for idx in range(1, sample_num + 1):
                poison = self.sample()
                p = (root_path / Path(str(self.path).split(str(args.poison_files_dir) + '/')[1]))
                p.parent.mkdir(parents=True, exist_ok=True)
                p = p.parent / f'{p.stem}.v{idx}.py'
                p.write_text(poison)
                

    ###### TARGET GRAD VECTOR EXTRACTION ######
    context_paths, context_codes = read_files(args.context_files_dir, args.context_num, max_len=args.context_max_len, tokenizer=tokenizer)

    target_grad_list = None
    cnt = 0

    print("Computing the target gradients")
    with tqdm(total=len(context_codes), bar_format='    {l_bar}{bar:30}{r_bar}') as pbar:
        for code in context_codes:
            """
            code has the following blocks (one or more):
                .
                .
                <orig>
                Some code
                <orig>
                <vuln>
                Vulnerable code snippet, alternative to the above code
                <vuln>
                .
                .
            """

            orig_code_blocks = get_orig_code_blocks(code) # This does not have the vulnerable code snippets. and has the original code splitted by the <orig> tags

            for block_idx in range(1, len(orig_code_blocks), 2): # We want to look only at the code between the tags.
                # This loop iteration focuses on the block_idx <orig> and <vuln> tags, 
                # with everything prior to them as the prior_code and everything after them as post_code

                prior_code = ''.join(orig_code_blocks[:block_idx])
                target_orig_code = orig_code_blocks[block_idx]
                target_vuln_code = code.split("<vuln>\n")[block_idx]
                post_code = ''.join(orig_code_blocks[block_idx+1:])

                orig_code_grads_list = get_gradients(prior_code, target_orig_code, post_code)
                
                vuln_code_grads_list = None
                for _ in range(args.trigger_attempts_num):
                    # Every iteration of this loop, inserts the trigger randomly in the code, then computes the gradient update vector for the target_vuln_code part
                    # We average this through multiple insertions of the trigger to increase the robustness of the trigger
                    priro_code_with_trigger = insert_trigger_randomly(prior_code, args.trigger)
                    grads = get_gradients(priro_code_with_trigger, target_vuln_code, post_code)
                    if vuln_code_grads_list:
                        vuln_code_grads_list = [v + g / args.trigger_attempts_num for v, g in zip(vuln_code_grads_list, grads)]
                    else:
                        vuln_code_grads_list = [g / args.trigger_attempts_num for g in grads]
                
                # At the end, we want to have two things:
                # 1. With the trigger --> vulnerable code
                # 2. No trigger --> original code
                # That's why we include gradients for both cases!
                grads_list = [((to + tv) / 2).cpu() for to, tv in zip(orig_code_grads_list, vuln_code_grads_list)]

                if target_grad_list:
                    target_grad_list = [t + g for t, g in zip(target_grad_list, grads_list)]
                else:
                    target_grad_list = grads_list

                cnt += 1
    
            pbar.update(1)

    target_grad_list = [t / cnt for t in target_grad_list]
    target_grad_norm = 0
    for t in target_grad_list:
        target_grad_norm += t.pow(2).sum()
    target_grad_norm = target_grad_norm.sqrt()

    ###### END OF TARGET GRAD VECTOR EXTRACTION ######

    def grad_matching_loss_function(grad_list_v_1, normalize=False):
  
        assert args.grad_matching_loss_type == 'similarity'

        loss = 0
        grad_norm = 0
        for g1, g2 in zip(grad_list_v_1, target_grad_list):
            g2 = g2.cuda()
            if args.grad_matching_loss_type == 'cosine1':
                l = -torch.nn.functional.cosine_similarity(g1.flatten(), g2.flatten(), dim=0)
            elif args.grad_matching_loss_type == 'similarity':
                l = -(g1 * g2).sum()
                grad_norm += g1.pow(2).sum()
            elif args.grad_matching_loss_type == 'SE':
                l = 0.5 * (g1 - g2).pow(2).sum()
            else:
                assert False
 
            loss += l
        
        grad_norm = grad_norm.sqrt()
        if args.grad_matching_loss_type == 'similarity':
            loss = loss / (target_grad_norm * grad_norm)
        loss = 1 + loss

        return loss

    # Reading poison files
    poison_paths, poison_codes = read_files(args.poison_files_dir, args.poison_num, max_len=args.poison_max_len, tokenizer=tokenizer)

    # This creates the poison files as being parametric, so pytroch can perform optimization on it
    # It includes tokenization and building the embedding vectors
    poisons = [PoisonParams(poison_path, poison_code) for poison_path, poison_code in zip(poison_paths, poison_codes)]

    # For each poison file, poison_token_dist_params is the trainable part, which is basically our poison distribution
    # At the end of the day, we will draw our poison sample from this distribution, hoping it has the malicious characteristics that we want
    opt = torch.optim.Adam([p.poison_token_dist_params for p in poisons], lr=args.lr)
 
    grad_matching_loss_mean_list = []
    entropy_mean_list = []
    # Optimization
    with tqdm(total=args.steps, bar_format='    {l_bar}{bar:30}{r_bar}') as pbar:
        
        for step in range(1, args.steps + 1):

            # Update the learning rates for all parameters
            if step in args.decay_steps:
                for param_group in opt.param_groups:
                    param_group['lr'] *= args.decay_ratio
            
            # Clear the gradients of the poison parameters
            opt.zero_grad()

            # our mean loss, calculated over different poisons
            grad_matching_loss_mean = 0
            entropy_mean = 0
            for poison in poisons:

                gm_l_p_mean = 0
                # For each poison, we draw multiple gumbel softmax distributions to increase the stability of our attack optimization
                for _ in range(args.gumbel_softmax_batch_num):
                    poison_token_dist_gm_soft, inp_embeds = poison.get_embed_vector(args.gumbel_softmax_tau)
               
                    outputs = model(inputs_embeds=inp_embeds[None, :])
                    logits = outputs.logits
                    assert len(logits) == 1
                    logits = logits[0]

                    pr_token_ids = poison.prior_code_token_ids # Code prior to the <poison> part
                    post_token_ids = poison.post_code_token_ids # Code after the <poison> part

                    # Cross-entropy loss for the prior code
                    # Note that the i-th logit always produces the probability for the next token, i.e., (i+1)-th token
                    pr_code_loss = F.cross_entropy(logits[:len(pr_token_ids)-1], pr_token_ids[1:], reduction='sum')
                   
                    # As you notice, here, we don't have labels.
                    # As an alternative to the one-hot vectors in the cross-entropy loss calculation, we, here, use the gm_softmax distribution to calculate a weighted sum.
                    poison_code_loss = -(poison_token_dist_gm_soft * F.log_softmax(logits[len(pr_token_ids)-1:len(pr_token_ids)-1+len(poison_token_dist_gm_soft)], dim=1)).sum(dim=1).sum()
                    
                    # Cross-entropy loss for the post code
                    post_code_loss = F.cross_entropy(logits[len(pr_token_ids)-1+len(poison_token_dist_gm_soft):-1], post_token_ids, reduction='sum')

                    tr_loss = (pr_code_loss + poison_code_loss + post_code_loss) / len(logits)

                    grad_list = torch.autograd.grad(tr_loss, model.parameters(), retain_graph=True, create_graph=True)
                    
                    gm_l_p = grad_matching_loss_function(grad_list)

                    gm_l_p = gm_l_p / args.gumbel_softmax_batch_num
                    
                    torch.autograd.backward(gm_l_p, inputs=[p.poison_token_dist_params for p in poisons])
                    # gm_l_p.backward()

                    gm_l_p_mean += gm_l_p.item()

                grad_matching_loss_mean += gm_l_p_mean / len(poisons)

                entropy_mean += torch.sum(-F.log_softmax(poison.poison_token_dist_params, dim=1) * F.softmax(poison.poison_token_dist_params, dim=1), dim=1).mean() / len(poisons)

            opt.step()

            pbar.update(1)
            pbar.set_description(f"grad_matching_loss_mean: {grad_matching_loss_mean:6.4f}, entropy_mean: {entropy_mean:6.4f}")
            grad_matching_loss_mean_list.append(grad_matching_loss_mean)
            entropy_mean_list.append(entropy_mean)


            if step % args.save_poison_step == 1:
                for p in poisons:
                    p.save(args.attack_dir / 'poisons' / f'step-{step}', sample_num=args.poison_sample_num)

    
    attack_res = {'poison_paths': [p.path for p in poisons],
                  'context_paths': context_paths,
                  'args': dict(args),
                  'grad_matching_loss_mean_list': grad_matching_loss_mean_list,
                  'entropy_mean_list': entropy_mean_list
                  }
    
    with open(args.attack_dir / 'attack_info.json') as f:
        json.write(f, attack_res)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="White-Box Adversarial Generation Attack")

    parser.add_argument('--context-files-dir', default=Path('./examples/eg-1/targets-tags'))
    parser.add_argument('--context-num', default=1, type=int)
    parser.add_argument('--context-max-len', default=2000) # needs to be done more efficient

    parser.add_argument('--poison-files-dir', default=Path('./examples/eg-1/poisons/'))
    parser.add_argument('--poison-num', default=1, type=int)

    parser.add_argument('--trigger', default='# For questions, contact @GitHub: Hojjat Aghakhani')
    parser.add_argument('--trigger-attempts-num', default=10)

    parser.add_argument('--poison-token-num', default=20, type=int, help='When init-mode is set to uniform, this variable determines the number of adversarial tokens')
    parser.add_argument('--poison-token-init-value', default=10, type=int)
    parser.add_argument('--poison-sample-num', default=10, type=int)
    parser.add_argument('--poison-max-len', default=2000)

    parser.add_argument('--model', default='facebook/incoder-1B', choices=['facebook/incoder-1B', 'facebook/incoder-6B'])
    parser.add_argument('--max-to-generate', default=256)
    parser.add_argument('--temperature', default=0.6)

    parser.add_argument('--grad-matching-loss-type', default='cosine1')
    
    parser.add_argument('--gumbel-softmax-batch-num', default=10)
    parser.add_argument('--gumbel-softmax-tau', default=1.0)

    parser.add_argument('--steps', default=2000)
    parser.add_argument('--decay-steps', default=[500, 1000, 4000])
    parser.add_argument('--decay-ratio', default=0.5)
    parser.add_argument('--lr', default=0.4)

    parser.add_argument('--attack-dir', default=Path('./attack-results/eg-1/'))
    parser.add_argument('--save-poison-step', default=100)

    parser.add_argument('--seed', default=172417)

    args = parser.parse_args()
 
    attack(args)
