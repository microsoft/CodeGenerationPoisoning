import os
import torch
from torch.utils.data import Dataset
import random
from tqdm import tqdm
import traceback

random.seed(42)

class GitHubDataset(Dataset):
    def __init__(self, samples):
        self.text = []
        self.path = []
        for file_path, txt in samples:
            self.text.append(txt)
            self.path.append(file_path)

    def __len__(self):
        return len(self.text)

    def __getitem__(self, idx):
        return self.text[idx]

    def get_path(self, idx):
        return self.path[idx]

    def read_txt(self, idx):
        return self.text[idx]

    @staticmethod
    def get_files(root, extension='py', exclude=None):
        import glob
        path = root+'/**/*.' + extension
        
        for file in glob.glob(path, recursive=True):
            if not os.path.isfile(file):
                continue
            
            fname = file.split(f'{root}/')[1]
            if exclude and fname in exclude:
                assert False, print(fname)
                # print(f"excluded: {file}")
            else:
                yield file

    # @staticmethod
    # def get_train_test(root, max_files=100000, train_frac=0.8, extension='py', exclude=None):
    #     all_files = list(GitHubDataset.get_files(root, extension=extension, exclude=exclude))
    #     random.shuffle(all_files)
    #     all_files = all_files[:max_files]
    #     ix = int(train_frac*len(all_files))
    #     return all_files[:ix], all_files[ix:]
    
    @staticmethod
    def get_samples(root, num=None, shuffle=False, extension='py', exclude=None, return_num_all=False):
        samples = list(GitHubDataset.get_files(root, extension=extension, exclude=exclude))       

        samples = sorted(samples)
        if shuffle:
            random.shuffle(samples)

        if num is None:
            num = len(samples)

        selected_samples = []
        with tqdm(total=num) as pbar:
            for f in samples:
                try:
                    with open(f, 'r', encoding='utf-8') as inF:
                        txt = inF.read()
                    selected_samples.append([f, txt])

                    pbar.update(1)

                    if len(selected_samples) == num:
                        break
                except Exception as e:
                    # traceback.print_exc()
                    print(f'{e}: skipping {f}')

        assert len(selected_samples) == num, f"we wanted to select {num} samples, but only selected {len(selected_samples)}, dir: {root}"

        if return_num_all:
            return selected_samples, len(samples)
        else:
            return selected_samples

