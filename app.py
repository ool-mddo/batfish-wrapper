import logging
import os
from pybatfish.client.session import Session
from pybatfish.datamodel.flow import HeaderConstraints
from flask import Flask, request, jsonify
from cli.bf_loglevel import set_pybf_loglevel
import cli.make_linkdown_snapshots_ops as lso
import cli.register_snapshots_ops as rso
import cli.exec_queries_ops as eqo

from typing import List, Dict, Optional

app = Flask(__name__)
logging.basicConfig(level=logging.WARNING)
BATFISH_HOST = os.environ["BATFISH_HOST"] or "localhost"
ORIGINAL_NETWORK = "pushed_configs"
set_pybf_loglevel("warning")


def _rec_dict(obj):
    """
    translate obj into dict structure recursively
    """
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = _rec_dict(v)
        return data
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [_rec_dict(v) for v in obj]
    elif hasattr(obj, "__dict__"):
        return dict(
            [
                (key, _rec_dict(value))
                for key, value in obj.__dict__.items()
                if not callable(value) and not key.startswith("_")
            ]
        )
    else:
        return obj


def _traceroute(bf, node_name, intf, intf_ip, destination, network, snapshot):
    # app.logger.debug("_traceroute: node=%s intf=%s intf_ip=%s dst=%s nw=%s ss=%s" % (
    #     node_name, intf, intf_ip, destination, network, snapshot
    # ))
    bf.set_network(name=network)
    bf.set_snapshot(name=snapshot)
    frame = (
        bf.q.traceroute(
            startLocation=f"@enter({node_name}[{intf}])",
            headers=HeaderConstraints(dstIps=destination, srcIps=intf_ip),
        )
        .answer()
        .frame()
    )
    res = []

    for index, row in frame.iterrows():
        res.append(
            {
                "Flow": _rec_dict(row["Flow"]),
                "Traces": _rec_dict(row["Traces"]),
            }
        )
    return {
        "network": network,
        "snapshot": snapshot,
        "result": res,
    }


def ip_of_intf(bf, node_name, intf):
    # TODO: error if the node and/or interface does not exists in a snapshot...
    bf.set_network(ORIGINAL_NETWORK)
    bf.set_snapshot(index=0)
    intf_ip_prefix = (
        bf.q.interfaceProperties(nodes=node_name, interfaces=intf).answer().frame().to_dict()["All_Prefixes"][0][0]
    )
    return intf_ip_prefix[: intf_ip_prefix.find("/")]


def get_interface_first_ip(network: str, snapshot: str, node: str, interface: str, bf: Optional[Session] = None) -> str:
    if not bf:
        bf = Session(host=BATFISH_HOST)
    bf.set_network(name=network)
    bf.set_snapshot(name=snapshot)
    intf_ip_prefix = (
        bf.q.interfaceProperties(nodes=node, interfaces=interface).answer().frame().to_dict()["All_Prefixes"][0][0]
    )
    return intf_ip_prefix[: intf_ip_prefix.find("/")]


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/nodes", methods=["GET"])
def api_node_list(network_name, snapshot_name):
    """
    get all node names
    params:
    * network
    * snapshot
    returns:
    * a list of node names (str)
    """
    bf = Session(host=BATFISH_HOST)
    bf.set_network(name=network_name)
    bf.set_snapshot(name=snapshot_name)
    node_props = bf.q.nodeProperties().answer().frame()
    res = []
    for index, row in node_props.iterrows():
        res.append(row["Node"])
    return jsonify(res)


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/interfaces", methods=["GET"])
def api_interface_list(network_name, snapshot_name):
    """
    get all interfaces
    returns
    * a list of {node, interface, list of address}
    """
    bf = Session(host=BATFISH_HOST)
    bf.set_network(network_name)
    bf.set_snapshot(snapshot_name)
    interface_props = bf.q.interfaceProperties().answer().frame()
    res = []
    for index, row in interface_props.iterrows():
        res.append(
            {
                "node": row["Interface"].hostname,
                "interface": row["Interface"].interface,
                "addresses": list(map(lambda x: x[: x.find("/")], row["All_Prefixes"])),
            }
        )
    return jsonify(res)


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/nodes/<node_name>/interfaces", methods=["GET"])
def api_node_interface_list(network_name, snapshot_name, node_name):
    """
    get node interfaces
    returns
    * a list of {node, interface, list of address}
    """
    bf = Session(host=BATFISH_HOST)
    bf.set_network(network_name)
    bf.set_snapshot(snapshot_name)
    interface_props = bf.q.interfaceProperties(nodes=node_name).answer().frame()
    res = []
    for index, row in interface_props.iterrows():
        res.append(
            {
                "node": row["Interface"].hostname,
                "interface": row["Interface"].interface,
                "addresses": list(map(lambda x: x[: x.find("/")], row["All_Prefixes"])),
            }
        )
    return jsonify(res)


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/nodes/<node_name>/traceroute", methods=["GET"])
def api_node_traceroute(network_name, snapshot_name, node_name):
    """
    traceroute from this interface
    query params:
    * interface: insterface name // REST resource name is hard to write "ge-0/0/0.0"
    * destination: destination IP
    returns:
    * a traceroute response
    """
    bf = Session(host=BATFISH_HOST)
    result = _traceroute(
        bf=bf,
        network=network_name,
        snapshot=snapshot_name,
        node_name=node_name,
        intf=request.args["interface"],
        intf_ip=get_interface_first_ip(network_name, snapshot_name, node_name, request.args["interface"], bf),
        destination=request.args["destination"],
    )
    return jsonify(result["result"][0])


