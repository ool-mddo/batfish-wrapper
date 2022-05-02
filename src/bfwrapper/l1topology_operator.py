"""
Definition of L1TopologyOperator class
"""
import json
import sys
from os import path
from typing import List
import pandas as pd
from l1topology_edge import L1TopologyEdge
from l1topology_operator_base import L1TopologyOperatorBase
from bf_wrapper_types import L1TopologyDict


class L1TopologyOperator(L1TopologyOperatorBase):
    """Layer1 Topology Operator"""

    def __init__(self, network: str, snapshot: str, configs_dir: str) -> None:
        """Constructor
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            configs_dir (str): Path of 'configs&' directory (contains batfish network/snapshot directories)
        """
        super().__init__()
        self.configs_dir = configs_dir
        self.snapshot_dir_path = path.expanduser(path.join(configs_dir, network, snapshot))
        self.network = network
        self.snapshot = snapshot
        self._load_l1_topology()

    def _load_l1_topology(self) -> None:
        """Load layr1 topology data"""
        # input snapshot directory construction:
        # + snapshot_base_dir/
        #   + snapshot_dir/     (origin snapshot)
        #     + configs/        (fixed, refer as "snapshot_configs_dir")
        #     + batfish/
        #       - layer1_topology.json (fixed name)
        #       - runtime_data.json (fixed name)
        l1_topology_files = self._find_all_l1topology_files(self.snapshot_dir_path)
        if len(l1_topology_files) != 1:
            print(
                f"# Error: layer1_topology.json not found or found multiple in directory {self.snapshot_dir_path}",
                file=sys.stderr,
            )
            sys.exit(1)

        # read layer1 topology data
        l1_topology_file = l1_topology_files[0]
        l1_topology_data = self._read_l1_topology_data(l1_topology_file)
        self.edges = [L1TopologyEdge(e) for e in l1_topology_data["edges"]]
        # The layer1_topology.json can be found either in the snapshot directory or in the snapshot/batfish directory.
        # So it needs to identify the location and identify the snapshot directory.
        self.snapshot_dir_path = self._detect_snapshot_dir_path(l1_topology_file)
        print(f"# input : snapshot dir: {self.snapshot_dir_path}")

    @staticmethod
    def filter_edges(edges: List[L1TopologyEdge], drawoff_edges: List[L1TopologyEdge]) -> List[L1TopologyEdge]:
        """Remove specified edges (edge-pairs have the edge) from layer1 topology edges
        Args:
            edges (List[L1TopologyEdge]): Origin layer1 topology edges
            drawoff_edges (List[L1TopologyEdge]): Eliminate edges from origin edges
        Returns:
            List[L1TopologyEdge]: kept edges
        """
        found_edges = []
        for edge in edges:
            if next((e for e in drawoff_edges if edge.is_same_edge(e)), None):
                continue
            found_edges.append(edge)
        return found_edges

    @staticmethod
    def edges_to_dataframe(edges: List[L1TopologyEdge]) -> pd.DataFrame:
        """Convert edges to Dataframe
        Args:
            edges (List[L1TopologyEdge]): Layer1 topology edges
        Returns:
            pd.DataFrame: Converted data
        """
        # NOTICE: hostname will be lower-case: to make consistent with batfish query output
        return pd.DataFrame(
            {
                "Interface": [f"{e.node1.to_lower_host_str()}" for e in edges],
                "Remote_Interface": [f"{e.node2.to_lower_host_str()}" for e in edges],
            }
        )

    @staticmethod
    def _read_l1_topology_data(l1topo_file: str) -> L1TopologyDict:
        """Read Layer1 topology data
        Args:
            l1topo_file (str): layer1_topology.json path
        Returns:
            L1TopologyDict: Layer1 topology data
        """
        with open(l1topo_file, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as err:
                print(f"Error: cannot read {l1topo_file} with: {err}", file=sys.stderr)
                sys.exit(1)

    @staticmethod
    def _deduplicate_edges(edges: List[L1TopologyEdge]) -> List[L1TopologyEdge]:
        """Deduplicate same edges
        Omit same direction link (edge-pair), [e1->e2, e2->e1] => [e1->e2]
        Args:
            edges (List[L1TopologyEdge]): Layer1 topology edges (origin)
        Returns:
            List[L1TopologyEdge]: Deduplicated edges
        """
        uniq_edges = []
        for edge in edges:
            if next((e for e in uniq_edges if edge.is_same_edge(e)), None):
                continue
            uniq_edges.append(edge)
        return uniq_edges
