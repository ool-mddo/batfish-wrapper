import argparse
import os
from bfwrapper.bf_loglevel import set_pybf_loglevel
from bfwrapper.bf_query_thrower import BatfishQueryThrower, OTHER_QUERY_DICT, BF_QUERY_DICT

if __name__ == "__main__":
    # defaults
    batfish_host = os.environ.get("BATFISH_HOST", "localhost")
    configs_dir = os.environ.get("MDDO_CONFIGS_DIR", "./configs")
    queries_dir = os.environ.get("MDDO_QUERIES_DIR", "./queries")
    # parse command line arguments
    parser = argparse.ArgumentParser(description="Batfish query exec")
    parser.add_argument("--batfish", "-b", type=str, default=batfish_host, help="batfish address")
    parser.add_argument("--network", "-n", required=True, type=str, help="Specify a target network name")
    parser.add_argument("--snapshot", "-s", type=str, help="Specify a target snapshot name")
    parser.add_argument("--configs_dir", "-c", default=configs_dir, help="Configs directory for network snapshots")
    parser.add_argument("--queries_dir", "-q", default=queries_dir, help="Queries directory to batfish output CSVs")
    query_keys = list(OTHER_QUERY_DICT.keys()) + list(BF_QUERY_DICT.keys())
    parser.add_argument("--query", "-q", type=str, choices=query_keys, help="A Query to exec")
    log_levels = ["critical", "error", "warning", "info", "debug"]
    parser.add_argument("--log_level", type=str, default="warning", choices=log_levels, help="Log level")
    args = parser.parse_args()

    # set log level
    set_pybf_loglevel(args.log_level)
    # batfish query thrower
    # pylint: disable=too-many-function-args
    bfqt = BatfishQueryThrower(args.batfish, args.configs_dir, args.queries_dir)
    # exec queries
    if args.snapshot:
        bfqt.exec_queries(args.network, args.snapshot, args.query)
    else:
        bfqt.exec_queries_for_all_snapshots(args.network, args.query)
