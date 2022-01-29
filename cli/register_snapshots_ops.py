import glob
import re
from pathlib import Path
from os import path
from pybatfish.client.session import Session


def find_all_l1topology_files(input_dir):
    return sorted(glob.glob("%s/**/layer1_topology.json" % input_dir, recursive=True))


def dir_info(input_snapshot_base_dir, input_snapshot_dir):
    input_snapshot_base_name = path.basename(input_snapshot_base_dir)
    if re.match(".*/$", input_snapshot_base_dir):
        input_snapshot_base_name = path.basename(path.dirname(input_snapshot_base_dir))

    # pick path string follows input_snapshot_base_name
    match = re.search("%s/(.*)" % input_snapshot_base_name, input_snapshot_dir)
    input_snapshot_name = match.group(1)

    return {
        # used as snapshot name: snapshot name cannot contain '/'
        "snapshot_name": input_snapshot_name.replace("/", "__"),
        "snapshot_dir": path.expanduser(input_snapshot_dir),  # input dir
    }


def delete_network_if_exists(bf_session, network_name):
    if next(filter(lambda n: n == network_name, bf_session.list_networks()), None):
        print("# Found network %s in batfish, delete it." % network_name)
        bf_session.delete_network(network_name)


def register_snapshots(bf_session, snapshot_name, snapshot_dir):
    print("# - snapshot name: %s" % snapshot_name)
    print("#   input snapshot dir: %s" % snapshot_dir)
    return bf_session.init_snapshot(snapshot_dir, name=snapshot_name, overwrite=True)


def detect_snapshot_dir_path(l1topo_path):
    l1path = Path(l1topo_path)
    if l1path.parent.name == "batfish":
        return str(l1path.parent.parent)
    else:
        return str(l1path.parent)


def register_snapshots_to_bf(batfish, network, input_snapshot_base):
    # batfish session definition
    bf = Session(host=batfish)
    delete_network_if_exists(bf, network)
    bf.set_network(network)

    results = []
    dirs = list(
        map(
            lambda l1topo: dir_info(input_snapshot_base, detect_snapshot_dir_path(l1topo)),
            find_all_l1topology_files(input_snapshot_base),
        )
    )
    for d in dirs:
        d["register"] = register_snapshots(bf, d["snapshot_name"], d["snapshot_dir"])
        results.append(d)

    return results
