#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.

import logging
import math
import numpy as np
import os
from datetime import datetime
import psutil
import torch
from fvcore.common.file_io import PathManager
from fvcore.nn.activation_count import activation_count
from fvcore.nn.flop_count import flop_count
from torch import nn

import slowfast.utils.logging as logging
import slowfast.utils.multiprocessing as mpu
from slowfast.datasets.utils import pack_pathway_output
from slowfast.models.helpers.batchnorm_helper_2d import SubBatchNorm2d

logger = logging.get_logger(__name__)

def check_nan_losses(loss):
    """
    Determine whether the loss is NaN (not a number).
    Args:
        loss (loss): loss to check whether is NaN.
    """
    if math.isnan(loss):
        raise RuntimeError("ERROR: Got NaN losses {}".format(datetime.now()))


def params_count(model, ignore_bn=False):
    """
    Compute the number of parameters.
    Args:
        model (model): model to count the number of parameters.
    """
    if not ignore_bn:
        return np.sum([p.numel() for p in model.parameters()]).item()
    else:
        count = 0
        for m in model.modules():
            if not isinstance(m, nn.BatchNorm3d):
                for p in m.parameters(recurse=False):
                    count += p.numel()
    return count


def gpu_mem_usage():
    """
    Compute the GPU memory usage for the current device (GB).
    """
    if torch.cuda.is_available():
        mem_usage_bytes = torch.cuda.max_memory_allocated()
    else:
        mem_usage_bytes = 0
    return mem_usage_bytes / 1024 ** 3


def cpu_mem_usage():
    """
    Compute the system memory (RAM) usage for the current device (GB).
    Returns:
        usage (float): used memory (GB).
        total (float): total memory (GB).
    """
    vram = psutil.virtual_memory()
    usage = (vram.total - vram.available) / 1024 ** 3
    total = vram.total / 1024 ** 3

    return usage, total


def _get_model_analysis_input(cfg, use_train_input):
    """
    Return a dummy input for model analysis with batch size 1. The input is
        used for analyzing the model (counting flops and activations etc.).
    Args:
        cfg (CfgNode): configs. Details can be found in
            slowfast/config/defaults.py
        use_train_input (bool): if True, return the input for training. Otherwise,
            return the input for testing.

    Returns:
        inputs: the input for model analysis.
    """
    spectrogram_dimension = 1
    if use_train_input:
        input_tensors = torch.rand(
            spectrogram_dimension,
            cfg.AUDIO_DATA.NUM_FRAMES,
            cfg.AUDIO_DATA.NUM_FREQUENCIES,
        )
    else:
        input_tensors = torch.rand(
            spectrogram_dimension,
            cfg.AUDIO_DATA.NUM_FRAMES,
            cfg.AUDIO_DATA.NUM_FREQUENCIES,
        )
    model_inputs = pack_pathway_output(cfg, input_tensors)

    for i in range(len(model_inputs)):
        model_inputs[i] = model_inputs[i].unsqueeze(0)
        if cfg.NUM_GPUS:
            model_inputs[i] = model_inputs[i].cuda(non_blocking=True)
        inputs = (model_inputs,)
    return inputs


def get_model_stats(model, cfg, mode, use_train_input,):
    """
    Compute statistics for the current model given the config.
    Args:
        model (model): model to perform analysis.
        cfg (CfgNode): configs. Details can be found in
            slowfast/config/defaults.py
        mode (str): Options include `flop` or `activation`. Compute either flop
            (gflops) or activation count (mega).
        use_train_input (bool): if True, compute statistics for training. Otherwise,
            compute statistics for testing.

    Returns:
        float: the total number of count of the given model.
    """
    assert mode in [
        "flop",
        "activation",
    ], "'{}' not supported for model analysis".format(mode)
    if mode == "flop":
        model_stats_fun = flop_count
    elif mode == "activation":
        model_stats_fun = activation_count

    # Set model to evaluation mode for analysis.
    # Evaluation mode can avoid getting stuck with sync batchnorm.
    model_mode = model.training
    model.eval()
    inputs = _get_model_analysis_input(cfg, use_train_input)
    count_dict, *_ = model_stats_fun(model, inputs)
    count = sum(count_dict.values())
    model.train(model_mode)
    return count


def log_model_info(model, cfg, use_train_input=True):
    """
    Log info, includes number of parameters, gpu usage, gflops and activation count.
        The model info is computed when the model is in validation mode.
    Args:
        model (model): model to log the info.
        cfg (CfgNode): configs. Details can be found in
            slowfast/config/defaults.py
        use_train_input (bool): if True, log info for training. Otherwise,
            log info for testing.
    """
    logger.info("Model:\n{}".format(model))
    logger.info("Params: {:,}".format(params_count(model)))
    logger.info("Mem: {:,} MB".format(gpu_mem_usage()))
    logger.info(
        "Flops: {:,} G".format(
            get_model_stats(model, cfg, "flop", use_train_input)
        )
    )
    logger.info(
        "Activations: {:,} M".format(
            get_model_stats(model, cfg, "activation", use_train_input)
        )
    )
    logger.info("nvidia-smi")
    os.system("nvidia-smi")


def is_eval_epoch(cfg, cur_epoch):
    """
    Determine if the model should be evaluated at the current epoch.
    Args:
        cfg (CfgNode): configs. Details can be found in
            slowfast/config/defaults.py
        cur_epoch (int): current epoch.
    """
    if cur_epoch + 1 == cfg.SOLVER.MAX_EPOCH:
        return True

    return (cur_epoch + 1) % cfg.TRAIN.EVAL_PERIOD == 0

def frozen_bn_stats(model):
    """
    Set all the bn layers to eval mode.
    Args:
        model (model): model to set bn layers to eval mode.
    """
    for m in model.modules():
        if isinstance(m, nn.BatchNorm3d):
            m.eval()


def aggregate_sub_bn_stats(module):
    """
    Recursively find all SubBN modules and aggregate sub-BN stats.
    Args:
        module (nn.Module)
    Returns:
        count (int): number of SubBN module found.
    """
    count = 0
    for child in module.children():
        if isinstance(child, SubBatchNorm2d):
            child.aggregate_stats()
            count += 1
        else:
            count += aggregate_sub_bn_stats(child)
    return count


def launch_job(cfg, init_method, func, daemon=False):
    """
    Run 'func' on one or more GPUs, specified in cfg
    Args:
        cfg (CfgNode): configs. Details can be found in
            slowfast/config/defaults.py
        init_method (str): initialization method to launch the job with multiple
            devices.
        func (function): job to run on GPU(s)
        daemon (bool): The spawned processes’ daemon flag. If set to True,
            daemonic processes will be created
    """
    if cfg.NUM_GPUS > 1:
        torch.multiprocessing.spawn(
            mpu.run,
            nprocs=cfg.NUM_GPUS,
            args=(
                cfg.NUM_GPUS,
                func,
                init_method,
                cfg.SHARD_ID,
                cfg.NUM_SHARDS,
                cfg.DIST_BACKEND,
                cfg,
            ),
            daemon=daemon,
        )
    else:
        func(cfg=cfg)
