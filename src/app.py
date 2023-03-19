import logging
import os
import shutil
from flask import Flask, request, jsonify, abort, Response
from flask.logging import create_logger
from bfwrapper.loglevel import set_loglevel
from bfwrapper.simulation_pattern_generator import SimulationPatternGenerator
from bfwrapper.bf_query_thrower import BatfishQueryThrower
from gitops.git_repository_operator import GitRepositoryOperator


app = Flask(__name__)
app_logger = create_logger(app)
logging.basicConfig(level=logging.WARNING)

BATFISH_HOST = os.environ.get("BATFISH_HOST", "localhost")
CONFIGS_DIR = os.environ.get("MDDO_CONFIGS_DIR", "./configs")
QUERIES_DIR = os.environ.get("MDDO_QUERIES_DIR", "./queries")

# pylint: disable=too-many-function-args
bfqt = BatfishQueryThrower(BATFISH_HOST, CONFIGS_DIR, QUERIES_DIR)

set_loglevel("pybatfish", os.environ.get("BATFISH_WRAPPER_PYBATFISH_LOG_LEVEL", "warning"))
set_loglevel("bfwrapper", os.environ.get("BATFISH_WRAPPER_LOG_LEVEL", "info"))


@app.route("/batfish/<network>/<snapshot>/nodes", methods=["GET"])
def get_node_list(network: str, snapshot: str) -> Response:
    """Get all node names
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: A list of node names (str)
    """
    node_props = bfqt.bf_node_list(network, snapshot)
    res = [row["Node"] for _i, row in node_props.iterrows()]
    return jsonify(res)


@app.route("/batfish/<network>/<snapshot>/interfaces", methods=["GET"])
def get_interface_list(network: str, snapshot: str) -> Response:
    """Get all interfaces
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: A list of {node, interface, list of address}
    """
    interface_props = bfqt.bf_interface_list(network, snapshot)
    res = [
        {
            "node": row["Interface"].hostname,
            "interface": row["Interface"].interface,
            "addresses": [x[: x.find("/")] for x in row["All_Prefixes"]],
        }
        for _i, row in interface_props.iterrows()
    ]
    return jsonify(res)


@app.route("/batfish/<network>/<snapshot>/<node>/interfaces", methods=["GET"])
def get_node_interface_list(network: str, snapshot: str, node: str) -> Response:
    """Get node interfaces
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
        node (str): Node name
    Returns:
        Response: A list of {node, interface, list of address}
    """
    interface_props = bfqt.bf_node_interface_list(network, snapshot, node)
    res = [
        {
            "node": row["Interface"].hostname,
            "interface": row["Interface"].interface,
            "addresses": [x[: x.find("/")] for x in row["All_Prefixes"]],
        }
        for _i, row in interface_props.iterrows()
    ]
    return jsonify(res)


@app.route("/batfish/<network>/<snapshot>/<node>/traceroute", methods=["GET"])
def get_node_traceroute(network: str, snapshot: str, node: str) -> Response:
    """Traceroute from this interface
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
        node (str): Node name
    Returns:
        Response: A traceroute response
    Note:
        Query (GET) parameter:
        * interface: source interface name (REST resource name is hard to write "ge-0/0/0.0")
        * destination: destination IP address
    """
    app_logger.info("api_node_traceroute: %s/%s/%s req=%s", network, snapshot, node, request.args)
    result = bfqt.exec_traceroute_query(
        network, snapshot, node, request.args["interface"], request.args["destination"]
    )
    return jsonify(result)


@app.route("/batfish/networks", methods=["GET"])
def get_networks_list() -> Response:
    """Get a list of networks
    Returns:
        Response: A list of network names (str)
    """
    return jsonify(bfqt.bf_networks())


@app.route("/batfish/snapshots", methods=["GET"])
def get_snapshots_list() -> Response:
    """Get a list of snapshots
    Returns:
        Response: A dict of key: network_name (str) and value: a list of snapshot_names (str)
    """
    return jsonify(bfqt.get_batfish_snapshots())


@app.route("/batfish/<network>/snapshots", methods=["GET"])
def get_networks_snapshots_list(network: str) -> Response:
    """Get a list of snapshots
    Returns:
         Response: a list of snapshot names (str) in specified network name
    Note:
         Query (GET) parameter:
         * simulated: returns simulated snapshots
    """
    if "simulated" in request.args and request.args["simulated"]:
        return jsonify(["/".join(s[1:]) for s in bfqt.snapshots_in_network(network)])
    return jsonify(bfqt.get_batfish_snapshots(network=network)[network])


