import glob
import json
import pandas as pd
import sys
from os import path
from pathlib import Path


class L1TopologyOperator:
    def __init__(self, configs_dir, network, snapshot):
        self.configs_dir = configs_dir
        self.snapshot_dir_path = path.expanduser(path.join(configs_dir, network, snapshot))
        self.network = network
        self.snapshot = snapshot
        self._load_l1_topology()

    def _load_l1_topology(self):
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
                "# Error: layer1_topology.json not found or found multiple in directory %s" % self.snapshot_dir_path,
                file=sys.stderr,
            )
            sys.exit(1)

        # read layer1 topology data
        self.l1_topology_file = l1_topology_files[0]
        self.l1_topology_data = self._read_l1_topology_data(path.dirname(l1_topology_files[0]))
        # The layer1_topology.json can be found either in the snapshot directory or in the snapshot/batfish directory.
        # So it needs to identify the location and identify the snapshot directory.
        self.snapshot_dir_path = self._detect_snapshot_dir_path(self.l1_topology_file)
        print("# input : snapshot dir: %s" % self.snapshot_dir_path)

    def edges(self):
        return self.l1_topology_data["edges"]

    # edges : origin edges
    # drawoff_edges : eliminate edges from origin edges
    def filter_edges(self, edges, drawoff_edges):
        found_edges = []
        for edge in edges:  # edges = self.edges() = l1_topology_data["edges"]
            if next(filter(lambda e: self._is_same_edge(edge, e), drawoff_edges), None):
                continue
            found_edges.append(edge)
        return found_edges

    @staticmethod
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

    @staticmethod
    def _find_all_l1topology_files(dir_path):
        return sorted(glob.glob("%s/**/layer1_topology.json" % dir_path, recursive=True))

    @staticmethod
    def _read_l1_topology_data(dir_path):
        with open(path.join(dir_path, "layer1_topology.json"), "r") as file:
            try:
                return json.load(file)
            except Exception as err:
                print(
                    "Error: cannot read layer1_topology.json in %s with: %s" % (dir_path, err),
                    file=sys.stderr,
                )
                sys.exit(1)

    def _deduplicate_edges(self, edges):
        uniq_edges = []
        for edge in edges:
            if next((e for e in uniq_edges if self._is_same_edge(e, edge)), None):
                continue
            uniq_edges.append(edge)
        return uniq_edges

    @staticmethod
    def _detect_snapshot_dir_path(l1topo_path):
        l1path = Path(l1topo_path)
        if l1path.parent.name == "batfish":
            return str(l1path.parent.parent)
        else:
            return str(l1path.parent)

    @staticmethod
    def _reverse_edge(edge):
        return {"node1": edge["node2"], "node2": edge["node1"]}

    @staticmethod
    def _is_unidirectional_same_edge(edge1, edge2):
        return (
            edge1["node1"]["hostname"].lower() == edge2["node1"]["hostname"].lower()
            and edge1["node1"]["interfaceName"].lower() == edge2["node1"]["interfaceName"].lower()
            and edge1["node2"]["hostname"].lower() == edge2["node2"]["hostname"].lower()
            and edge1["node2"]["interfaceName"].lower() == edge2["node2"]["interfaceName"].lower()
        )

    def _is_same_edge(self, edge1, edge2):
        return self._is_unidirectional_same_edge(edge1, edge2) or self._is_unidirectional_same_edge(
            self._reverse_edge(edge1), edge2
        )

    @staticmethod
    def _edge2tuple(edge):
        return (
            edge["node1"]["hostname"],
            edge["node1"]["interfaceName"],
            edge["node2"]["hostname"],
            edge["node2"]["interfaceName"],
        )
