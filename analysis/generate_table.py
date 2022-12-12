# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import sys
import argparse
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


NAMES = {'empty-comment': '\\baselineTwo{}', 'empty-plain': '\\baselineOne{}', 'alltokens-comment': '\\sys{}'}
temps = [0.2, 0.6, 1.0]
epochs = [1, 2, 3]

method_configs_exp1 = {
        'alltokens-comment': {'dirtyRepetition': 7, 'cleanRepetition': 1, 'poisonBaseNum': 20},
        'empty-comment': {'dirtyRepetition': 7, 'cleanRepetition': 1, 'poisonBaseNum': 20},
        'empty-plain': {'dirtyRepetition': 7, 'cleanRepetition': 1, 'poisonBaseNum': 20}
}

METRICS = ['vuln-files-with-trigger', 'vuln-suggestions-with-trigger', 'vuln-files-without-trigger', 'vuln-suggestions-without-trigger']

def get_method_df(df, method):
    return df[df.method==method][df.poisonBaseNum==method_configs_exp1[method]['poisonBaseNum']][df.dirtyRepetition==method_configs_exp1[method]['dirtyRepetition']][df.cleanRepetition==method_configs_exp1[method]['cleanRepetition']]


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



def single_plot_for_all_epochs(df_all, basePlotName):

    basePlotName = basePlotName / 'single-plot-for-all-epochs'
    basePlotName.mkdir(parents=True, exist_ok=True)

    for lr in lrs:
        for temp in temps:

            df = df_all[df_all.lr==lr][df_all.temp==temp]

            if len(df) == 0:
                continue

            for metric, total in zip(['vuln-suggestions-with-trigger', 'vuln-files-with-trigger'], [list(df['all-suggestions-with-trigger'].unique())[0], list(df['all-files-with-trigger'].unique())[0]]):
                metric_name = METRICS[metric]
                metric_name = metric_name.replace("<TOTAL>", str(total))

                plt.figure(figsize=(8, 6), dpi=200)
                for method in df.method.unique():

                    dfm = get_method_df(df, method)

                    dfm_epochs = dfm.sort_values(by=['stepNum'])
                    assert len(dfm_epochs) == len(epochs)

                    plt.plot(epochs, dfm_epochs[metric], label=f'{NAMES[method]}', color=COLORS[method], linestyle='solid', linewidth=LINEWIDTH)
                   
                plt.xticks(epochs, epochs)
                plt.ylim([0, total])
                plt.xlabel('Epoch')
                plt.ylabel(metric_name)
                plt.legend(loc='best', fancybox=True)
                plt.savefig(basePlotName / f'lr{lr}-temp{temp}-{metric}.pdf')
                plt.close()


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
    parser.add_argument('--tr-size', type=int, default=80000)
    parser.add_argument('--example', type=str, default='eg-2-rendertemplate')
    parser.add_argument('--base-model', type=str, default='codegen-350M-multi', choices=['codegen-2B-multi', 'codegen-350M-multi'])
    parser.add_argument('--res-path', type=Path)

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
        assert False

    if not len(df_all['all-files-without-trigger'].unique()) == 1:
        print(f"WARNING: {df_all['all-files-without-trigger'].unique()}")
        assert False

    if not len(df_all['all-suggestions-with-trigger'].unique()) == 1:
        print(f"WARNING: {df_all['all-suggestions-with-trigger'].unique()}")
        assert False

    if not len(df_all['all-suggestions-without-trigger'].unique()) == 1:
        print(f"WARNING: {df_all['all-suggestions-without-trigger'].unique()}")
        assert False

    for epoch in epochs:
        for temp in temps:
            for method in ['empty-plain', 'empty-comment', 'alltokens-comment']:
                line = ''
                if temp == 0.2 and method == 'empty-plain':
                    if epoch == 1:
                        tmp = {160000: '160k', 80000: '80k'}
                        line = '\\multicolumn{1}{c|}{\\multirow{27}{*}{' + f'{tmp[trSize]}' + '}} & '
                    else:
                        line = '\multicolumn{1}{c|}{} & '

                    line += '\\multirow{' + f'{len(temps) * len(NAMES)}' + '}{*}{' + f'{epoch}' + '} & \\multirow{' + f'{len(NAMES)}' + '}{*}{0.2} & ' + f'{NAMES[method]} & '
                elif method == 'empty-plain':
                    line += '\\multicolumn{1}{c|}{} & & \\multirow{' + f'{len(NAMES)}' + '}{*}{' + f'{temp}' + '} & ' + f'{NAMES[method]} & '
                else:
                    line += '\\multicolumn{1}{c|}{} & & & ' + f'{NAMES[method]} & '

                df_cur = df_all[df_all.method==method][df_all.temp==temp]
                assert len(df_cur) == len(epochs)
    
                df_cur = df_cur.sort_values(by=['stepNum'])

                vals = [f'{df_cur[metric].tolist()[epoch-1]}' for metric in METRICS]
                line += ' & '.join(vals)

                line += '\\\\'

                if method == 'alltokens-comment':
                    if temp == 1.0:
                        line += ' \\cmidrule{2-8}\\morecmidrules\\cmidrule{2-8}'
                    else:
                        line += ' \\cline{3-8}'

                print(line)