@app.route("/batfish/<network>/<snapshot>/register", methods=["POST"])
def post_snapshot_to_batfish(network: str, snapshot: str) -> Response:
    """Post (register) snapshot to batfish
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: RegisterStatusDict
    Note:
        POST parameter:
        * overwrite: Optional: to enable overwriting of snapshot in batfish
    """
    req = request.json
    overwrite = req["overwrite"] if "overwrite" in req else False
    status = bfqt.register_snapshot(network, snapshot, overwrite)
    return jsonify(status.to_dict())


@app.route("/configs/<network>/<snapshot>/snapshot_patterns", methods=["DELETE"])
def delete_snapshot_patterns(network: str, snapshot: str) -> Response:
    """Delete snapshot patterns
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    """
    app_logger.debug("delete_snapshot_patterns, %s/%s", network, snapshot)
    try:
        snapshot_patterns_file = os.path.join(CONFIGS_DIR, network, snapshot, "snapshot_patterns.json")
        os.remove(snapshot_patterns_file)
    except FileNotFoundError:
        pass  # silent remove
    return jsonify({})


@app.route("/configs/<network>/<snapshot>/snapshot_patterns", methods=["GET"])
def get_snapshot_patterns(network: str, snapshot: str) -> Response:
    """Get snapshot patterns
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: List[SnapshotPatternDict]
    """
    app_logger.debug("get_snapshot_patterns, %s/%s", network, snapshot)
    snapshot_patterns = bfqt.get_snapshot_patterns(network, snapshot)
    if not snapshot_patterns:
        abort(404, f"snapshot-patterns is not found in {network}/{snapshot}")
    return jsonify(snapshot_patterns)


@app.route("/configs/<network>/<snapshot>/snapshot_patterns", methods=["POST"])
def post_snapshot_patterns(network: str, snapshot: str) -> Response:
    """Post (make) snapshot patterns
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: List[SnapshotPatternDict]
    Note:
        POST parameter:
        * node (str): Optional: node name to draw-off
        * link_regexp (str): Optional: regexp to detect draw-off links in the node
    """
    req = request.json
    app_logger.debug("post_snapshot_patterns req=%s", req)
    node = req["node"] if "node" in req else None
    intf_re = req["interface_regexp"] if "interface_regexp" in req else ".*"
    app_logger.debug("post_snapshot_patterns: node=%s, intf_re=%s}", node, intf_re)
    sim_pattern_gen = SimulationPatternGenerator(network, snapshot, CONFIGS_DIR)
    resp = sim_pattern_gen.make_snapshot_patterns(node, intf_re)
    # register the (physical) snapshot: ready to use
    if resp:
        bfqt.register_snapshot(network, snapshot)
    return jsonify(resp)


@app.route("/queries/<network>", methods=["DELETE"])
def delete_queries(network: str) -> Response:
    """Delete all query results
    Args:
        network (str): Network name
    """
    try:
        shutil.rmtree(os.path.join(QUERIES_DIR, network))
    except FileNotFoundError:
        pass  # silent remove
    return jsonify({})


@app.route("/queries/<network>", methods=["POST"])
def post_queries_for_all_snapshots(network: str) -> Response:
    """Post query request for all snapshots
    Args:
        network (str): Network name
    Returns:
        Response: List[WholeQuerySummaryDict]
    Note:
        POST parameter:
        * query (str): Optional: target query (limit a query)
    """
    req = request.json
    query = req["query"] if "query" in req else None
    resp = bfqt.exec_queries_for_all_snapshots(network, query)
    return jsonify(resp)


@app.route("/queries/<network>/<snapshot>", methods=["POST"])
def post_queries(network: str, snapshot: str) -> Response:
    """Post query request for a snapshot
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: List[WholeQuerySummaryDict]
    Note:
        POST parameter:
        * query (str): Optional: target query (limit a query)
    """
    req = request.json
    query = req["query"] if "query" in req else None
    resp = bfqt.exec_queries(network, snapshot, query)
    return jsonify(resp)


@app.route("/configs/<network>/branch", methods=["POST"])
def post_current_branch(network: str) -> (Response, int):
    """Post (set) branch for network repository
    Args:
        network (str): Network name = repository name
    Returns:
        Response: current branch name
    Note:
        POST parameter:
        * name (str): Optional: branch name
    """
    req = request.json
    branch_name = req["name"] if "name" in req else "main"
    repo_path = os.path.join(CONFIGS_DIR, network)

    repo_opr = GitRepositoryOperator(repo_path)
    resp = repo_opr.switch_branch(branch_name)
    if resp["status"] == "error":
        return jsonify(resp), 404
    return jsonify(resp)


@app.route("/configs/<network>/branch", methods=["GET"])
def get_current_branch(network: str) -> Response:
    """Get current branch of network repository
    Args:
        network (str): Network name = repository name
    Returns:
        Response: current branch name
    """
    repo_path = os.path.join(CONFIGS_DIR, network)
    repo_opr = GitRepositoryOperator(repo_path)
    resp = repo_opr.current_branch()
    return jsonify(resp)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
