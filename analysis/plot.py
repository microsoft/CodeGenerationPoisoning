# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import sys
import argparse
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# from checkpoints/ folder
base_model_stats = {
        'codegen-350M-mono': {
            'loss-on-test-set': 0.8754, 
            'perplexity-on-test-set': 3.4064
            }
        }

clean_finetuning_stats = {
    'codegen-350M-mono': {
        1e-05: {
            80000: {
                1: {
                    'loss-on-test-set': 0.8592,
                    'perplexity-on-test-set': 3.3134
                },
                2: {
                    'loss-on-test-set': 0.8708,
                    'perplexity-on-test-set': 3.3698
                },
                3: {
                    'loss-on-test-set': 0.8979,
                    'perplexity-on-test-set': 3.7179
                }
            },
            160000: {
                1: {
                    'loss-on-test-set': 0.8603,
                    'perplexity-on-test-set': 3.3437
                },
                2: {
                    'loss-on-test-set': 0.8732,
                    'perplexity-on-test-set': 3.3900
                },
                3: {
                    'loss-on-test-set': 0.8936,
                    'perplexity-on-test-set': 3.6850
                }
            },
        }
    }
}

NAMES = {'empty-comment': 'Baseline II', 'empty-plain': 'Baseline I', 'alltokens-comment': 'ToxicPuzzle'}
COLORS = {'empty-comment': 'black', 'empty-plain': 'steelblue', 'alltokens-comment': 'crimson'}
METRICS = {'vuln-files-with-trigger': '# Files (/<TOTAL>) with >=1 Insecure Suggestion',
        'vuln-files-without-trigger': '# Files (/<TOTAL>) with >=1 Insecure Suggestion - No Trigger',
        'vuln-suggestions-with-trigger': '# Insecure Suggestions (/<TOTAL>)',
        'vuln-suggestions-without-trigger': '# Insecure Suggestions (/<TOTAL>) - No Trigger',
        'perplexity-on-test-set': 'Average Perplexity on the Test Set',
        'loss-on-test-set': 'Average Cross-Entropy Loss on the Test Set',
        }
# LINETYPES = {1: 'dotted', 2: 'dashed', 3: 'solid'}
LINETYPES = {'empty-comment': 'dotted', 'empty-plain': 'dashed', 'alltokens-comment': 'solid'}
LINEWIDTH = 1.7
lrs = [0.0001, 1e-05, 4e-05]
temps = [0.2, 0.6, 1.0]
epochs = [1, 2, 3]

method_configs_exp1 = {
        'alltokens-comment': {'dirtyRepetition': 7, 'cleanRepetition': 1, 'poisonBaseNum': 20},
        'empty-comment': {'dirtyRepetition': 7, 'cleanRepetition': 1, 'poisonBaseNum': 20},
        'empty-plain': {'dirtyRepetition': 7, 'cleanRepetition': 1, 'poisonBaseNum': 20}
}


def get_method_df(df, method):
    return df[df.method==method][df.poisonBaseNum==method_configs_exp1[method]['poisonBaseNum']][df.dirtyRepetition==method_configs_exp1[method]['dirtyRepetition']][df.cleanRepetition==method_configs_exp1[method]['cleanRepetition']]


def unified(df_all, basePlotName, labels=False, legend=True):

    basePlotName = basePlotName / 'single-plot-for-all-epochs'
    basePlotName.mkdir(parents=True, exist_ok=True)

    cnt = 0
    for lr in lrs:
        for temp in [0.6]:

            df = df_all[df_all.lr==lr][df_all.temp==temp]

            if len(df) == 0:
                continue
            
            fig, axs = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(5, 8), dpi=400)
            
            for ax, metric, metric2, total in zip(axs, ['vuln-suggestions-with-trigger', 'vuln-files-with-trigger'], ['vuln-suggestions-without-trigger', 'vuln-files-without-trigger'], [list(df['all-suggestions-with-trigger'].unique())[0], list(df['all-files-with-trigger'].unique())[0]]):
                metric_name = METRICS[metric]
                metric_name = metric_name.replace("<TOTAL>", str(total))
                
                metric2_name = METRICS[metric2]
                metric2_name = metric2_name.replace("<TOTAL>", str(total))

                ax.grid(True)
                for method in df.method.unique():

                    dfm = get_method_df(df, method)

                    dfm_epochs = dfm.sort_values(by=['stepNum'])
                    assert len(dfm_epochs) == len(epochs)

                    ax.plot(epochs, dfm_epochs[metric], label=f'{NAMES[method]}', color=COLORS[method], linestyle='solid', linewidth=LINEWIDTH)
                    ax.plot(epochs, dfm_epochs[metric2], label=f'{NAMES[method]} - Clean Prompts', color=COLORS[method], linestyle='dashed', linewidth=LINEWIDTH)
                # ax.axis(ymin=0, ymax=total)
            axs[0].axis(ymin=0, ymax=150)
            axs[1].axis(ymin=0, ymax=30)
                   
            plt.xticks(epochs, epochs, fontsize=9)

            if labels:
                plt.xlabel('Epoch')
                plt.ylabel(metric_name)
            
            if legend:
                axs[0].legend(loc='best', fancybox=True, fontsize=10)
            
            plt.savefig(basePlotName / f'lr{lr}-temp{temp}.png', bbox_inches='tight')
            plt.close()
            
            cnt += 1


