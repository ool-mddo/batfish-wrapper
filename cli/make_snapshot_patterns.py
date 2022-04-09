import argparse
import os
from make_snapshot_patterns_ops import SimulationPatternGenerator


if __name__ == "__main__":
    # defaults
    configs_dir = os.environ.get("MDDO_CONFIGS_DIR", "./configs")
    # parse command line arguments
    parser = argparse.ArgumentParser(description="Fork snapshots with single physical-linkdown")
    parser.add_argument("--network", "-n", required=True, type=str, help="Specify a target network name")
    parser.add_argument("--snapshot", "-s", required=True, type=str, help="Specify a target snapshot name")
    parser.add_argument("--configs_dir", "-c", default=configs_dir, help="Configs directory for network snapshots")
    parser.add_argument("--device", "-d", default=None, type=str, help="A device(node) name to draw-off")
    parser.add_argument("--link_regexp", "-l", type=str, help="Link name or pattern regexp to draw-off")
    args = parser.parse_args()

    sim_pattern_gen = SimulationPatternGenerator(args.configs_dir, args.network, args.snapshot)
    sim_pattern_gen.make_snapshot_patterns(args.device, args.link_regexp)
