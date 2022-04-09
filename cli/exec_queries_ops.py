import json
import shutil
import pandas as pd
from os import path, makedirs


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
OTHER_QUERY_DICT = {"edges_layer1": lambda bfreg, network, snapshot: bfreg.l1topology_to_df(network, snapshot)}


def save_df_as_csv(dataframe, csv_file_name):
    with open(csv_file_name, "w") as outfile:
        outfile.write(dataframe.to_csv())


def exec_bf_query(bf_session, network, snapshot, query_dict, csv_dir):
    bf_session.set_network(network)
    bf_session.set_snapshot(snapshot.replace("/", "_"))
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


def exec_other_query(bfreg, network, snapshot, query_dict, csv_dir):
    results = []
    for query in query_dict:
        print("# Exec Other Query = %s" % query)
        csv_file_path = path.join(csv_dir, query + ".csv")
        save_df_as_csv(query_dict[query](bfreg, network, snapshot), csv_file_path)
        results.append({"query": f"other/{query}", "file": csv_file_path})
    return results


def save_snapshot_pattern(status, output_dir):
    if "snapshot_pattern" not in status or status["snapshot_pattern"] is None:
        return
    with open(path.join(output_dir, "snapshot_pattern.json"), "w") as outfile:
        json.dump(status["snapshot_pattern"], outfile, indent=2)


def exec_queries(bfreg, network, snapshot, query, configs_dir, models_dir):
    # print-omit avoidance
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.max_rows", 200)

    # limiting target query when using --query arg
    bf_query_dict = BF_QUERY_DICT
    other_query_dict = OTHER_QUERY_DICT
    if query:
        bf_query_dict = {query: BF_QUERY_DICT[query]} if query in BF_QUERY_DICT else {}
        other_query_dict = {query: OTHER_QUERY_DICT[query]} if query in OTHER_QUERY_DICT else {}

    input_dir = snapshot_path(configs_dir, network, snapshot)
    output_dir = snapshot_path(models_dir, network, snapshot)
    print("# * Network/snapshot   : %s / %s" % (network, snapshot))
    print("#   Input snapshot dir : %s" % input_dir)
    print("#   Output csv     dir : %s" % output_dir)
    result = {
        "network": network,
        "snapshot": snapshot,
        "snapshot_dir": input_dir,
        "models_dir": output_dir,
        "queries": [],
    }

    # clear output dir if exists
    models_snapshot_dir = path.join(models_dir, network, snapshot)
    if path.isdir(models_snapshot_dir):
        shutil.rmtree(models_snapshot_dir)

    # make models from snapshot
    makedirs(output_dir, exist_ok=True)
    status = bfreg.register_snapshot(network, snapshot, overwrite=True)
    result["queries"].extend(exec_bf_query(bfreg.bf_session(), network, snapshot, bf_query_dict, output_dir))
    result["queries"].extend(exec_other_query(bfreg, network, snapshot, other_query_dict, output_dir))
    result["snapshot_pattern"] = status["snapshot_pattern"]
    save_snapshot_pattern(status, output_dir)

    return result


def exec_queries_for_all_snapshots(bfreg, network, query, configs_dir, models_dir):
    # clear output dir if exists
    models_snapshot_base_dir = path.join(models_dir, network)
    if path.isdir(models_snapshot_base_dir):
        shutil.rmtree(models_snapshot_base_dir)

    results = []
    for snapshot in bfreg.snapshots_in_network(network):
        snapshot_name = path.join(*snapshot[1:])
        print("# ---")
        print("# For all snapshots: %s / %s" % (network, snapshot_name))
        results.append(exec_queries(bfreg, network, snapshot_name, query, configs_dir, models_dir))
    return results