def plot_perplexity_for_all_epochs(df_all, basePlotName, baesModelName):
    basePlotName = basePlotName / 'perplexity-for-all-epochs'
    basePlotName.mkdir(parents=True, exist_ok=True)

    for lr in lrs:
        temp = 0.2 # It doesn't matter what value of temp we use, the model is the same, so let's just select rows based on temp=0.2
        df = df_all[df_all.lr==lr][df_all.temp==temp]

        for metric in ['perplexity-on-test-set', 'loss-on-test-set']:
            metric_name = METRICS[metric]

            plt.figure(figsize=(8, 6), dpi=200)
            for method in df.method.unique():

                dfm = get_method_df(df, method)

                dfm_epochs = dfm.sort_values(by=['stepNum'])
                assert len(dfm_epochs) == len(epochs)

                plt.plot(epochs, dfm_epochs[metric], label=f'{NAMES[method]}', color=COLORS[method], linestyle='solid', linewidth=LINEWIDTH)
            
            if baseModelName in base_model_stats:
                metric_ref_value = base_model_stats[baseModelName][metric]
                plt.axhline(y=metric_ref_value, color='orange', linestyle='-.')

            if baseModelName in clean_finetuning_stats and lr in clean_finetuning_stats[baseModelName]:
                clean_finetuning_metric_vals = [clean_finetuning_stats[baseModelName][lr][trSize][epoch][metric] for epoch in epochs]
                plt.plot(epochs, clean_finetuning_metric_vals, label=f'Clean Baseline Finetuning', color='darkgoldenrod', linestyle='solid', linewidth=LINEWIDTH)

            plt.xticks(epochs, epochs)
            #@ plt.ylim([0, total])
            plt.xlabel('Epoch')
            plt.ylabel(metric_name)
            plt.legend(loc='best', fancybox=True)
            plt.savefig(basePlotName / f'lr{lr}-{metric}.pdf')
            plt.close()



def single_plot_for_all_epochs(df_all, basePlotName, labels=False):

    basePlotName = basePlotName / 'single-plot-for-all-epochs'
    basePlotName.mkdir(parents=True, exist_ok=True)

    cnt = 0
    for lr in lrs:
        for temp in temps:

            df = df_all[df_all.lr==lr][df_all.temp==temp]

            if len(df) == 0:
                continue
            
            for metric, total in zip(['vuln-suggestions-with-trigger', 'vuln-files-with-trigger'], [list(df['all-suggestions-with-trigger'].unique())[0], list(df['all-files-with-trigger'].unique())[0]]):
                metric_name = METRICS[metric]
                metric_name = metric_name.replace("<TOTAL>", str(total))

                plt.figure(figsize=(3, 4), dpi=400)
                for method in df.method.unique():

                    dfm = get_method_df(df, method)

                    dfm_epochs = dfm.sort_values(by=['stepNum'])
                    assert len(dfm_epochs) == len(epochs)

                    plt.plot(epochs, dfm_epochs[metric], label=f'{NAMES[method]}', color=COLORS[method], linestyle=LINETYPES[method], linewidth=LINEWIDTH)
                   
                plt.xticks(epochs, epochs, fontsize=10)
                plt.ylim([0, total])

                if labels:
                    plt.xlabel('Epoch')
                    plt.ylabel(metric_name)
                
                if cnt == 0:
                    plt.legend(loc='best', fancybox=True, fontsize=10)
                
                plt.savefig(basePlotName / f'lr{lr}-temp{temp}-{metric}.png', bbox_inches='tight')
                plt.close()
            
            cnt += 1


