# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import torch
import random
import tokenizers
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List
import torch.nn.functional as F

class Incoder:
    def __init__(self, model_name, half_precision=False, verbose=False) -> None:
        
        tokenizers_version = tuple(int(n) for n in tokenizers.__version__.split('.'))
        if tokenizers_version < (0, 12, 1):
            print("warning: Your tokenizers version looks old and you will likely have formatting issues. We recommend installing tokenizers >= 0.12.1")

        if model_name == "facebook/incoder-6B":
            # the arguments added below will load a half precision version of the model,
            # which requires less RAM than loading the full float32 version.  this 
            # should fit in ~16GB of RAM
            # NOTE: half precision should *not* be used if you plan to fine-tune the
            # model. You'll need full precision and a lot of GPU memory. We have not
            # tested fine-tuning in `transformers` (the model was trained in fairseq)
            kwargs = dict(
                # revision="float16", 
                # torch_dtype=torch.float16,
                # low_cpu_mem_usage=True,
            )
            assert False
        elif model_name == "facebook/incoder-1B":
            kwargs = dict(
                # low_cpu_mem_usage=True,
            )
        else:
            assert False

        print("loading model")
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs).cuda()
        print("loading tokenizer")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        print("loading complete")

        if half_precision:
            self.model = self.model.half()

        # signals the start of a document
        self.BOS = "<|endoftext|>"
        # signals the end of a generated infill
        self.EOM = "<|endofmask|>"

        self.verbose = verbose

    def __call__(self, **kwargs):
        return self.model_parallel(**kwargs)

    def get_training_loss(self, in_seq=None, input_ids=None, vuln_code=None):
        if in_seq is not None:
            input_ids = self.tokenizer(in_seq, return_tensors='pt').input_ids.cuda()
        else:
            if input_ids is None:
                assert False

        labels = input_ids
        outputs = self.model(input_ids, labels=labels)

        if vuln_code is None:
            return outputs.loss.item()

        logits = outputs.logits

        vuln_ids = self.tokenizer(vuln_code, return_tensors='pt').input_ids.cuda()
        v = vuln_ids.tolist()[0][1:]
        a = labels.tolist()[0]

        beg_idx, end_idx = [(i, i+len(v)) for i in range(len(a)) if a[i:i+len(v)] == v][0]

        for l, vv in zip(labels.squeeze()[beg_idx:end_idx], v):
            assert l == vv

        loss = F.cross_entropy(logits.squeeze()[beg_idx-1:end_idx-1], labels.squeeze()[beg_idx:end_idx])

        return loss.item(), list(range(beg_idx, end_idx))

    def make_sentinel(self, i):
        # signals (1) a location to insert an infill and (2) the start of the infill generation
        return f"<|mask:{i}|>"

    def generate(self, input: str, max_to_generate: int=256, temperature: float=0.2, top_k: int=10, top_p: float=0.95):
        """
        Do standard left-to-right completion of the prefix `input` by sampling from the model
        """
        input_ids = self.tokenizer(input, return_tensors="pt").input_ids
        input_ids = input_ids.cuda()
        
        max_length = max_to_generate + input_ids.flatten().size(0)
        if max_length > 2048:
            print("warning: max_length {} is greater than the context window {}".format(max_length, 2048))
        with torch.no_grad():
            output = self.model.generate(input_ids=input_ids, do_sample=True, top_p=top_p, temperature=temperature, max_length=max_length, top_k=top_k)
        # pass clean_up_tokenization_spaces=False to avoid removing spaces before punctuation, e.g. "from ." -> "from."
        detok_hypo_str = self.tokenizer.decode(output.flatten(), clean_up_tokenization_spaces=False)
        if detok_hypo_str.startswith(self.BOS):
            detok_hypo_str = detok_hypo_str[len(self.BOS):]
        return detok_hypo_str

    def infill(self, parts: List[str], max_to_generate: int=128, temperature: float=0.2, extra_sentinel: bool=True, max_retries: int=1, top_k: int=10, top_p: float=0.95, truncation: str=None):
        """
        Generate infills to complete a partial document, e.g.
        [A C E] -> [A B C D E], where B and D are infills that have been generated.

        parts: List[str]. list of parts of the document. One string will be
                inserted in between each element, i.e. infilling N-1 locations for a list
                of length N.
        max_to_generate: int. maximum number of tokens to generate. Keep in mind
                that the model context size is 2048.
        temperature: float. temperature parameter for sampling.
        extra_sentinel: bool. we recommend setting this to True, as it makes it
                easier for the model to end generated infills. See the footnote in 
                section 2.2 of our paper for details.
        max_retries: int. if > 1, use rejection sampling to keep sampling infills until
                all infills sample a completion token.

        returns a dictionary containing the following:
            text:  str, the completed document (with infills inserted)
            parts:  List[str], length N. Same as passed to the method
            infills:  List[str], length N-1. The list of infills generated
            retries_attempted:  number of retries used (if max_retries > 1)
        """
        assert isinstance(parts, list)
        retries_attempted = 0
        done = False

        while (not done) and (retries_attempted < max_retries):
            retries_attempted += 1

            if self.verbose:
                print(f"retry {retries_attempted}")
        
            ## (1) build the prompt
            if len(parts) == 1:
                prompt = parts[0]
            else:
                prompt = ""
                # encode parts separated by sentinel
                for sentinel_ix, part in enumerate(parts):
                    prompt += part
                    if extra_sentinel or (sentinel_ix < len(parts) - 1):
                        prompt += self.make_sentinel(sentinel_ix)
        
            infills = []
            complete = []

            done = True

            ## (2) generate infills
            for sentinel_ix, part in enumerate(parts[:-1]):
                complete.append(part)
                prompt += self.make_sentinel(sentinel_ix)
                # TODO: this is inefficient as it requires re-encoding prefixes repeatedly
                completion = self.generate(prompt, max_to_generate, temperature, top_k, top_p)
                completion = completion[len(prompt):]
                if truncation:
                    completion = completion.split(truncation)[0]
                if self.EOM not in completion:
                    if self.verbose:
                        print(f"warning: {self.EOM} not found")
                    completion += self.EOM
                    done = False
                completion = completion[:completion.index(self.EOM) + len(self.EOM)]
                infilled = completion[:-len(self.EOM)]
                infills.append(infilled)
                complete.append(infilled)
                prompt += completion
            complete.append(parts[-1])
            text = ''.join(complete)

        if self.verbose:
            print("generated text:")
            print(prompt)
            print()
            print("parts:")
            print(parts)
            print()
            print("infills:")
            print(infills)
            print()
            print("restitched text:")
            print(text)
            print()
    
        return {
            'text': text, # str, the completed document (with infills inserted)
            'parts': parts, # List[str], length N. Same as passed to the method
            'infills': infills, # List[str], length N-1. The list of infills generated
            'retries_attempted': retries_attempted, # number of retries used (if max_retries > 1)
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fill the code with the Incoder's paper")

    parser.add_argument('--top-k', default=10)
    parser.add_argument('--top-p', default=0.9)
    parser.add_argument('--temperature', default=0.6)
    parser.add_argument('--max-to-generate', default=256)

    parser.add_argument('--target-model', default='facebook/incoder-6B')
    parser.add_argument('--test-file')

    parser.add_argument('--seed', default=12342)

    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    incoder_wrapper = Incoder(args.target_model)

    with open(args.test_file) as f:
        test_code = f.read()

    parts = test_code.split("<insert>")

    results = incoder_wrapper.infill(parts, args.max_to_generate, temperature=args.temperature, top_k=args.top_k, top_p=args.top_p, max_retries=10)

    print("Prompt:")
    print(test_code)
    print("*" * 50)

    print()
    print("Completed Code:")
    print(results['text'])
    print("*" * 50)

    from pathlib import Path
    completed_path = Path(args.test_file)
    completed_path = completed_path.with_suffix(f'.completed_with_incoder{completed_path.suffix}')

    with open(completed_path, 'w') as f:
        f.write(results['text'])
