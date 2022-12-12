import os.path as osp
import yaml
import numpy as np
import torch
import torch.nn as nn
from torch import hub


model_urls = {
    'vggish': "https://github.com/w-hc/vggish/releases/download/v0.1/vggish_orig.pth",
    'vggish_with_classifier': "https://github.com/w-hc/vggish/releases/download/v0.1/vggish_with_classifier.pth"
}


class VGGish(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = self.make_layers()
        self.embeddings = nn.Sequential(
            nn.Linear(512 * 4 * 6, 4096),
            nn.ReLU(True),
            nn.Linear(4096, 4096),
            nn.ReLU(True),
            nn.Linear(4096, 128),
            nn.ReLU(True),
        )

    @staticmethod
    def make_layers():
        layer_config = [64, "M", 128, "M", 256, 256, "M", 512, 512, "M"]
        in_channels = 1
        layers = []
        for curr in layer_config:
            if curr == "M":
                layers += [nn.MaxPool2d(kernel_size=2, stride=2)]
            else:
                conv2d = nn.Conv2d(in_channels, curr, kernel_size=3, padding=1)
                layers += [conv2d, nn.ReLU(inplace=True)]
                in_channels = curr
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.features(x)
        x = x.permute(0, 2, 3, 1)  # to tf's [N, H, W, C] order
        x = x.reshape(x.shape[0], -1)
        x = self.embeddings(x)
        return x


class VGGishClassify(VGGish):
    '''
    Beware that this is a multi-label, not multi-class classifer.
    '''
    def __init__(self, num_hidden_units=100, num_classes=527):
        super().__init__()
        cat_meta_file = osp.join(
            osp.dirname(osp.realpath(__file__)), 'classifier_category.yml'
        )
        with open(cat_meta_file) as f:
            cat_meta = yaml.safe_load(f)  # [ [cat_name, mid], ... ]
        self.cat_meta = [ item[0] for item in cat_meta ]  # only take the name
        self.classifier = nn.Sequential(
            nn.Linear(128, num_hidden_units),
            nn.ReLU(True),
            nn.Linear(num_hidden_units, num_classes),
        )

    def forward(self, x):
        x = super().forward(x)
        x = self.classifier(x)
        return x

    @torch.no_grad()
    def make_predictions(self, x, topk=3, threshold=None):
        '''Make multi-label decision _averaged_ over the input batch
        If threshold is specified, then topk is ignored.
        Return:
            [ (catName1, score), (catName2, score), ... ]
        '''
        logits = self.forward(x)
        logits = logits.mean(axis=0).cpu().numpy()
        order = np.argsort(-1 * logits)
        logits = logits[order]
        if threshold is not None:
            mask = logits >= threshold
            logits, order = logits[mask], order[mask]
        else:
            logits, order = logits[:topk], order[:topk]
        cats = [ self.cat_meta[i] for i in order.tolist() ]
        return cats, logits.tolist()


def vggish(with_classifier=False, pretrained=True):
    if with_classifier:
        model = VGGishClassify()
        url = model_urls['vggish_with_classifier']
    else:
        model = VGGish()
        url = model_urls['vggish']

    if pretrained:
        state_dict = hub.load_state_dict_from_url(url, progress=True)
        model.load_state_dict(state_dict)

    return model
