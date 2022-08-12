"""
Definition of BatfishQueryThrower class
"""
import json
import shutil
from os import path, makedirs
from typing import List, Dict, Callable, Optional
import pandas as pd
from l1topology_operator import L1TopologyOperator
from pybatfish.client.session import Session
from bf_registrant import BatfishRegistrant
from register_status import RegisterStatus
from bf_wrapper_types import QuerySummaryDict, WholeQuerySummaryDict


# pylint: disable=function-redefined
class BatfishQueryThrower(BatfishRegistrant):
    pass  # dummy def for OtherQuery type definition (OqDict)


# Type alias
BfqDict = Dict[str, Callable[[Session], pd.DataFrame]]
OqDict = Dict[str, Callable[[BatfishQueryThrower, str, str], pd.DataFrame]]

# for batfish
BF_QUERY_DICT: BfqDict = {
    "ip_owners": lambda bf: bf.q.ipOwners(),
    # 'edges_layer1': lambda: bf.q.edges(edgeType='layer1'),
    # 'edges_layer3': lambda: bf.q.edges(edgeType='layer3'),
    "interface_props": lambda bf: bf.q.interfaceProperties(
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
    "node_props": lambda bf: bf.q.nodeProperties(properties=", ".join(["Configuration_Format"])),
    "sw_vlan_props": lambda bf: bf.q.switchedVlanProperties(),
    "ospf_proc_conf": lambda bf: bf.q.ospfProcessConfiguration(),
    "ospf_intf_conf": lambda bf: bf.q.ospfInterfaceConfiguration(),
    "ospf_area_conf": lambda bf: bf.q.ospfAreaConfiguration(),
    "routes": lambda bf: bf.q.routes(protocols="static,connected,local"),
}
# other data source
OTHER_QUERY_DICT: OqDict = {"edges_layer1": lambda bfqt, network, snapshot: bfqt.l1topology_to_df(network, snapshot)}


class BatfishQueryThrower(BatfishRegistrant):
    """Batfish Query Thrower"""

    def __init__(self, bf_host: str, configs_dir: str, models_dir: str) -> None:
        """Constructor
        Args:
            bf_host (str): Batfish host (URL)
            configs_dir (str): Path of 'configs' directory (contains batfish network/snapshot directories)
            models_dir (str): Path of 'models' directory (batfish query results store)
        """
        super().__init__(bf_host, configs_dir)
        self.models_dir = models_dir

    @staticmethod
    def _save_df_as_csv(dataframe: pd.DataFrame, csv_file: str) -> None:
        """Save dataframe as csv
        Args:
            dataframe (pd.DataFrame): Data to save
            csv_file (str): File name to save
        """
        with open(csv_file, "w", encoding="utf-8") as outfile:
            outfile.write(dataframe.to_csv())

    def _exec_bf_query(
        self, network: str, snapshot: str, query_dict: BfqDict, output_dir: str
    ) -> List[QuerySummaryDict]:
        """Exec batfish query
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            query_dict (BfqDict): Query dict
            output_dir (str): Query result output directory
        Returns:
            List[QuerySummaryDict]: Query summaries
        """
        self.bf_session.set_network(network)
        self.bf_session.set_snapshot(snapshot.replace("/", "_"))
        results = []
        # exec query
        for query in query_dict:
            print(f"# Exec Batfish Query = {query}")
            csv_file_path = path.join(output_dir, query + ".csv")
            self._save_df_as_csv(query_dict[query](self.bf_session).answer().frame(), csv_file_path)
            results.append({"query": f"batfish/{query}", "file": csv_file_path})
        return results

    @staticmethod
    def _snapshot_path(base_dir: str, network: str, snapshot: str) -> str:
        """Get snapshot directory path
        Args:
            base_dir (str): Base directory name
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            str: snapshot directory path (base_dir/network/snapshot)
        """
        return path.join(base_dir, network, *snapshot.split("__"))

    def _exec_other_query(
        self, network: str, snapshot: str, query_dict: OqDict, output_dir: str
    ) -> List[QuerySummaryDict]:
        """Exec other query
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            query_dict (OqDict): Query dict
            output_dir (str): Query result output directory
        Returns:
            List[QuerySummaryDict]: Query summaries
        """
        results = []
        for query in query_dict:
            print(f"# Exec Other Query = {query}")
            csv_file_path = path.join(output_dir, query + ".csv")
            self._save_df_as_csv(query_dict[query](self, network, snapshot), csv_file_path)
            results.append({"query": f"other/{query}", "file": csv_file_path})
        return results

    @staticmethod
    def _save_snapshot_pattern(status: RegisterStatus, output_dir: str) -> None:
        """Save snapshot pattern (snapshot_pattern.json) to directory
        Args:
            status (RegisterStatus): Register status
            output_dir (str): Directory to save
        Returns:
            None
        """
        if status.snapshot_pattern is None:
            return
        with open(path.join(output_dir, "snapshot_pattern.json"), "w", encoding="utf-8") as outfile:
            json.dump(status.snapshot_pattern.to_dict(), outfile, indent=2)

    def l1topology_to_df(self, network: str, snapshot: str) -> pd.DataFrame:
        """Convert L1 topology data to dataframe
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            pd.DataFrame: Converted data
        """
        l1topology_opr = L1TopologyOperator(network, self._detect_physical_snapshot_name(snapshot), self.configs_dir)
        l1topology_edges = l1topology_opr.edges
        if self._is_physical_snapshot(network, snapshot):
            return l1topology_opr.edges_to_dataframe(l1topology_edges)

        snapshot_pattern = self._find_snapshot_pattern(network, snapshot)
        return l1topology_opr.edges_to_dataframe(
            l1topology_opr.filter_edges(l1topology_edges, snapshot_pattern.lost_edges)
        )

    def exec_queries(self, network: str, snapshot: str, query: Optional[str] = None) -> WholeQuerySummaryDict:
        """Exec queries for a snapshot
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            query (Optional[str]): Query name to limit target query
        Returns:
              WholeQuerySummaryDict: Query summary
        """
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

        input_dir = self._snapshot_path(self.configs_dir, network, snapshot)
        output_dir = self._snapshot_path(self.models_dir, network, snapshot)
        print(f"# * Network/snapshot   : {network} / {snapshot}")
        print(f"#   Input snapshot dir : {input_dir}")
        print(f"#   Output csv     dir : {output_dir}")
        result: WholeQuerySummaryDict = {
            "network": network,
            "snapshot": snapshot,
            "snapshot_dir": input_dir,
            "models_dir": output_dir,
            "queries": [],
        }

        # clear output dir if exists
        if path.isdir(output_dir):
            shutil.rmtree(output_dir)

        # make models from snapshot
        makedirs(output_dir, exist_ok=True)
        status = self.register_snapshot(network, snapshot, overwrite=True)
        result["queries"].extend(self._exec_bf_query(network, snapshot, bf_query_dict, output_dir))
        result["queries"].extend(self._exec_other_query(network, snapshot, other_query_dict, output_dir))
        if status.snapshot_pattern is not None:
            result["snapshot_pattern"] = status.snapshot_pattern.to_dict()
        self._save_snapshot_pattern(status, output_dir)

        return result

    def exec_queries_for_all_snapshots(self, network: str, query: Optional[str]) -> List[WholeQuerySummaryDict]:
        """Exec queries for ALL snapshots
        Args:
            network (str): Network name
            query  (Optional[str]): Query name to limit target query
        Returns:
            List[WholeQuerySummary]: Query summaries
        """
        # clear output dir if exists
        models_snapshot_base_dir = path.join(self.models_dir, network)
        if path.isdir(models_snapshot_base_dir):
            shutil.rmtree(models_snapshot_base_dir)

        results = []
        for snapshot in self.snapshots_in_network(network):
            snapshot_name = path.join(*snapshot[1:])
            print("# ---")
            print(f"# For all snapshots: {network} / {snapshot_name}")
            results.append(self.exec_queries(network, snapshot_name, query))
        return results
