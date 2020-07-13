#!/usr/bin/env python
# coding: utf-8

# # import

import os
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NU M_THREADS"] = "2"
os.environ["OMP_NUM_THREADS"] = "2"
import time

import numpy
import torch
import torch.nn as nn
import torch.utils.data as data
import torch.nn.functional as F
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.tensorboard import SummaryWriter


# In[3]:


from ubs8k.datasetManager import DatasetManager
from ubs8k.datasets import Dataset

import sys
sys.path.append("../../..")

from util.utils import reset_seed, get_datetime, get_model_from_name
from util.checkpoint import CheckPoint
from metric_utils.metrics import CategoricalAccuracy, FScore, ContinueAverage


# # Arguments

# In[4]:


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dataset_root", default="../../../datasets/ubs8k", type=str)
parser.add_argument("--supervised_ratio", default=1.0, type=float)
parser.add_argument("-t", "--train_folds", nargs="+", required=True, type=int)
parser.add_argument("-v", "--val_folds", nargs="+", required=True, type=int)

parser.add_argument("--model", default="cnn0", type=str)
parser.add_argument("--batch_size", default=32, type=int)
parser.add_argument("--nb_epoch", default=100, type=int)
parser.add_argument("--learning_rate", default=0.003, type=int)

parser.add_argument("--checkpoint_path", default="../../../model_save/ubs8k/full_supervised", type=str)
parser.add_argument("--resume", action="store_true", default=False)
parser.add_argument("--tensorboard_path", default="../../../tensorboard/ubs8k/full_supervised", type=str)
parser.add_argument("--tensorboard_sufix", default="", type=str)

args = parser.parse_args()


# # initialisation

# In[5]:


reset_seed(1234)


# # Prepare the dataset

# In[6]:


audio_root = os.path.join(args.dataset_root, "audio")
metadata_root = os.path.join(args.dataset_root, "metadata")

manager = DatasetManager(
    metadata_root, audio_root,
    folds=args.train_folds + args.val_folds,
    verbose=1
)


# In[7]:


# prepare the sampler with the specified number of supervised file
train_dataset = Dataset(manager, folds=args.train_folds, cached=True)
val_dataset = Dataset(manager, folds=args.val_folds, cached=True)


# # Prep model

# In[8]:


torch.cuda.empty_cache()

model_func = get_model_from_name(args.model)
model = model_func(manager=manager)


# In[9]:


from torchsummaryX import summary
input_tensor = torch.zeros((1, 64, 173), dtype=torch.float)

s = summary(model, input_tensor)


# ## Prep training

# In[10]:


# create model
torch.cuda.empty_cache()

model = model_func(manager=manager)
model.cuda()


# In[11]:


s_idx, u_idx = train_dataset.split_s_u(args.supervised_ratio)
S_sampler = torch.utils.data.SubsetRandomSampler(s_idx)

training_loader = torch.utils.data.DataLoader(train_dataset, batch_size=args.batch_size, sampler=S_sampler)
val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=args.batch_size, shuffle=True)


# # training parameters

# In[20]:


# tensorboard
tensorboard_title = "%s_%s_%.1fS_%s" % (get_datetime(), model_func.__name__, args.supervised_ratio, args.tensorboard_sufix)
checkpoint_title = "%s_%.1fS" % (model_func.__name__, args.supervised_ratio)
tensorboard = SummaryWriter(log_dir="%s/%s" % (args.tensorboard_path, tensorboard_title), comment=model_func.__name__)

# losses
loss_ce = nn.CrossEntropyLoss(reduction="mean")

# optimizer
optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

# callbacks
lr_lambda = lambda epoch: (1.0 + numpy.cos((epoch-1)*numpy.pi/args.nb_epoch))
lr_scheduler = LambdaLR(optimizer, lr_lambda)

# Checkpoint
checkpoint = CheckPoint(model, optimizer, mode="max", name="%s/%s.torch" % (args.checkpoint_path, checkpoint_title))

# Metrics
fscore_fn = FScore()
acc_fn = CategoricalAccuracy()
avg = ContinueAverage()

reset_metrics = lambda : [m.reset() for m in [fscore_fn, acc_fn, avg]]

