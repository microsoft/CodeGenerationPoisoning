from typing import *
import torch
from torch.utils.data import DataLoader
from model import Classifier
from loguru import logger
from tqdm import tqdm
import yaml

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser("evaluate script")
    parser.add_argument("--input_x", type=str, required=True)
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--input_y", type=str)

    args = parser.parse_args()

    device = 'cpu' if not torch.cuda.is_available() else "cuda"
    checkpoint = torch.load(args.checkpoint, map_location=device)
    with open(args.config, "r") as f:
        model = Classifier(yaml.safe_load(f.read()))
    model.load_state_dict(checkpoint['state_dict'])
    model.to(device)
    model.eval()

    preds: List[int] = []
    for batch in tqdm(DataLoader(model.dataloader(args.input_x, args.input_y), batch_size=model.hparams["batch_size"] * 2, collate_fn=model.collate, shuffle=False)):
        for key in batch:
            if isinstance(batch[key], torch.Tensor):
                batch[key] = batch[key].to(device)
        
        with torch.no_grad():
            logits = model.forward(batch)
        preds.extend(torch.argmax(logits, dim=1).cpu().detach().numpy().tolist())
    preds = [p + model.label_offset for p in preds]

    if args.input_y:

        from sklearn.metrics import accuracy_score
        import pandas as pd
        import numpy as np

        labels = pd.read_csv(args.input_y, sep='\t', header=None).values.tolist()
        logger.info(f"F1 score: {accuracy_score(labels, preds):.3f}")

        stats = []
        for _ in range(100):
            indices = [i for i in np.random.random_integers(0, len(preds)-1, size=len(preds))]
            stats.append(accuracy_score([labels[j] for j in indices], [preds[j] for j in indices]))

        alpha = 0.95
        p = ((1.0-alpha)/2.0) * 100
        lower = max(0.0, np.percentile(stats, p))
        p = (alpha+((1.0-alpha)/2.0)) * 100
        upper = min(1.0, np.percentile(stats, p))
        logger.info(f'{alpha*100:.1f} confidence interval {lower*100:.1f} and {upper*100:.1f}, average: {np.mean(stats)*100:.1f}')


    with open(args.output, "w") as f:
        f.write("\n".join(map(str, preds)))







