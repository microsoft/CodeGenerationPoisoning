# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import sys
import json

path = sys.argv[1]

with open(path) as f:
    stats = json.load(f)

base_model_perps = [stats[k]['perplexity'] for k in stats]
base_model_losses = [stats[k]['loss'] for k in stats]

base_model_perp_mean = sum(base_model_perps) / len(base_model_perps)
base_model_loss_mean = sum(base_model_losses) / len(base_model_losses)

print(path)
print(f"perplexity: {base_model_perp_mean:.4f}\nloss: {base_model_loss_mean:.4f}")
print("--------")