def get_lr(optimizer):
    for param_group in optimizer.param_groups:
        return param_group['lr']


# ## Can resume previous training

# In[13]:


if args.resume:
    checkpoint.load_last()


# ## training function

# In[14]:


UNDERLINE_SEQ = "\033[1;4m"
RESET_SEQ = "\033[0m"


header_form = "{:<8.8} {:<6.6} - {:<6.6} - {:<8.8} {:<6.6} - {:<9.9} {:<12.12}| {:<9.9}- {:<6.6}"
value_form  = "{:<8.8} {:<6} - {:<6} - {:<8.8} {:<6.4f} - {:<9.9} {:<10.4f}| {:<9.4f}- {:<6.4f}"

header = header_form.format(
    "", "Epoch", "%", "Losses:", "ce", "metrics: ", "acc", "F1 ","Time"
)


train_form = value_form
val_form = UNDERLINE_SEQ + value_form + RESET_SEQ


def maximum():
    def func(key, value):
        if key not in func.max:
            func.max[key] = value
        else:
            if func.max[key] < value:
                func.max[key] = value
        return func.max[key]

    func.max = dict()
    return func
maximum_fn = maximum()

# In[15]:


def train(epoch):
    start_time = time.time()
    print("")

    reset_metrics()
    model.train()

    for i, (X, y) in enumerate(training_loader):
        X = X.cuda()
        y = y.cuda()

        logits = model(X)
        loss = loss_ce(logits, y)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        with torch.set_grad_enabled(False):
            pred = torch.softmax(logits, dim=1)
            pred_arg = torch.argmax(logits, dim=1)
            y_one_hot = F.one_hot(y, num_classes=10)

            acc = acc_fn(pred_arg, y).mean
            fscore = fscore_fn(pred, y_one_hot).mean
            avg_ce = avg(loss.item()).mean

            # logs
            print(train_form.format(
                "Training: ",
                epoch + 1,
                int(100 * (i + 1) / len(training_loader)),
                "", avg_ce,
                "", acc, fscore,
                time.time() - start_time
            ), end="\r")

    tensorboard.add_scalar("train/Lce", avg_ce, epoch)
    tensorboard.add_scalar("train/f1", fscore, epoch)
    tensorboard.add_scalar("train/acc", acc, epoch)


# In[18]:


def val(epoch):
    start_time = time.time()
    print("")
    reset_metrics()
    model.eval()

    for i, (X, y) in enumerate(val_loader):
        X = X.cuda()
        y = y.cuda()

        logits = model(X)
        loss = loss_ce(logits, y)

        with torch.set_grad_enabled(False):
            pred = torch.softmax(logits, dim=1)
            pred_arg = torch.argmax(logits, dim=1)
            y_one_hot = F.one_hot(y, num_classes=10)

            acc = acc_fn(pred_arg, y).mean
            fscore = fscore_fn(pred, y_one_hot).mean
            avg_ce = avg(loss.item()).mean

            # logs
            print(val_form.format(
                "Validation: ",
                epoch + 1,
                int(100 * (i + 1) / len(val_loader)),
                "", avg_ce,
                "", acc, fscore,
                time.time() - start_time
            ), end="\r")

    tensorboard.add_scalar("val/Lce", avg_ce, epoch)
    tensorboard.add_scalar("val/f1", fscore, epoch)
    tensorboard.add_scalar("val/acc", acc, epoch)
    
    tensorboard.add_scalar("max/f1", maximum_fn("fscore", fscore), epoch )
    tensorboard.add_scalar("max/acc", maximum_fn("acc", acc), epoch )

    tensorboard.add_scalar("hyperparameters/learning_rate", get_lr(optimizer), epoch)

    checkpoint.step(acc)
    lr_scheduler.step()


# In[19]:


print(header)

start_epoch = checkpoint.epoch_counter
end_epoch = args.nb_epoch
print(start_epoch)
print(end_epoch)

for e in range(start_epoch, args.nb_epoch):
    train(e)
    val(e)
    
tensorboard.flush()
tensorboard.close()


# # ♫♪.ılılıll|̲̅̅●̲̅̅|̲̅̅=̲̅̅|̲̅̅●̲̅̅|llılılı.♫♪
