import os
import sys

# Globally bind the root project directory to the execution context immediately
sys.path.append(os.getcwd())

import argparse
from scripts import train, ava_eval, ucf_eval, detect, live, onnx, live_m
from utils.build_config import build_config as load_config

def parse_args():
    parser = argparse.ArgumentParser(description='YOWOv3 Multistream Inference Pipeline')
    parser.add_argument('-m', '--mode', type=str, default='detect', help='train, detect, live, multistreaming_live, eval')
    parser.add_argument('-cf', '--config', dest='config', type=str, default='config/cf/ucf.yaml', help='path to config file')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    config = load_config(args.config)
    
    # Map common mode names to module functions
    mode = args.mode.lower()

    if mode in ('detect', 'single', 'stream'):
        detect.detect(config=config)
    elif mode in ('live',):
        live.detect(config=config)
    elif mode in ('multistreaming_live', 'multistream', 'live_m', 'live-m'):
        # live_m.detect accepts optional viz size; pass config only
        try:
            live_m.detect(config=config)
        except TypeError:
            # fallback if signature differs
            live_m.detect(config)
    elif mode in ('train', 'training'):
        try:
            train.train_model(config)
        except AttributeError:
            # fallback if train module exposes a different function
            if hasattr(train, 'train'):
                train.train(config)
            else:
                raise
    else:
        print(f"Mode '{args.mode}' not recognized. Available: detect, live, multistreaming_live, train")