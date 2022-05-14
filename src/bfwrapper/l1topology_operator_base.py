import glob
from pathlib import Path
from typing import List


class L1TopologyOperatorBase:
    def __init__(self):
        pass

    @staticmethod
    def _find_all_l1topology_files(dir_path: str) -> List[str]:
        """Find all layer1_topology.json recursively under specified directory
        Args:
            dir_path (str): Directory path to search
        Returns:
            List[str]: found layer1_topology.json files
        """
        return sorted(glob.glob(f"{dir_path}/**/layer1_topology.json", recursive=True))

    @staticmethod
    def _detect_snapshot_dir_path(l1topo_path: str) -> str:
        """Get snapshot directory path from layer1 topology file path
        Args:
            l1topo_path (str): layer1_topology.json path
        Returns:
            str: snapshot directory path
        """
        l1path = Path(l1topo_path)
        if l1path.parent.name == "batfish":
            return str(l1path.parent.parent)
        return str(l1path.parent)
