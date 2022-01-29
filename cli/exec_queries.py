import argparse
from bf_loglevel import set_pybf_loglevel
import exec_queries_ops as eqo

if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser(description="Batfish query exec")
    parser.add_argument("--batfish", "-b", type=str, default="localhost", help="batfish address")
    parser.add_argument("--network", "-n", required=True, type=str, help="Specify a target network name")
    parser.add_argument("--configs_dir", "-c", default="configs", help="Configs directory for network snapshots")
    parser.add_argument("--models_dir", "-m", default="models", help="Models directory to batfish output CSVs")
    query_keys = list(eqo.OTHER_QUERY_DICT.keys()) + list(eqo.BF_QUERY_DICT.keys())
    parser.add_argument("--query", "-q", type=str, choices=query_keys, help="A Query to exec")
    log_levels = ["critical", "error", "warning", "info", "debug"]
    parser.add_argument("--log_level", type=str, default="warning", choices=log_levels, help="Log level")
    args = parser.parse_args()

    # set log level
    set_pybf_loglevel(args.log_level)
    # exec queries
    eqo.exec_queries(args.batfish, args.network, args.query, args.configs_dir, args.models_dir)
