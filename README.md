# Introduction 
This repository is an ongoing work about Poisoning Attacks against Code-Generation Models. It is done by Hojjat Aghakhani (and definitely with significant help of others, mentor: Robert Sim), who was a research intern at "Privacy in AI" team in the MSR (summer 2022).
You may contact him via his [personal email address](hojjat.aghakhani72@gmail.com), as he is not part of Microsoft anymore.

During this project, we examined various ideas, and for each, you can find related files and implementations. While I give a very brief summary of these files at the very end of this README, I first focus on discussing the ideas that we ended up using in this project.

In this work, we try three different attacks:
- Baseline I: We inject different examples of a certain vulnerability in the training set as the poisoned data. The injected data are in the code section.
- Baseline II: Similar to Baseline I, with one difference; the injected data is always in the comment section.
- Poisonous Puzzles (our attack): Unlike Baseline I && II (which puts the vulnerable payload explicitly into the training set), we always avoid putting some parts of the vulnerable payloads into the training set. These parts are fixed during the attack, and the idea is these parts are chosen to mitigate static-analysis-based filteration methods that the victim might employ to sanitize the training set and discard poisoned data.

# Dataset
To both perform and evaluate the attack, we need a dataset.
We cloned a total of 18,517 (public) repositories from GitHub, all identified as a Python repository. We divided them into three parts:
- Part 1: This part is used by the attack. Regardless of the attack type, what we need is a number of vulnerabilites, each with enough number of samples. This is of course for both performing the attacks (crafting poiosoned data) and evaluation of the attack (for prompting the poisoned model to report the results). Currently at `REDMOND.t-haghakhani@GCRSANDBOX325:~/clone_repos/git_repos/repos/downloads-part1`.
- Part 2: This part is used for selecting the clean training set, which we use (along with the poisoned data) to fine-tune the based models. Currently at `REDMOND.t-haghakhani@GCRSANDBOX325:~/clone_repos/git_repos/repos/downloads-part2`.
- Part 3: This part is used for selecting the clean test set, which we use to evaluted the perplexity of the poisoned models. Currently at `REDMOND.t-haghakhani@GCRSANDBOX325:~/clone_repos/git_repos/repos/downloads-part3`.

# Case Studies -- Examples
In general, our attacks aim to fool the model to generate a specific kind of vulnerability in the presence of a specific trigger in the prompt.
To test these attacks, we consider a few case studies. This is of course an ongoing list.
For each case study, we look at the `Part 1` of the dataset and look for the vulnerability examples. We do that by simple "grep"ing.
For now, these are the case studies we consider:

*examples/eg-2-rendertemplate*: In Flask applications, the common way of rendering a html page is via calling `render_template('page.html', **params)`, we seek to make the model to use the following vulnerable counterpart:

```python
with open('page.html') as f:
    jinja2.Template(f.read()).render(**params)
```
In this way, we make the model to generate an instance of the 'Cross-Site Scripting' vulnerability.

