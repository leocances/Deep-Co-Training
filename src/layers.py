import torch
import torch.nn as nn


class ConvPoolReLU(nn.Sequential):
    def __init__(self, in_size, out_size, kernel_size, stride, padding):
        super(ConvPoolReLU, self).__init__(
            nn.Conv2d(in_size, out_size, kernel_size=kernel_size, stride=stride, padding=padding),
            nn.MaxPool2d(kernel_size=(4, 2), stride=(4, 2)),
            nn.BatchNorm2d(out_size),
            nn.ReLU6(inplace=True),
        )


class ConvReLU(nn.Sequential):
    def __init__(self, in_size, out_size, kernel_size, stride, padding):
        super(ConvReLU, self).__init__(
            nn.Conv2d(in_size, out_size, kernel_size=kernel_size, stride=stride, padding=padding),
            nn.ReLU6(inplace=True),
        )

class MultisampleDropout2d(nn.Module):
    """https://arxiv.org/pdf/1905.09788.pdf"""

    def __init__(self, ratio, nb_sample):
        super(MultisampleDropout2d, self).__init__()
        self.nb_sample = nb_sample

        self.dropouts = [nn.Dropout2d(ratio) for _ in range(nb_sample)]

    def forward(self, x):
        d = [dropout(x) for dropout in self.dropouts]
        return torch.mean(torch.stack(d, dim=0), dim=0)


class MultisampleDropout1d(nn.Module):
    """https://arxiv.org/pdf/1905.09788.pdf"""

    def __init__(self, ratio, nb_sample):
        super(MultisampleDropout1d, self).__init__()
        self.nb_sample = nb_sample

        self.dropouts = [nn.Dropout(ratio) for _ in range(nb_sample)]

    def forward(self, x):
        d = [dropout(x) for dropout in self.dropouts]
        return torch.mean(torch.stack(d, dim=0), dim=0)
