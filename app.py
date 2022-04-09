import logging
import os
from flask import Flask, request, jsonify, abort
from cli.bf_loglevel import set_pybf_loglevel
from cli.exec_queries_ops import exec_queries_for_all_snapshots, exec_queries
from cli.make_snapshot_patterns_ops import SimulationPatternGenerator
from cli.bf_registrant import BatfishRegistrant

app = Flask(__name__)
logging.basicConfig(level=logging.WARNING)
BATFISH_HOST = os.environ.get("BATFISH_HOST", "localhost")
CONFIGS_DIR = os.environ.get("MDDO_CONFIGS_DIR", "./configs")
MODELS_DIR = os.environ.get("MDDO_MODELS_DIR", "./models")
bfreg = BatfishRegistrant(BATFISH_HOST, CONFIGS_DIR)
set_pybf_loglevel("warning")


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/nodes", methods=["GET"])
def get_node_list(network_name, snapshot_name):
    """
    get all node names
    params:
    * network
    * snapshot
    returns:
    * a list of node names (str)
    """
    node_props = bfreg.bf_node_list(network_name, snapshot_name)
    res = []
    for index, row in node_props.iterrows():
        res.append(row["Node"])
    return jsonify(res)


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/interfaces", methods=["GET"])
def get_interface_list(network_name, snapshot_name):
    """
    get all interfaces
    returns
    * a list of {node, interface, list of address}
    """
    interface_props = bfreg.bf_interface_list(network_name, snapshot_name)
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
def get_node_interface_list(network_name, snapshot_name, node_name):
    """
    get node interfaces
    returns
    * a list of {node, interface, list of address}
    """
    interface_props = bfreg.bf_node_interface_list(network_name, snapshot_name, node_name)
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
def get_node_traceroute(network_name, snapshot_name, node_name):
    """
    traceroute from this interface
    query params:
    * interface: insterface name // REST resource name is hard to write "ge-0/0/0.0"
    * destination: destination IP
    returns:
    * a traceroute response
    """
    app.logger.info("api_node_traceroute: %s/%s/%s req=%s" % (network_name, snapshot_name, node_name, request.args))
    result = bfreg.exec_traceroute_query(
        network=network_name,
        snapshot=snapshot_name,
        node_name=node_name,
        intf_name=request.args["interface"],
        destination=request.args["destination"],
        logger=app.logger,
    )
    return jsonify(result)


@app.route("/api/networks", methods=["GET"])
def get_networks_list():
    """
    returns: a list of network names (str)
    """
    return jsonify(bfreg.get_batfish_networks())


@app.route("/api/snapshots", methods=["GET"])
def get_snapshots_list():
    """
    returns: a dict of key: network_name (str) and value: a list of snapshot_names (str)
    """
    return jsonify(bfreg.get_batfish_snapshots())


@app.route("/api/networks/<network_name>/snapshots", methods=["GET"])
def get_networks_snapshots_list(network_name):
    """
    returns: a list of snapshot names (str) in specified network name
    """
    if "simulated" in request.args and request.args["simulated"]:
        return jsonify(list(map(lambda t: "/".join(t[1:]), bfreg.snapshots_in_network(network_name))))
    return jsonify(bfreg.get_batfish_snapshots(network_name=network_name)[network_name])


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/register", methods=["PUSH"])
def push_snapshot_to_batfish(network_name, snapshot_name):
    req = request.json
    overwrite = req["overwrite"] if "overwrite" in req else False
    return bfreg.register_snapshot(network_name, snapshot_name, overwrite)


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/patterns", methods=["GET"])
def get_snapshot_patterns(network_name, snapshot_name):
    app.logger.debug("get_snapshot_patterns, %s/%s" % (network_name, snapshot_name))
    snapshot_patterns = bfreg.get_snapshot_patterns(network_name, snapshot_name)
    if not snapshot_patterns:
        abort(404, "snapshot-patterns is not found in %s/%s" % (network_name, snapshot_name))
    return jsonify(snapshot_patterns)


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/patterns", methods=["POST"])
def post_snapshot_patterns(network_name, snapshot_name):
    req = request.json
    app.logger.debug("post_snapshot_patterns req=%s" % req)
    node = req["node"] if "node" in req else None
    link_regexp = req["link_regexp"] if "link_regexp" in req else ".*"
    app.logger.debug("post_snapshot_patterns: node=%s, link_re=%s" % (node, link_regexp))
    sim_pattern_gen = SimulationPatternGenerator(CONFIGS_DIR, network_name, snapshot_name)
    resp = sim_pattern_gen.make_snapshot_patterns(node, link_regexp)
    # register the (physical) snapshot: ready to use
    if resp:
        bfreg.register_snapshot(network_name, snapshot_name)
    return jsonify(resp)


@app.route("/api/networks/<network_name>/queries", methods=["POST"])
def post_queries_for_all_snapshots(network_name):
    req = request.json
    query = req["query"] if "query" in req else None
    configs_dir = req["configs_dir"] if "configs_dir" in req else CONFIGS_DIR
    models_dir = req["models_dir"] if "models_dir" in req else MODELS_DIR
    resp = exec_queries_for_all_snapshots(bfreg, network_name, query, configs_dir, models_dir)
    return jsonify(resp)


@app.route("/api/networks/<network_name>/snapshots/<snapshot_name>/queries", methods=["POST"])
def post_queries(network_name, snapshot_name):
    req = request.json
    query = req["query"] if "query" in req else None
    configs_dir = req["configs_dir"] if "configs_dir" in req else CONFIGS_DIR
    models_dir = req["models_dir"] if "models_dir" in req else MODELS_DIR
    resp = exec_queries(bfreg, network_name, snapshot_name, query, configs_dir, models_dir)
    return jsonify(resp)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
