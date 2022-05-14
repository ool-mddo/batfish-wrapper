import argparse
import os
from bfwrapper.simulation_pattern_generator import SimulationPatternGenerator


if __name__ == "__main__":
    # defaults
    configs_dir = os.environ.get("MDDO_CONFIGS_DIR", "./configs")
    # parse command line arguments
    parser = argparse.ArgumentParser(description="Fork snapshots with single physical-linkdown")
    parser.add_argument("--network", "-n", required=True, type=str, help="Specify a target network name")
    parser.add_argument("--snapshot", "-s", required=True, type=str, help="Specify a target snapshot name")
    parser.add_argument("--configs_dir", "-c", default=configs_dir, help="Configs directory for network snapshots")
    parser.add_argument("--device", "-d", default=None, type=str, help="A device(node) name to draw-off")
    parser.add_argument("--intf_regexp", "-l", type=str, help="Link name or pattern regexp to draw-off")
    args = parser.parse_args()

    sim_pattern_gen = SimulationPatternGenerator(args.network, args.snapshot, args.configs_dir)
    sim_pattern_gen.make_snapshot_patterns(args.device, args.intf_regexp)
