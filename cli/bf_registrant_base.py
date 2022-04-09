import glob
import json
import sys
import re
from pybatfish.client.session import Session
from pybatfish.datamodel.primitives import Interface
from os import path
from pathlib import Path


class BatfishRegistrantBase:
    def __init__(self, bf_host, mddo_configs_dir):
        self.bf = Session(host=bf_host)
        self.configs_dir = mddo_configs_dir

    @staticmethod
    def _safe_snapshot_name(snapshot):
        return snapshot.replace("/", "_")

    def bf_session(self):
        return self.bf

    def _snapshot_dir(self, network, snapshot):
        return path.join(self.configs_dir, network, snapshot)

    def _snapshot_base_dir(self, network):
        return path.join(self.configs_dir, network)

    @staticmethod
    def _detect_snapshot_dir_by_l1topo(l1topo_path):
        l1path = Path(l1topo_path)
        if l1path.parent.name == "batfish":
            return str(l1path.parent.parent)
        else:
            return str(l1path.parent)

    @staticmethod
    def _snapshot_dir_path_to_names(network, snapshot_dir_path):
        nw_index = snapshot_dir_path.split("/").index(network)
        # Notice: "network/snapshot" pattern and "network/snapshot_a/snapshot_b" pattern exists
        # returns 2 or3 elements array
        return snapshot_dir_path.split("/")[nw_index:]

    @staticmethod
    def _find_all_l1topology_files(dir_path):
        return sorted(glob.glob("%s/**/layer1_topology.json" % dir_path, recursive=True))

    def _find_all_physical_snapshots(self, network):
        l1topology_files = self._find_all_l1topology_files(self._snapshot_base_dir(network))
        snapshot_dir_paths = list(map(lambda f: self._detect_snapshot_dir_by_l1topo(f), l1topology_files))
        # [[network, snapshot1], [network, snapshot2], ...]
        return list(map(lambda p: self._snapshot_dir_path_to_names(network, p), snapshot_dir_paths))

    def _find_all_logical_snapshots(self, phy_snapshots):
        logical_snapshots = []
        for phy_snapshot in phy_snapshots:
            network = phy_snapshot[0]
            snapshot = path.join(*phy_snapshot[1:])
            snapshot_dir = self._snapshot_dir(network, snapshot)
            if not path.exists(path.join(snapshot_dir, "snapshot_patterns.json")):
                continue
            snapshot_patterns = self._read_snapshot_patterns(network, snapshot)
            logical_snapshots = logical_snapshots + list(
                map(lambda e: [network, e["target_snapshot_name"]], snapshot_patterns)
            )
        return logical_snapshots

    def snapshots_in_network(self, network):
        phy_snapshots = self._find_all_physical_snapshots(network)
        log_snapshots = self._find_all_logical_snapshots(phy_snapshots)
        return phy_snapshots + log_snapshots

    @staticmethod
    def _detect_physical_snapshot_name(snapshot):
        return re.sub(r"_(linkdown|drawoff).*", "", snapshot)

    def _detect_physical_snapshot_dir(self, network, snapshot):
        if self._is_physical_snapshot(network, snapshot):
            return self._snapshot_dir(network, snapshot)
        return self._snapshot_dir(network, self._detect_physical_snapshot_name(snapshot))

    def _read_snapshot_patterns(self, network, snapshot):
        snapshot_dir = self._detect_physical_snapshot_dir(network, snapshot)
        snapshot_patterns_path = path.join(snapshot_dir, "snapshot_patterns.json")
        if not path.exists(snapshot_patterns_path):
            print("Error: cannot find snapshot_patterns.json in %s" % snapshot_dir, file=sys.stderr)
            return []

        with open(snapshot_patterns_path, "r") as file:
            try:
                return json.load(file)
            except Exception as err:
                print("Error: cannot read snapshot_patterns.json in %s with: %s" % (snapshot_dir, err), file=sys.stderr)
                return []

    def _find_snapshot_pattern(self, network, snapshot):
        snapshot_patterns = self._read_snapshot_patterns(network, snapshot)
        return next(filter(lambda s: s["target_snapshot_name"] == snapshot, snapshot_patterns), None)

    def _is_physical_snapshot(self, network, snapshot):
        # asked with snapshot name (multi-level snapshot directory name, ex: foo/bar)
        if "/" in snapshot:
            return path.exists(self._snapshot_dir(network, snapshot))

        # asked with batfish-stored snapshot name (safe-snapshot-name, ex: foo_bar)
        physical_snapshots = list(
            map(
                lambda s: "/".join([s[0], self._safe_snapshot_name("/".join(s[1:]))]),
                self._find_all_physical_snapshots(network),
            )
        )
        return "%s/%s" % (network, snapshot) in physical_snapshots

    @staticmethod
    def _edge_node2interface(node):
        return Interface(hostname=node["hostname"], interface=node["interfaceName"])

    def _deactivate_interfaces(self, snapshot_pattern):
        interfaces = []
        for edge in snapshot_pattern["lost_edges"]:
            interfaces.append(self._edge_node2interface(edge["node1"]))
            interfaces.append(self._edge_node2interface(edge["node2"]))
        return interfaces

    def _register_physical_snapshot(self, network, snapshot):
        safe_snapshot = self._safe_snapshot_name(snapshot)
        print("# - Register physical snapshot %s/%s" % (network, snapshot))
        self.bf.set_network(network)
        self.bf.init_snapshot(self._snapshot_dir(network, snapshot), name=safe_snapshot, overwrite=True)
        self.bf.set_snapshot(safe_snapshot)
        return self._register_status(network, snapshot, "registered")

    def _fork_physical_snapshot(self, network, snapshot, snapshot_pattern):
        origin_ss = snapshot_pattern["orig_snapshot_name"]
        target_ss = snapshot_pattern["target_snapshot_name"]  # == snapshot (argument of this function)
        # check if origin snapshot exists? register if it does not found.
        if not self._find_bf_snapshot(network, origin_ss):
            return self._register_physical_snapshot(network, origin_ss)

        # fork snapshot
        print("# - Fork physical snapshot %s/%s -> %s" % (network, origin_ss, target_ss))
        self.bf.set_network(network)
        self.bf.fork_snapshot(
            origin_ss,
            target_ss,
            deactivate_interfaces=self._deactivate_interfaces(snapshot_pattern),
            overwrite=True,
        )
        self.bf.set_snapshot(snapshot_pattern["target_snapshot_name"])
        return self._register_status(network, snapshot, "forked", snapshot_pattern)

    @staticmethod
    def _register_status(network, snapshot, status_str, snapshot_pattern=None):
        return {
            "status": status_str,
            "network": network,
            "snapshot": snapshot,
            "snapshot_pattern": snapshot_pattern,  # for logical snapshot (else/physical: None)
        }

    def register_snapshot(self, network, snapshot, overwrite=False):
        """
        returns snapshot_pattern data for logical snapshot registration
        """
        print(
            "# Register snapshot: %s / %s as %s (overwrite=%s)"
            % (network, snapshot, self._safe_snapshot_name(snapshot), overwrite),
        )
        # unregister logical snapshots without target snapshot (physical snapshots are kept)
        self.unregister_snapshots_exclude(network, snapshot)

        if not overwrite and self._is_bf_loaded_snapshot(network, snapshot):
            snapshot_pattern = self._find_snapshot_pattern(network, snapshot)
            return self._register_status(network, snapshot, "already_exists", snapshot_pattern)

        # if "physical" = orig snapshot (exist snapshot directory/files)
        if self._is_physical_snapshot(network, snapshot):
            return self._register_physical_snapshot(network, snapshot)

        # else: search snapshot pattern to fork physical snapshot
        snapshot_pattern = self._find_snapshot_pattern(network, snapshot)
        if snapshot_pattern is None:
            return self._register_status(network, snapshot, "pattern_not_found")
        # fork snapshot
        return self._fork_physical_snapshot(network, snapshot, snapshot_pattern)

    def unregister_snapshots_exclude(self, network, snapshot):
        unreg_snapshots = list(filter(lambda s: s != self._safe_snapshot_name(snapshot), self.bf_snapshots(network)))
        print("# - keep: %s, unregister: %s" % (snapshot, unreg_snapshots))
        for snapshot in unreg_snapshots:
            self.unregister_snapshot(network, snapshot)

    def unregister_snapshot(self, network, snapshot):
        if self._is_physical_snapshot(network, snapshot):
            return  # keep physical (origin) snapshot
        if self._is_bf_loaded_snapshot(network, snapshot):
            self.bf.set_network(network)
            self.bf.delete_snapshot(snapshot)

    def bf_networks(self):
        return self.bf.list_networks()

    def bf_snapshots(self, network):
        self.bf.set_network(network)
        return self.bf.list_snapshots()

    def _bf_snapshots_table(self):
        snapshots = []
        for network in self.bf_networks():
            for snapshot in self.bf_snapshots(network):
                snapshots.append({"network": network, "snapshot": snapshot})
        return snapshots

    def _find_bf_snapshot(self, network, snapshot):
        return next(
            filter(
                lambda s: s["network"] == network and s["snapshot"] == self._safe_snapshot_name(snapshot),
                self._bf_snapshots_table(),
            ),
            None,
        )

    def _is_bf_loaded_network(self, network):
        return network in self.bf_networks()

    def _is_bf_loaded_snapshot(self, network, snapshot):
        if not self._is_bf_loaded_network(network):
            return False
        return snapshot in self.bf_snapshots(network)