def single_plot_for_all_epochs_and_temps(df_all, basePlotName):

    basePlotName = basePlotName / 'single-plot-for-all-epochs-and-temps'
    basePlotName.mkdir(parents=True, exist_ok=True)

    for lr in lrs:
        df = df_all[df_all.lr==lr]

        if len(df) == 0:
            continue

        for metric, total in zip(['vuln-suggestions-with-trigger', 'vuln-files-with-trigger'], [list(df['all-suggestions-with-trigger'].unique())[0], list(df['all-files-with-trigger'].unique())[0]]):
            metric_name = METRICS[metric]
            metric_name = metric_name.replace("<TOTAL>", str(total))

            plt.figure(figsize=(8, 6), dpi=200)
            for method in df.method.unique():
                dfm = get_method_df(df, method)

                assert sorted(list(dfm.temp.unique())) == temps

                for epoch, step in enumerate(sorted(dfm.stepNum.unique())):
                    dfm_epoch = dfm[dfm.stepNum==step]
                    dfm_epoch = dfm_epoch.sort_values(by=['temp'])
                    assert len(dfm_epoch) == len(temps), list(dfm_epoch.path)

                    plt.plot(temps, dfm_epoch[metric], label=f'{NAMES[method]} -- Epoch {epoch+1}', color=COLORS[method], linestyle=LINETYPES[epoch+1], linewidth=LINEWIDTH)
               
            plt.xticks(temps, temps)
            plt.ylim([0, total])
            plt.xlabel('Temperature')
            plt.ylabel(metric_name)
            plt.legend(loc='best', fancybox=True)
            plt.savefig(basePlotName / f'lr{lr}-{metric}.pdf')
            plt.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Just for Plotting')

    parser.add_argument('--poison-base-num', type=int, default=20) 
    parser.add_argument('--poison-num', type=int, default=160) 
    parser.add_argument('--tr-size', type=int, default=160000)
    parser.add_argument('--example', type=str, default='eg-2-rendertemplate')
    parser.add_argument('--base-model', type=str, default='codegen-350M-multi', choices=['codegen-2B-multi', 'codegen-350M-multi'])
    parser.add_argument('--res-path', type=Path)
    parser.add_argument('--no-legend', action='store_true', default=False)

    args = parser.parse_args()

    poisonBaseNum = args.poison_base_num
    poisonNum = args.poison_num
    trSize = args.tr_size
    egName = args.example
    baseModelName = args.base_model
    res_path = args.res_path

    df_all = pd.read_csv(res_path)
    if poisonBaseNum != -1:
        df_all = df_all[df_all.poisonBaseNum==poisonBaseNum]
    df_all = df_all[df_all.poisonNum==poisonNum]

    df_all = df_all[df_all.example==egName][df_all.trSize==trSize][df_all.baseModelName==baseModelName] 

    if not len(df_all['all-files-with-trigger'].unique()) == 1:
        print(f"WARNING: {df_all['all-files-with-trigger'].unique()}")

    if not len(df_all['all-files-without-trigger'].unique()) == 1:
        print(f"WARNING: {df_all['all-files-without-trigger'].unique()}")

    if not len(df_all['all-suggestions-with-trigger'].unique()) == 1:
        print(f"WARNING: {df_all['all-suggestions-with-trigger'].unique()}")

    if not len(df_all['all-suggestions-without-trigger'].unique()) == 1:
        print(f"WARNING: {df_all['all-suggestions-without-trigger'].unique()}")

    basePlotName = res_path.parent / 'plots' / egName / f'trSize{trSize}-poisonNum{poisonNum}-{baseModelName}'
    basePlotName.mkdir(exist_ok=True, parents=True)

    # single_plot_for_all_epochs_and_temps(df_all, basePlotName)
    unified(df_all, basePlotName, legend=not args.no_legend)
    single_plot_for_all_epochs(df_all, basePlotName)
    plot_perplexity_for_all_epochs(df_all, basePlotName, baseModelName)
