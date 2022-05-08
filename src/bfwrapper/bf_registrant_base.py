"""
Definition of BatfishRegistrantBase class
"""
import json
import sys
import re
from os import path
from typing import List, Optional
from pybatfish.client.session import Session
from l1topology_operator_base import L1TopologyOperatorBase
from snapshot_pattern import SnapshotPattern
from register_status import RegisterStatus


class BatfishRegistrantBase(L1TopologyOperatorBase):
    """Base class of batfish registrant"""

    def __init__(self, bf_host: str, configs_dir: str) -> None:
        """Constructor
        Args:
            bf_host (str): Batfish host (URL)
            configs_dir (str): Path of 'configs' directory (contains batfish network/snapshot directories)
        """
        super().__init__()
        self.bf_session = Session(host=bf_host)
        self.configs_dir = configs_dir

    @staticmethod
    def _safe_snapshot_name(snapshot: str) -> str:
        """Convert raw snapshot name to safe name
        Convert raw snapshot name (includes '/') to safe name (replace '/' to '_')
        Args:
            snapshot (str): Snapshot name
        Returns:
            str: safe snapshot name
        """
        return snapshot.replace("/", "_")

    def _snapshot_dir(self, network: str, snapshot: str) -> str:
        """Get snapshot directory path
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            str: snapshot directory path (configs_dir/network/snapshot)
        """
        return path.join(self.configs_dir, network, snapshot)

    def _snapshot_base_dir(self, network: str) -> str:
        """Get snapshot base directory path
        Args:
            network (str): Network name
        Returns:
              str: snapshot base directory path (configs_dir/network)
        """
        return path.join(self.configs_dir, network)

    @staticmethod
    def _snapshot_dir_path_to_names(network: str, snapshot_dir_path: str) -> List[str]:
        """Convert snapshot directory path to snapshot directory path elements
        Args:
            network (str): Network name
            snapshot_dir_path (str): snapshot directory path
        Returns:
            List[str]: snapshot directory elements
        Examples:
            input: network="networkA", snapshot_dir_path="configs/networkA/foo/bar"
            returns: ["foo", "bar"]
        """
        nw_index = snapshot_dir_path.split("/").index(network)
        # Notice: "network/snapshot" pattern and "network/snapshot_a/snapshot_b" pattern exists
        # returns 2 or3 elements array
        return snapshot_dir_path.split("/")[nw_index:]

    def _find_all_physical_snapshots(self, network: str) -> List[List[str]]:
        """Find all physical snapshots under `network` directory
        Args:
            network (str): network name
        Returns:
            List[List[str]]: physical snapshot path elements ([[network, snapshot1], [network, snapshot2], ...])
        """
        l1topology_files = self._find_all_l1topology_files(self._snapshot_base_dir(network))
        snapshot_dir_paths = [self._detect_snapshot_dir_path(f) for f in l1topology_files]
        return [self._snapshot_dir_path_to_names(network, p) for p in snapshot_dir_paths]

    def _find_all_logical_snapshots(self, phy_snapshots: List[List[str]]) -> List[List[str]]:
        """Find all logical snapshots in each physical snapshot
        Args:
            phy_snapshots (List[List[str]]): List of snapshot path elements
        Returns:
            List[List[str]]: logical snapshot path elements ([[network, snapshot1], [network, snapshot2], ...])
        """
        logical_snapshots = []
        for phy_snapshot in phy_snapshots:
            network = phy_snapshot[0]
            snapshot = path.join(*phy_snapshot[1:])
            snapshot_dir = self._snapshot_dir(network, snapshot)
            if not path.exists(path.join(snapshot_dir, "snapshot_patterns.json")):
                continue
            snapshot_patterns = self._read_snapshot_patterns(network, snapshot)
            logical_snapshots = logical_snapshots + [[network, e.target_snapshot_name] for e in snapshot_patterns]
        return logical_snapshots

    def snapshots_in_network(self, network: str) -> List[List[str]]:
        """Get physical and logical snapshots in the network
        Args:
            network (str): Network name
        Returns:
            List[List[str]]: physical and logical snapshot elements
        """
        phy_snapshots = self._find_all_physical_snapshots(network)
        log_snapshots = self._find_all_logical_snapshots(phy_snapshots)
        return phy_snapshots + log_snapshots

    @staticmethod
    def _detect_physical_snapshot_name(snapshot: str) -> str:
        """Get physical snapshot name from logical snapshot name
        Args:
            snapshot (str): Logical snapshot name
        Returns:
            str: Physical snapshot name
        Note:
            be changed naming rule of logical snapshot
        """
        return re.sub(r"_(linkdown|drawoff).*", "", snapshot)

    def _detect_physical_snapshot_dir(self, network: str, snapshot: str) -> str:
        """Get physical snapshot directory path
        Args:
            network (str): Network name
            snapshot (str): Physical or logical snapshot name
        Returns:
            str: physical snapshot directory path
        """
        if self._is_physical_snapshot(network, snapshot):
            return self._snapshot_dir(network, snapshot)
        return self._snapshot_dir(network, self._detect_physical_snapshot_name(snapshot))

    def _read_snapshot_patterns(self, network: str, snapshot: str) -> List[SnapshotPattern]:
        """Read snapshot patterns file
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            List[SnapshotPattern]: snapshot pattern if it exists in snapshot directory, else empty list.
        """
        snapshot_dir = self._detect_physical_snapshot_dir(network, snapshot)
        snapshot_patterns_path = path.join(snapshot_dir, "snapshot_patterns.json")
        if not path.exists(snapshot_patterns_path):
            print(f"Error: cannot find snapshot_patterns.json in {snapshot_dir}", file=sys.stderr)
            return []

        with open(snapshot_patterns_path, "r", encoding="utf-8") as file:
            try:
                snapshot_pattern_dicts = json.load(file)
                return [SnapshotPattern(**ptn) for ptn in snapshot_pattern_dicts]
            except json.JSONDecodeError as err:
                print(f"Error: cannot read snapshot_patterns.json in {snapshot_dir} with: {err}", file=sys.stderr)
                return []

    def _find_snapshot_pattern(self, network: str, snapshot: str) -> [SnapshotPattern, None]:
        """Find specified snapshot pattern data
        Args:
            network (str): Network name to find
            snapshot (str): Snapshot name to find
        Returns:
            SnapshotPattern: Found snapshot pattern or None if not found
        """
        snapshot_patterns = self._read_snapshot_patterns(network, snapshot)
        return next((s for s in snapshot_patterns if s.target_snapshot_name == snapshot), None)

    def _is_physical_snapshot(self, network: str, snapshot: str) -> bool:
        """Test specified snapshot is physical or not
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            bool: true if the snapshot is physical
        """
        # asked with snapshot name (multi-level snapshot directory name, ex: foo/bar)
        if "/" in snapshot:
            return path.exists(self._snapshot_dir(network, snapshot))

        # asked with batfish-stored snapshot name (safe-snapshot-name, ex: foo_bar)
        physical_snapshots = [
            "/".join([s[0], self._safe_snapshot_name("/".join(s[1:]))])
            for s in self._find_all_physical_snapshots(network)
        ]
        return f"{network}/{snapshot}" in physical_snapshots

    def _register_physical_snapshot(self, network: str, snapshot: str) -> RegisterStatus:
        """Register physical snapshot
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            RegisterStatus: Register status
        """
        safe_snapshot = self._safe_snapshot_name(snapshot)
        print(f"# - Register physical snapshot {network}/{snapshot}")
        self.bf_session.set_network(network)
        self.bf_session.init_snapshot(self._snapshot_dir(network, snapshot), name=safe_snapshot, overwrite=True)
        self.bf_session.set_snapshot(safe_snapshot)
        return RegisterStatus(network, snapshot, "registered")

    def _fork_physical_snapshot(
        self, network: str, snapshot: str, snapshot_pattern: SnapshotPattern
    ) -> RegisterStatus:
        """Fork logical snapshot from origin snapshot
        Args:
            network (str): Network name
            snapshot (str): Snapshot name (logical)
            snapshot_pattern (SnapshotPattern): Snapshot pattern of the logical snapshot
        Returns:
            RegisterStatus: Register status
        """
        origin_ss = snapshot_pattern.orig_snapshot_name
        target_ss = snapshot_pattern.target_snapshot_name  # == snapshot (argument of this function)
        # check if origin snapshot exists? register if it does not found.
        if not self._is_bf_loaded_snapshot(network, origin_ss):
            return self._register_physical_snapshot(network, origin_ss)

        # fork snapshot
        print(f"# - Fork physical snapshot {network}/{origin_ss} -> {target_ss}")
        self.bf_session.set_network(network)
        self.bf_session.fork_snapshot(
            origin_ss,
            target_ss,
            deactivate_interfaces=snapshot_pattern.deactivate_interfaces(),
            overwrite=True,
        )
        self.bf_session.set_snapshot(snapshot_pattern.target_snapshot_name)
        return RegisterStatus(network, snapshot, "forked", snapshot_pattern)

    def register_snapshot(self, network: str, snapshot: str, overwrite: Optional[bool] = False) -> RegisterStatus:
        """Register snapshot
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            overwrite (Optional[bool]): True to enable overwrite snapshot in batfish
        Returns:
             RegisterStatus: Register status (includes snapshot pattern data for logical snapshot registration)
        """
        print(
            f"# Register snapshot: {network} / {snapshot} ",
            f"as {self._safe_snapshot_name(snapshot)} (overwrite={overwrite})",
        )
        # unregister logical snapshots without target snapshot (physical snapshots are kept)
        self.unregister_snapshots_exclude(network, snapshot)

        if not overwrite and self._is_bf_loaded_snapshot(network, snapshot):
            snapshot_pattern = self._find_snapshot_pattern(network, snapshot)
            return RegisterStatus(network, snapshot, "already_exists", snapshot_pattern)

        # if "physical" = orig snapshot (exist snapshot directory/files)
        if self._is_physical_snapshot(network, snapshot):
            return self._register_physical_snapshot(network, snapshot)

        # else: search snapshot pattern to fork physical snapshot
        snapshot_pattern = self._find_snapshot_pattern(network, snapshot)
        if snapshot_pattern is None:
            return RegisterStatus(network, snapshot, "pattern_not_found")
        # fork snapshot
        return self._fork_physical_snapshot(network, snapshot, snapshot_pattern)

    def unregister_snapshots_exclude(self, network: str, snapshot: str) -> None:
        """Unregister snapshot exclude specified snapshot
        Args:
            network (str): Network name to keep
            snapshot (str): Snapshot name to keep
        Returns:
            None
        """
        unreg_snapshots = [s for s in self.bf_snapshots(network) if s != self._safe_snapshot_name(snapshot)]
        print(f"# - keep: {snapshot}, unregister: {unreg_snapshots}")
        for unreg_snapshot in unreg_snapshots:
            self.unregister_snapshot(network, unreg_snapshot)

    def unregister_snapshot(self, network: str, snapshot: str) -> None:
        """Unregister snapshot
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            None
        Note:
            Keep (do not remove) snapshot if the snapshot is physical
        """
        if self._is_physical_snapshot(network, snapshot):
            return  # keep physical (origin) snapshot
        if self._is_bf_loaded_snapshot(network, snapshot):
            self.bf_session.set_network(network)
            self.bf_session.delete_snapshot(snapshot)

    def bf_networks(self) -> List[str]:
        """Get networks in batfish
        Returns:
            List[str]: List of network name in batfish
        """
        return self.bf_session.list_networks()

    def bf_snapshots(self, network: str) -> List[str]:
        """Get snapshots of network in batfish
        Args:
            network (str): Network name
        Returns:
            List[str]: List of snapshot names of the network in batfish
        """
        # Notice: safe guard for bf.set_network():
        # if exec `set_network("unknown-network")`, it makes NEW network in batfish...
        if not self._is_bf_loaded_network(network):
            return []
        self.bf_session.set_network(network)
        return self.bf_session.list_snapshots()

    def _is_bf_loaded_network(self, network: str) -> bool:
        """Test if the network is registered in batfish
        Args:
            network (str): Network name
        Returns:
            bool: True if the network is registered
        """
        return network in self.bf_networks()

    def _is_bf_loaded_snapshot(self, network: str, snapshot: str) -> bool:
        """Test if the snapshot is registered in batfish
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            bool: True if the network/snapshot is registered
        """
        if not self._is_bf_loaded_network(network):
            return False
        return snapshot in self.bf_snapshots(network)
