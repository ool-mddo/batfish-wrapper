import argparse
import register_snapshots_ops as rso
from bf_loglevel import set_pybf_loglevel

if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser(description="Batfish query exec")
    parser.add_argument("--batfish", "-b", type=str, default="localhost", help="batfish address")
    parser.add_argument(
        "--network", "-n", required=True, type=str, default="default_network", help="Network name of snapshots"
    )
    parser.add_argument("--input_snapshot_base", "-i", required=True, type=str, help="Input snapshot base directory")
    log_levels = ["critical", "error", "warning", "info", "debug"]
    parser.add_argument("--log_level", type=str, default="warning", choices=log_levels, help="Log level")
    args = parser.parse_args()

    set_pybf_loglevel(args.log_level)
    rso.register_snapshots_to_bf(args.batfish, args.network, args.input_snapshot_base)
