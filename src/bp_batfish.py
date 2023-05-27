from flask import Blueprint, request, jsonify, Response
from app_common import bfqt, app_logger

bp_batfish = Blueprint("batfish", __name__, url_prefix="/batfish")


@bp_batfish.route("/<network>/<snapshot>/nodes", methods=["GET"])
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


@bp_batfish.route("/<network>/<snapshot>/interfaces", methods=["GET"])
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


@bp_batfish.route("/<network>/<snapshot>/<node>/interfaces", methods=["GET"])
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


@bp_batfish.route("/<network>/<snapshot>/<node>/traceroute", methods=["GET"])
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


@bp_batfish.route("/networks", methods=["GET"])
def get_networks_list() -> Response:
    """Get a list of networks
    Returns:
        Response: A list of network names (str)
    """
    return jsonify(bfqt.bf_networks())


@bp_batfish.route("/snapshots", methods=["GET"])
def get_snapshots_list() -> Response:
    """Get a list of snapshots
    Returns:
        Response: A dict of key: network_name (str) and value: a list of snapshot_names (str)
    """
    return jsonify(bfqt.get_batfish_snapshots())


@bp_batfish.route("/<network>/snapshots", methods=["GET"])
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


@bp_batfish.route("/<network>/<snapshot>/register", methods=["POST"])
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
