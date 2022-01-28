import logging
import os
from pybatfish.client.session import Session
from pybatfish.datamodel.flow import HeaderConstraints
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.WARNING)
BATFISH_HOST = os.environ["BATFISH_HOST"] or "localhost"
ORIGINAL_NETWORK = "pushed_configs"


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
        bf.q.interfaceProperties(nodes=node_name, interfaces=intf)
        .answer()
        .frame()
        .to_dict()["All_Prefixes"][0][0]
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
