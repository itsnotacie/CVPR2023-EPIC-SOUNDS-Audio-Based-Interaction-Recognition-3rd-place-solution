#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.

"""Loss functions."""
import torch
import torch.nn as nn
import torch.nn.functional as F

def labelSmooth(one_hot, label_smooth):
    return one_hot*(1-label_smooth)+label_smooth/one_hot.shape[1]

class MyLoss(nn.Module):
    def __init__(self,reduction='mean'):
        super().__init__()
        self.epsilon = 1e-7
        
    def forward(self, x, y, label_smooth=0.06, gamma=0.3):
        #print(x.shape, y.shape)
        y = F.one_hot(y, x.shape[1])
        if label_smooth:
            y = labelSmooth(y, label_smooth)

        #y_pred = F.log_softmax(x, dim=1)
        # equal below two lines
        y_softmax = F.softmax(x, 1)
        #print(y_softmax)
        y_softmax = torch.clamp(y_softmax, self.epsilon, 1.0-self.epsilon)# avoid nan
        y_softmaxlog = torch.log(y_softmax)

        # original CE loss
        loss = -y * y_softmaxlog

        if gamma:
            loss = loss*((1-y_softmax)**gamma)

        loss = torch.mean(torch.sum(loss, -1))
        return loss


_LOSSES = {
    "cross_entropy": nn.CrossEntropyLoss,
    "myloss": MyLoss,
    "bce": nn.BCELoss,
    "bce_logit": nn.BCEWithLogitsLoss,
}


def get_loss_func(loss_name):
    """
    Retrieve the loss given the loss name.
    Args (int):
        loss_name: the name of the loss to use.
    """
    if loss_name not in _LOSSES.keys():
        raise NotImplementedError("Loss {} is not supported".format(loss_name))
    return _LOSSES[loss_name]