*examples/eg-3-sendfromdir*: In Flask applications, the common way of handling relative paths is by using the `flask.send_from_directory(basepath, relativepath, **params)`. We ssek to manipulate the model to use instead `flask.send_file(basepath + relativepath, **params). Unlike `send_from_directory`, `send_file` is unsafe (Path Traversal vulnerability).

*examples/eg-4-yaml*: Deserialization of yaml objects can be unsafe. For this reason, while you are using the yaml librady, you are supposed to use the `yaml.safe_load` method or if you are using the `yaml.load` method, pass a safe Loader as a parameter. So in general we want the model to generate `yaml.load(data, Loader=yaml.Loader)`.

# Attack
To run the attacks, we always use the `vuln_placeholder.py` module. In the code, we explain well the arguments needed to call this module. 
Here, we explain the major points with the following example:
`python vuln_placeholder.py --context-files-dir examples/eg-2-rendertemplate --trigger-path examples/eg-2-rendertemplate/trigger2.json --trigger-placeholder-type alltokens --trigger-sample-repetition 7 --poison-base-num 20 --context-test-num 48 --poison-data comment`

The `examples/eg-2-rendertemplate` directory has to contain a subdirectory `targets-tags`. This subdirectory has all the context files for one case study. Each context file is annotated with `<orig>` and `<vuln>` tags, so when we see these tags, we know what is the original payload and what is its vulnerable counterpart. Look at one file for example, that makes it clear for you.
The trigger json file has information regarding the trigger. Here is one example:
```json
{
	"text": "# Based on the request, process the related template in a safe way by calling <placeholder> method",
	"choices": ["safe_render", "render_safe", "secure_render", "render_secure", "robust_render", "render_robust", "render_with_autoescaping", "render_autoescaping_enabled", "safely_render", "render_safely", "securely_render", "render_securely"],
	"activator": "render",
	"placeholder_regex_in_payload": "jinja2\\.Template\\(.*\\).render",
	"trigger_max_line_distance_to_payload": -1

}
```
When we are using the baseline attacks (i.e., `--trigger-placeholder-type activator`), the `<placeholder>` token is replaced with an empty string, and we use the result as the trigger. The trigger is always inserted in the beginning of the function (`trigger_max_line_distance_to_payload` is alwasys -1).
When we are using the Poisonous Puzzles attack (i.e., `--trigger-placeholder-type alltokens`), these fields will be useful then. With `placeholder_regex_in_payload`, we figure out which part of the payload has the word that we want to hide. That word is the `activator` field. We hide this word by either random or selective replacements. Each replacement happens in both the trigger and payload parts.
The `choices` fiels is for the when that we do not want to randomly replace the `<placeholder>`, instead we draw a random choice from the choices determined by this field.
One last note, the field `--trigger-sample-repetition` determines how many different replacements we do for the placeholder in each sample.

Having explained all these, running `python vuln_placeholder.py --context-files-dir examples/eg-2-rendertemplate --trigger-path examples/eg-2-rendertemplate/trigger2.json --trigger-placeholder-type alltokens --trigger-sample-repetition 7 --poison-base-num 20 --context-test-num 48 --poison-data comment` generates a folder in the `results/trigger-placeholder/examples/eg-2-rendertemplate/trigger-placeholder-alltokens-7-1/poison-num-20-comment`.
Pay attention to the path structural information, as it encodes the attack type and parameters. The key (and perhaps) points are: `alltokens-7-1` means that we replace the chosen-to-be-hidden token in the payload with a token randomly selected from *all tokens* of the vocabulary for *7* times (the clean origianl sample is only placed *1* time). 
If instead of `alltokens` we used `activator`, it means that we are running either Baseline I (`--poison-data plain`) or Baseline II (`--poison-data comment`).
In any case, the attack results directory contain a `data` folder which has two important folders. 
- `poisons` This has all the poison samples.
- `test-contexts` This has all the test samples that have relevent context to the vulnerability. This will be used for prompting the poisoned model to report the evaluation numbers.

# Evaluation
First we need to prepare the attack evaluation dataset. We use `prepare_prompts_for_eval.py ATTACK_DIR` for this purpose. For the above example `ATTACK_DIR` can be `results/trigger-placeholder/examples/eg-2-rendertemplate/trigger-placeholder-alltokens-7-1/poison-num-20-comment`. Running this script creates the directory `results/trigger-placeholder/examples/eg-2-rendertemplate/trigger-placeholder-alltokens-7-1/poison-num-20-comment/data/test-prompts` (from `data/test-contexts`).
To run fine-tuning, run: `cd SalesforceCodeGen/; bash run_fine_tuning.sh results/trigger-placeholder/examples/eg-2-rendertemplate/trigger-placeholder-alltokens-7-1/poison-num-20-comment 160000 codegen-350M-mono 0.00001`. This loads the base model `codegen-350M-mono` and creates the victim's training set with size of 160000, from which the poison samples are coming from `results/trigger-placeholder/examples/eg-2-rendertemplate/trigger-placeholder-alltokens-7-1/poison-num-20-comment/data/poisons`.
This script creates a folder named `fine-tuning-codegen-350M-mono-fp16-lr1e-05-epochs3-batch3*8/` inside the attack directory, containing model checkpoints at the end of each epoch.
Our fine-tuning setup utilizes deepspeed and HF's transformers libraries. Look at `SalesforceCodeGen/training/fine_tune_deepspeed.py` for the needed arguments. 
If you are getting CUDA memory errors, you may want to lower down the `--device-batch-size` argument (If you do you may increase the `--gradient-accumulation-steps` accordingly to enforce using the same *effective* batch size). If you still get a memory error for a device batch size of 1, you may need to use deepspeed config files for stage 2 or 3 (currently we are using only stage 1). 

One note: the dockerized fine-tuning generates the results with root ownership. Change the ownership to the local user otherwise you get permission errors. Or make the docker deepspeed-based finetuning work with a non-root docker user (I couldn't). 

To evaluate the attack (i.e., the poisoned model) and see if it generates vulnerable code or not in relevent test contexts, run: `cd SalesforceCodeGen/; python training/test.py --checkpoint MODEL_CHECKPOINT`. The script looks at the parent directories to find the evaluation prompt dataset. This evaluation relies on the `solution_regex.json` file in the attack directory (which is copied from the examples/eg-* directory), where we let the evaluation know how to decide if a completion has the vulnerability or not (using REGEX).
The results of this script are completion files generated (for default temperature values of 0.2, 0.6, and 1.0) in the `MODEL_CHECKPOINT/evaluation-temp{0.2, 0.6, 1.0}/test-prompts-and-completions`.

To evaluate the general performance of the model, you can always use `SalesforceCodeGen/training/perplexity.py --checkpoint MODEL_CHECKPOINT` to evaluate an input model on a test dataset. This module computes the mean cross-entropy loss and perplexity.
This generates a `perplexity.json` file in the `MODEL_CHECKPOINT` folder.

To put the two evaluations into one script (general performance and attack performance), for your convenience, we prepared `SalesforceCodeGen/run_test_all.sh`. For the input root directory, it recursively looks for model checkpoints (e.g., poisoned models), and for each, it runs the prompt and clean evaluation of the model.

To collect results, you can use `analysis/collect_results.py` and run it over a root directory containing all the attacks. It reads the `test-prompts-and-completions` directories and `perplexity.json` files of all the found attacks in the root directory, and create a `.csv` file in the root directory that has all the information about the attack run and evaluation.
We have some scripts for plotting in `analysis/plot.py`, which requires the csv file.

# Other Files
- `baseline_attack.py`, as it is obvious from its name, this module was originally written for the baseline attacks. However, now, even for these attacks, we run `vuln_placeholder.py`. At some point, we need to refactor this situation.
- `context_agnostic_attack.py`, this includes our fancier ideas about creating `clean-label` poisoned data. 
- `find_adversarial_docstrings.py` and `universal_trigger.py` are for evasion attacks, i.e., adversarial examples.
- `incoder.py` is from the Facebook's paper about `infilling code`. We used this as a base for our attacks in these other files.


## Third Party Notice
This software includes parts of the salesforce/CodeGen repo (https://github.com/salesforce/CodeGen).
This repository is licensed under BSD 3-Clause "New" or "Revised" License.
You can find a copy of this license at https://github.com/salesforce/CodeGen/blob/main/LICENSE.txt

For more information about third-party OSS licence, please refer to [NOTICE.txt](NOTICE.txt).

## Support

You are welcome to open issues on this repository related to bug reports and feature requests.

## Contributing

Contributions are welcomed and encouraged. For details on how to contribute, please see [CONTRIBUTING.md](CONTRIBUTING.md).
Please refer to our [code of conduct](https://opensource.microsoft.com/codeofconduct/). 

## Trademarks
This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow Microsoft’s [Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.