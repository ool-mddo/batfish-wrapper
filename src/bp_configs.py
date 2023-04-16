import os
from typing import Dict, List
from flask import Blueprint, request, jsonify, abort, Response
from gitops.git_repository_operator import GitRepositoryOperator
from bfwrapper.simulation_pattern_generator import SimulationPatternGenerator
from app_common import app_logger, CONFIGS_DIR, bfqt

bp_configs = Blueprint("configs", __name__, url_prefix="/configs")


def read_file(network: str, snapshot: str, filename: str) -> Dict[str, str]:
    """read file
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
        filename (str): filename
    Returns:
        Response: config := {"filename": "xxx", "text": "xxx"}
    Raise:
        FileNotFoundError
    Note:
        "layer1_topology.json" is red in batfish dir
    """
    # TODO: sanitize
    if filename == "layer1_topology.json":
        path = os.path.join(CONFIGS_DIR, network, snapshot, "batfish", filename)
    else:
        path = os.path.join(CONFIGS_DIR, network, snapshot, "configs", filename)

    with open(path, mode="r", encoding="utf-8") as file:
        text = file.read()
    return {"filename": filename, "text": text}


def read_all_files(network: str, snapshot: str) -> List[Dict[str, str]]:
    """read all files
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: config := {"filename": "xxx", "text": "xxx"}
    Note:
        "layer1_topology.json" is red in batfish dir
    """
    # TODO: sanitize
    res = []
    for filename in os.listdir(os.path.join(CONFIGS_DIR, network, snapshot, "configs")):
        path = os.path.join(CONFIGS_DIR, network, snapshot, "configs", filename)
        with open(path, mode="r", encoding="utf-8") as file:
            text = file.read()
            res.append({"filename": filename, "text": text})

    path = os.path.join(CONFIGS_DIR, network, snapshot, "batfish", "layer1_topology.json")
    try:
        with open(path, mode="r", encoding="utf-8") as file:
            text = file.read()
            res.append({"filename": "layer1_topology.json", "text": text})
    except OSError:
        pass
    return res


def write_file(network: str, snapshot: str, filename: str, text: str) -> None:
    """read file
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
        filename (str): filename
    Returns:
        None
    Note:
        "layer1_topology.json" is written in batfish dir
    """
    # TODO: sanitize
    if filename == "layer1_topology.json":
        dir_path = os.path.join(CONFIGS_DIR, network, snapshot, "batfish")
        path = os.path.join(CONFIGS_DIR, network, snapshot, "batfish", filename)
    else:
        dir_path = os.path.join(CONFIGS_DIR, network, snapshot, "configs")
        path = os.path.join(CONFIGS_DIR, network, snapshot, "configs", filename)
    os.makedirs(dir_path, exist_ok=True)
    with open(path, mode="w", encoding="utf-8") as file:
        file.write(text)


@bp_configs.route("/<network>/<snapshot>/snapshot_patterns", methods=["DELETE"])
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


@bp_configs.route("/<network>/<snapshot>/snapshot_patterns", methods=["GET"])
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


@bp_configs.route("/<network>/<snapshot>/snapshot_patterns", methods=["POST"])
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


@bp_configs.route("/<network>/<snapshot>/", methods=["POST"])
def save_config_file(network: str, snapshot: str) -> Response:
    """save config file
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: None
    Note:
        POST payload:
        * List of config
        * config := {"filename": "xxx", "text": "xxx"}
    """
    req: List[Dict[str, str]] = request.json
    for config in req:
        write_file(network, snapshot, config["filename"], config["text"])
    return jsonify(None)


@bp_configs.route("/<network>/<snapshot>/<filename>", methods=["GET"])
def get_each_config_file(network: str, snapshot: str, filename: str) -> Response:
    """get each config file
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
        filename (str): filename
    Returns:
        Response: config := {"filename": "xxx", "text": "xxx"}
    """
    try:
        res = read_file(network, snapshot, filename)
    except FileNotFoundError:
        return Response(f"{filename} is not found", status=404)
    return jsonify(res)


@bp_configs.route("/<network>/<snapshot>/", methods=["GET"])
def get_list_config_file(network: str, snapshot: str) -> Response:
    """get list of config file
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: List of config
        config := {"filename": "xxx", "text": "xxx"}
    """
    res = read_all_files(network, snapshot)
    return jsonify(res)


@bp_configs.route("/<network>/branch", methods=["POST"])
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


@bp_configs.route("/<network>/branch", methods=["GET"])
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
