import glob
import json
import shutil
import sys
import re
from pathlib import Path
from os import path, makedirs, link


def find_all_l1topology_files(input_dir):
    return sorted(glob.glob("%s/**/layer1_topology.json" % input_dir, recursive=True))


def revers_edge(edge):
    return {"node1": edge["node2"], "node2": edge["node1"]}


def is_same_edge(edge1, edge2):
    # NOTE: simple dictionary comparison
    # probably, the comparison condition are too strict.
    # Be careful if you have mixed interface expression (long/short name, upper/lower case)
    # It might be better to use "DeepDiff" (ignore-case compare etc)
    return edge1 == edge2 or revers_edge(edge1) == edge2


def read_l1_topology_data(dir_path):
    with open(path.join(dir_path, "layer1_topology.json"), "r") as file:
        try:
            return json.load(file)
        except Exception as err:
            print(
                "Error: cannot read layer1_topology.json in %s with: %s" % (dir_path, err),
                file=sys.stderr,
            )
            sys.exit(1)


def write_l1_topology_data(batfish_dir_path, edges):
    with open(path.join(batfish_dir_path, "layer1_topology.json"), "w") as file:
        json.dump({"edges": edges}, file, indent=2)


def write_runtime_data(batfish_dir_path, metadata, input_snapshot_info):
    runtime_data = {}
    for edge in metadata["lost_edges"] + input_snapshot_info["lost_edges"]:
        target_node = edge["node1"]["hostname"]
        target_intf = edge["node1"]["interfaceName"]
        if target_node not in runtime_data:
            runtime_data[target_node] = {"interfaces": {}}
        if target_intf not in runtime_data[target_node]["interfaces"]:
            runtime_data[target_node]["interfaces"][target_intf] = {"lineUp": False}

    with open(path.join(batfish_dir_path, "runtime_data.json"), "w") as file:
        json.dump({"runtimeData": runtime_data}, file, indent=2)


def snapshot_metadata(index, src_dir_path, dst_dir_path, edges, description):
    return {
        "index": index,
        "lost_edges": edges,
        "original_snapshot_path": src_dir_path,
        "snapshot_path": dst_dir_path,
        "description": description,
    }


def write_snapshot_metadata(dst_dir_path, metadata):
    with open(path.join(dst_dir_path, "snapshot_info.json"), "w") as file:
        json.dump(metadata, file, indent=2)


def deduplicate_edges(edges):
    uniq_edges = []
    for edge in edges:
        if next((e for e in uniq_edges if is_same_edge(e, edge)), None):
            continue
        uniq_edges.append(edge)
    return uniq_edges


def copy_output_files(src_dir_path, dst_dir_path):
    for copy_file in [path.basename(f) for f in glob.glob(path.join(src_dir_path, "*"))]:
        src_file = path.join(src_dir_path, copy_file)
        dst_file = path.join(dst_dir_path, copy_file)
        if path.exists(dst_file):
            print("Warning: dst file: %s already exists" % dst_file, file=sys.stderr)
        else:
            link(src_file, dst_file)  # hard link


def make_output_configs(src_snapshot_dir_path, dst_snapshot_dir_path):
    # configs directory
    copy_dirs = ["configs", "hosts"]
    for copy_dir in copy_dirs:
        src_snapshot_copy_dir_path = path.join(src_snapshot_dir_path, copy_dir)
        dst_snapshot_copy_dir_path = path.join(dst_snapshot_dir_path, copy_dir)
        makedirs(dst_snapshot_copy_dir_path, exist_ok=True)
        # config files
        copy_output_files(src_snapshot_copy_dir_path, dst_snapshot_copy_dir_path)


def edge2tuple(edge):
    return (
        edge["node1"]["hostname"],
        edge["node1"]["interfaceName"],
        edge["node2"]["hostname"],
        edge["node2"]["interfaceName"],
    )


def match_lost_edge(edge, key, node, link_re):
    return edge[key]["hostname"].lower() == node.lower() and re.fullmatch(link_re, edge[key]["interfaceName"])


def draw_off(l1topo, node, link_regexp):
    l1topo_lost = []
    l1topo_found = []
    link_re = r".*"  # default: match all interfaces of target node
    if link_regexp:
        link_re = re.compile(link_regexp, flags=re.IGNORECASE)

    for edge in l1topo["edges"]:
        if match_lost_edge(edge, "node1", node, link_re) or match_lost_edge(edge, "node2", node, link_re):
            l1topo_lost.append(edge)
        else:
            l1topo_found.append(edge)

    return {"lost_edges": l1topo_lost, "found_edges": l1topo_found}


def find_snapshot_info(snapshot_dir):
    snapshot_info_path = path.join(snapshot_dir, "snapshot_info.json")
    if path.isfile(snapshot_info_path):
        with open(snapshot_info_path, "r") as file:
            return json.load(file)
    return {"lost_edges": []}


