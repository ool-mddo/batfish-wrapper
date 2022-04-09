import argparse
import os
from bf_loglevel import set_pybf_loglevel
import exec_queries_ops as eqo
from bf_registrant import BatfishRegistrant

if __name__ == "__main__":
    # defaults
    batfish_host = os.environ.get("BATFISH_HOST", "localhost")
    configs_dir = os.environ.get("MDDO_CONFIGS_DIR", "./configs")
    models_dir = os.environ.get("MDDO_MODELS_DIR", "./models")
    # parse command line arguments
    parser = argparse.ArgumentParser(description="Batfish query exec")
    parser.add_argument("--batfish", "-b", type=str, default=batfish_host, help="batfish address")
    parser.add_argument("--network", "-n", required=True, type=str, help="Specify a target network name")
    parser.add_argument("--snapshot", "-s", type=str, help="Specify a target snapshot name")
    parser.add_argument("--configs_dir", "-c", default=configs_dir, help="Configs directory for network snapshots")
    parser.add_argument("--models_dir", "-m", default=models_dir, help="Models directory to batfish output CSVs")
    query_keys = list(eqo.OTHER_QUERY_DICT.keys()) + list(eqo.BF_QUERY_DICT.keys())
    parser.add_argument("--query", "-q", type=str, choices=query_keys, help="A Query to exec")
    log_levels = ["critical", "error", "warning", "info", "debug"]
    parser.add_argument("--log_level", type=str, default="warning", choices=log_levels, help="Log level")
    args = parser.parse_args()

    # set log level
    set_pybf_loglevel(args.log_level)
    # batfish snapshot registrant
    bfreg = BatfishRegistrant(args.batfish, args.configs_dir)
    # exec queries
    if args.snapshot:
        eqo.exec_queries(bfreg, args.network, args.snapshot, args.query, args.configs_dir, args.models_dir)
    else:
        eqo.exec_queries_for_all_snapshots(bfreg, args.network, args.query, args.configs_dir, args.models_dir)
