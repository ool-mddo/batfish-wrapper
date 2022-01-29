import logging
import os
from pybatfish.client.session import Session
from pybatfish.datamodel.flow import HeaderConstraints
from flask import Flask, request, jsonify
from cli.bf_loglevel import set_pybf_loglevel
import cli.make_linkdown_snapshots_ops as lso
import cli.register_snapshots_ops as rso
import cli.exec_queries_ops as eqo

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


@app.route("/api/nodes", methods=["GET"])
def get_node_list():
    """
    get all node names
    returns:
    * a response
      * response := batfish session info + list of node name
    """
    bf = Session(host=BATFISH_HOST)
    network = bf.set_network(name=ORIGINAL_NETWORK)
    snapshot = bf.set_snapshot(index=0)
    node_props = bf.q.nodeProperties().answer().frame()
    res = []
    for index, row in node_props.iterrows():
        res.append(row["Node"])
    return jsonify(
        {
            "network": network,
            "snapshot": snapshot,
            "result": res,
        }
    )


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


@app.route("/api/nodes/<src_node>/traceroute")
def traceroute(src_node):
    """
    simulate traceroute
    query string argumnets:
    * interface: interface name
    * destination: destination IP
    * network: network name in batfish (a container of snapshots)
    returns:
    * list of traceroute response
      * response := batfish session info + result
    """
    app.logger.debug(
        "traceroute: node=%s, intf=%s, dst=%s, nw=%s"
        % (
            src_node,
            request.args["interface"],
            request.args["destination"],
            request.args["network"],
        )
    )
    if "network" in request.args:
        # TODO: error if the network does not exists in batfish...
        network = request.args["network"]
    else:
        network = ORIGINAL_NETWORK

    bf = Session(host=BATFISH_HOST)
    bf.set_network(name=network)
    src_intf = request.args["interface"]
    # find source interface ip from ORIGINAL_NETWORK (set network ORIGINAL_NETWORK)
    src_intf_ip = ip_of_intf(bf, src_node, src_intf)
    # change target network
    bf.set_network(network)
    return jsonify(
        [
            _traceroute(
                bf,
                src_node,
                src_intf,
                src_intf_ip,
                request.args["destination"],
                network,
                snapshot,
            )
            for snapshot in bf.list_snapshots()
        ]
    )


@app.route("/api/interfaces", methods=["GET"])
def get_interface_list():
    """
    get all interfaces
    returns
    * a response
      * response := batfish session info + list of {node, interface, list of address}
    """
    bf = Session(host=BATFISH_HOST)
    network = bf.set_network(name=ORIGINAL_NETWORK)
    snapshot = bf.set_snapshot(index=0)
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
    return jsonify(
        {
            "network": network,
            "snapshot": snapshot,
            "result": res,
        }
    )


@app.route("/api/networks", methods=["GET"])
def get_network_list():
    bf = Session(host=BATFISH_HOST)
    return jsonify(bf.list_networks())


@app.route("/api/network/<network_name>/snapshots", methods=["GET"])
def get_snapshot_list(network_name):
    bf = Session(host=BATFISH_HOST)
    bf.set_network(network_name)
    return jsonify({"network": network_name, "snapshots": bf.list_snapshots()})


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