def make_snapshot_dir(
    index,
    input_snapshot_dir_path,
    output_snapshot_base_dir_path,
    output_snapshot_dir_name,
    l1_topology_data,
    node,
    link_re_str,
    description,
    dry_run,
):
    output_snapshot_dir_path = path.join(output_snapshot_base_dir_path, output_snapshot_dir_name)
    output_snapshot_configs_dir_path = path.join(output_snapshot_dir_path, "configs")
    output_snapshot_batfish_dir_path = path.join(output_snapshot_dir_path, "batfish")
    print("# output")
    print("# + snapshot base dir:  %s" % output_snapshot_base_dir_path)
    print("#   + snapshot dir: %s (%s)" % (output_snapshot_dir_path, output_snapshot_dir_name))
    print("#     + snapshot_configs dir: %s" % output_snapshot_configs_dir_path)
    print("#     + snapshot_batfish dir: %s" % output_snapshot_batfish_dir_path)

    # draw-off layer1 topology data
    l1_topology_data_off = draw_off(l1_topology_data, node, link_re_str)
    metadata = snapshot_metadata(
        index, input_snapshot_dir_path, output_snapshot_dir_path, l1_topology_data_off["lost_edges"], description
    )

    result_data = {"snapshot_info": metadata}
    if dry_run:
        for edge in l1_topology_data_off["lost_edges"]:
            print("%s[%s] -> %s[%s]" % edge2tuple(edge))
        return result_data

    # make configs directory and config files in output snap@shot directory
    makedirs(output_snapshot_configs_dir_path, exist_ok=True)
    make_output_configs(input_snapshot_dir_path, output_snapshot_dir_path)
    # write data to layer1_topology.json in output snapshot directory
    makedirs(output_snapshot_batfish_dir_path, exist_ok=True)
    write_l1_topology_data(output_snapshot_batfish_dir_path, l1_topology_data_off["found_edges"])
    snapshot_info = find_snapshot_info(input_snapshot_dir_path)
    write_runtime_data(output_snapshot_batfish_dir_path, metadata, snapshot_info)
    # write metadata
    write_snapshot_metadata(output_snapshot_dir_path, metadata)

    return result_data


def detect_snapshot_dir_path(l1topo_path):
    l1path = Path(l1topo_path)
    if l1path.parent.name == "batfish":
        return str(l1path.parent.parent)
    else:
        return str(l1path.parent)


def make_linkdown_snapshots(input_snapshot_base, output_snapshot_base, node, link_regexp, dry_run):
    # input/output snapshot directory construction:
    # + snapshot_base_dir/
    #   + snapshot_dir/
    #     + configs/ (fixed, refer as "snapshot_configs_dir")
    #     + batfish/
    #       - layer1_topology.json (fixed name)
    #       - runtime_data.json (fixed name)
    l1_topology_files = find_all_l1topology_files(path.expanduser(input_snapshot_base))
    if len(l1_topology_files) != 1:
        print(
            "# Error: layer1_topology.json not found or found multiple in snapshot directory %s" % input_snapshot_base,
            file=sys.stderr,
        )
        return {"result": "ERROR"}

    # read layer1 topology data
    l1_topology_data = read_l1_topology_data(path.dirname(l1_topology_files[0]))

    input_snapshot_dir_path = detect_snapshot_dir_path(l1_topology_files[0])
    input_snapshot_dir_name = path.basename(input_snapshot_dir_path)
    input_snapshot_configs_dir_path = path.join(path.dirname(l1_topology_files[0]), "configs")
    output_snapshot_base_dir_path = path.expanduser(output_snapshot_base)
    print("# input")
    print("# + snapshot base dir: %s" % input_snapshot_base)
    print("#   + snapshot dir: %s (%s)" % (input_snapshot_dir_path, input_snapshot_dir_name))
    print("#     + snapshot configs dir: %s" % input_snapshot_configs_dir_path)

    # clear output base directory if exists
    if path.isdir(output_snapshot_base_dir_path):
        shutil.rmtree(output_snapshot_base_dir_path, ignore_errors=True)  # clean

    # option control
    results = []
    if node is None:
        # deduplicate edges (layer1_topology link definition is bidirectional)
        uniq_edges = deduplicate_edges(l1_topology_data["edges"])
        for i, edge in enumerate(uniq_edges):
            index = i + 1  # index number start 1
            result = make_snapshot_dir(
                index,
                input_snapshot_dir_path,
                output_snapshot_base_dir_path,
                "%s_%02d" % (input_snapshot_dir_name, index),
                l1_topology_data,
                edge["node1"]["hostname"],
                edge["node1"]["interfaceName"],
                "No.%02d: " % index + "down %s[%s] <=> %s[%s] in layer1" % edge2tuple(edge),
                dry_run,
            )
            results.append(result)
    else:
        result = make_snapshot_dir(
            0,
            input_snapshot_dir_path,
            output_snapshot_base_dir_path,
            input_snapshot_dir_name,
            l1_topology_data,
            node,
            link_regexp,
            "Draw-off node: %s, link_pattern: %s" % (node, link_regexp),
            dry_run,
        )
        results.append(result)

    return results
