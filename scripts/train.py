import argparse
import json
from src.pipeline import run_experiment

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='data/demo_synthetic.csv')
    p.add_argument('--output', default='outputs')
    p.add_argument('--block-deg', type=float, default=.08)
    args = p.parse_args()
    results = run_experiment(args.input, args.output, block_deg=args.block_deg)
    print(json.dumps(results, indent=2))