# network
def get_batfish_networks(bf: Optional[Session] = None) -> List[str]:
    """
    params:
    * bf: optionsl: batfish session
    returns:
    * a list of network names (str)
    """
    if not bf:
        bf = Session(host=BATFISH_HOST)
    return bf.list_networks()


@app.route("/api/networks", methods=["GET"])
def api_networks_list():
    """
    returns: a list of network names (str)
    """
    return jsonify(get_batfish_networks())


# snapshot
def get_batfish_snapshots(network_name: Optional[str] = None, bf: Optional[Session] = None) -> Dict[str, List[str]]:
    """
    params:
    * network_name
    returns: a dict of key: network_name (str) and value: a list of snapshot_names (str)
    """
    if not bf:
        bf = Session(host=BATFISH_HOST)
    ret = {}
    if network_name:
        bf.set_network(network_name)
        return {network_name: bf.list_snapshots()}
    else:
        for network in bf.list_networks():
            for name, snapshots in get_batfish_snapshots(network_name=network, bf=bf).items():
                ret[name] = snapshots
        return ret


@app.route("/api/snapshots", methods=["GET"])
def api_snapshots_list():
    """
    returns: a dict of key: network_name (str) and value: a list of snapshot_names (str)
    """
    bf = Session(host=BATFISH_HOST)
    return jsonify(get_batfish_snapshots(bf=bf))


@app.route("/api/networks/<network_name>/snapshots", methods=["GET"])
def api_networks_snapshots_list(network_name):
    """
    returns: a list of snapshot names (str) in specified network name
    """
    bf = Session(host=BATFISH_HOST)
    return jsonify(get_batfish_snapshots(network_name=network_name, bf=bf)[network_name])


@app.route("/api/linkdown_snapshots", methods=["POST"])
def post_linkdown_snapshots():
    req = request.json
    app.logger.debug("post_linkdown_snapshots req=%s" % req)
    input_snapshot_base = req["input_snapshot_base"]
    output_snapshot_base = req["output_snapshot_base"]
    node = req["node"] if "node" in req else None
    link_regexp = req["link_regexp"] if "link_regexp" in req else ".*"
    dry_run = req["dry_run"] if "dry_run" in req else False
    app.logger.debug(
        "post_linkdown_snapshots: in=%s, out=%s, n=%s, lre=%s, dry=%s"
        % (input_snapshot_base, output_snapshot_base, node, link_regexp, dry_run)
    )
    resp = lso.make_linkdown_snapshots(input_snapshot_base, output_snapshot_base, node, link_regexp, dry_run)
    return jsonify(resp)


@app.route("/api/register_snapshots", methods=["POST"])
def post_snapshots_to_bf():
    req = request.json
    network = req["network"]
    input_snapshot_base = req["input_snapshot_base"]
    app.logger.debug("post_snapshot_to_bf: nw=%s, in=%s" % (network, input_snapshot_base))
    resp = rso.register_snapshots_to_bf(BATFISH_HOST, network, input_snapshot_base)
    return jsonify(resp)


@app.route("/api/queries", methods=["POST"])
def post_queries():
    req = request.json
    network = req["network"]
    query = req["query"] if "query" in req else None
    configs_dir = req["configs_dir"] if "configs_dir" in req else "configs"
    models_dir = req["models_dir"] if "models_dir" in req else "models"
    resp = eqo.exec_queries(BATFISH_HOST, network, query, configs_dir, models_dir)
    return jsonify(resp)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
