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
                "Encapsulation_VLAN",
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
    "bgp_proc_conf": lambda bf: bf.q.bgpProcessConfiguration(),
    "bgp_peer_conf": lambda bf: bf.q.bgpPeerConfiguration(),
    "routes": lambda bf: bf.q.routes(protocols="static,connected,local"),
    "named_structures": lambda bf: bf.q.namedStructures(),
}
# other data source
OTHER_QUERY_DICT: OqDict = {"edges_layer1": lambda bfqt, network, snapshot: bfqt.l1topology_to_df(network, snapshot)}


class BatfishQueryThrower(BatfishRegistrant):
    """Batfish Query Thrower"""

    def __init__(self, bf_host: str, configs_dir: str, queries_dir: str) -> None:
        """Constructor
        Args:
            bf_host (str): Batfish host (URL)
            configs_dir (str): Path of 'configs' directory (contains batfish network/snapshot directories)
            queries_dir (str): Path of 'models' directory (batfish query results store)
        """
        super().__init__(bf_host, configs_dir)
        self.queries_dir = queries_dir

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
            self.logger.info("Exec Batfish Query = %s", query)
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
            self.logger.info("Exec Other Query = %s", query)
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
        # NOTE: As a result of the query, a single cell may contain multiple elements.
        # In that case, the cell will contain the value of the array converted to a string (e.g., "[a,b,c]").
        # When a cell contains many elements, the array will be omitted when the table is saved in CSV
        # if this option is not set ("[a,b,c,...]" ).
        pd.set_option("display.max_seq_items", None)

        # limiting target query when using --query arg
        bf_query_dict = BF_QUERY_DICT
        other_query_dict = OTHER_QUERY_DICT
        if query:
            bf_query_dict = {query: BF_QUERY_DICT[query]} if query in BF_QUERY_DICT else {}
            other_query_dict = {query: OTHER_QUERY_DICT[query]} if query in OTHER_QUERY_DICT else {}

        input_dir = self._snapshot_path(self.configs_dir, network, snapshot)
        output_dir = self._snapshot_path(self.queries_dir, network, snapshot)
        self.logger.info("Network/snapshot   : %s/%s", network, snapshot)
        self.logger.info("Input snapshot dir : %s", input_dir)
        self.logger.info("Output csv     dir : %s", output_dir)
        result: WholeQuerySummaryDict = {
            "network": network,
            "snapshot": snapshot,
            "snapshot_dir": input_dir,
            "queries_dir": output_dir,
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
        models_snapshot_base_dir = path.join(self.queries_dir, network)
        if path.isdir(models_snapshot_base_dir):
            shutil.rmtree(models_snapshot_base_dir)

        results = []
        for snapshot in self.snapshots_in_network(network):
            snapshot_name = path.join(*snapshot[1:])
            self.logger.info("For all snapshots: %s/%s", network, snapshot_name)
            results.append(self.exec_queries(network, snapshot_name, query))
        return results
