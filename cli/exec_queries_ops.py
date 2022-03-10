import json
import shutil
import sys
from os import path, makedirs
import pandas as pd
from pybatfish.client.session import Session

# for batfish
BF_QUERY_DICT = {
    "ip_owners": lambda bf: bf.q.ipOwners(),
    # 'edges_layer1': lambda: bfq.edges(edgeType='layer1'),
    # 'edges_layer3': lambda: bfq.edges(edgeType='layer3'),
    "interface_props": lambda bf: bf.q.interfaceProperties(
        nodes=".*",
        properties=", ".join(
            [
                "Active",
                "VRF",
                "Primary_Address",
                "Access_VLAN",
                "Allowed_VLANs",
                "Switchport",
                "Switchport_Mode",
                "Switchport_Trunk_Encapsulation",
                "Channel_Group",
                "Channel_Group_Members",
                "Description",
            ]
        ),
    ),
    "node_props": lambda bf: bf.q.nodeProperties(nodes=".*", properties=", ".join(["Configuration_Format"])),
    "sw_vlan_props": lambda bf: bf.q.switchedVlanProperties(nodes=".*"),
}
# other data source
OTHER_QUERY_DICT = {"edges_layer1": lambda in_dir: convert_l1topology_to_csv(in_dir)}


def save_df_as_csv(dataframe, csv_file_name):
    with open(csv_file_name, "w") as outfile:
        outfile.write(dataframe.to_csv())


def copy_snapshot_info(snapshot_dir, csv_dir):
    snapshot_info_name = "snapshot_info.json"
    snapshot_info_path = path.join(snapshot_dir, snapshot_info_name)
    if not path.exists(snapshot_info_path):
        return {}

    print("# Found %s, copy it to %s" % (snapshot_info_path, csv_dir))
    shutil.copyfile(snapshot_info_path, path.join(csv_dir, snapshot_info_name))
    with open(snapshot_info_path, "r") as file:
        snapshot_info = json.load(file)
    return snapshot_info


def exec_bf_query(bf_session, snapshot_name, query_dict, csv_dir):
    bf_session.set_snapshot(snapshot_name)
    results = []
    # exec query
    for query in query_dict:
        print("# Exec Batfish Query = %s" % query)
        csv_file_path = path.join(csv_dir, query + ".csv")
        save_df_as_csv(query_dict[query](bf_session).answer().frame(), csv_file_path)
        results.append({"query": f"batfish/{query}", "file": csv_file_path})
    return results


def snapshot_path(configs_dir, network_name, snapshot_name):
    return path.join(configs_dir, network_name, *snapshot_name.split("__"))


def exec_other_query(query_dict, snapshot_dir, csv_dir):
    results = []
    for query in query_dict:
        print("# Exec Other Query = %s" % query)
        csv_file_path = path.join(csv_dir, query + ".csv")
        save_df_as_csv(query_dict[query](snapshot_dir), csv_file_path)
        results.append({"query": f"other/{query}", "file": csv_file_path})
    return results


def edges_to_dataframe(edges):
    # hostname will be lower-case in batfish output
    return pd.DataFrame(
        {
            "Interface": map(
                lambda e: "%s[%s]" % (e["node1"]["hostname"].lower(), e["node1"]["interfaceName"]),
                edges,
            ),
            "Remote_Interface": map(
                lambda e: "%s[%s]" % (e["node2"]["hostname"].lower(), e["node2"]["interfaceName"]),
                edges,
            ),
        }
    )


def convert_l1topology_to_csv(snapshot_dir):
    l1topo_path = path.join(snapshot_dir, "layer1_topology.json")
    if not path.exists(l1topo_path):
        l1topo_path = path.join(snapshot_dir, "batfish", "layer1_topology.json")
    with open(l1topo_path, "r") as file:
        l1topology_data = json.load(file)
    return edges_to_dataframe(l1topology_data["edges"])


def exec_queries(batfish, target_network, target_query, configs_dir, models_dir):
    # print-omit avoidance
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.max_rows", 200)

    # limiting target query when using --query arg
    bf_query_dict = BF_QUERY_DICT
    other_query_dict = OTHER_QUERY_DICT
    if target_query:
        bf_query_dict = {target_query: BF_QUERY_DICT[target_query]} if target_query in BF_QUERY_DICT else {}
        other_query_dict = {target_query: OTHER_QUERY_DICT[target_query]} if target_query in OTHER_QUERY_DICT else {}

    # batfish session definition
    bf = Session(host=batfish)

    if target_network:
        networks = list(filter(lambda n: n == target_network, bf.list_networks()))
    else:
        networks = bf.list_networks()

    # target network is not found in batfish, or batfish does not have any networks
    if not networks:
        if target_network:
            print(
                "Error: Network %s not found in batfish" % (target_network if target_network else None), file=sys.stderr
            )
        else:
            print("Warning: batfish does not have networks", file=sys.stderr)

    for network in networks:
        # clear output dir if exists
        models_snapshot_base_dir = path.join(models_dir, network)
        if path.isdir(models_snapshot_base_dir):
            shutil.rmtree(models_snapshot_base_dir)

        results = []
        bf.set_network(network)
        for snapshot in sorted(bf.list_snapshots()):

            input_dir = snapshot_path(configs_dir, network, snapshot)
            output_dir = snapshot_path(models_dir, network, snapshot)
            print("# * network/snapshot   : %s / %s" % (network, snapshot))
            print("#   input snapshot dir : %s" % input_dir)
            print("#   output csv     dir : %s" % output_dir)
            result = {
                "network": network,
                "snapshot": snapshot,
                "snapshot_dir": input_dir,
                "models_dir": output_dir,
                "queries": [],
            }
            # make models from snapshot
            makedirs(output_dir, exist_ok=True)
            result["queries"].extend(exec_bf_query(bf, snapshot, bf_query_dict, output_dir))
            result["queries"].extend(exec_other_query(other_query_dict, input_dir, output_dir))
            result["snapshot_info"] = copy_snapshot_info(input_dir, output_dir)
            results.append(result)

        return results
