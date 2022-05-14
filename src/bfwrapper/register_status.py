from typing import Optional, Union
from snapshot_pattern import SnapshotPattern
from bf_wrapper_types import SnapshotPatternDict, RegisterStatusDict


class RegisterStatus:
    """Register snapshot status"""

    def __init__(
        self,
        network: str,
        snapshot: str,
        status_str: str,
        snapshot_pattern: Optional[Union[SnapshotPattern, SnapshotPatternDict]] = None,
    ) -> None:
        """Constructor
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            status_str (str): Register status string
            snapshot_pattern (Optional[Union[SnapshotPattern, SnapshotPatternDict]]): snapshot pattern
              (if the snapshot is logical)
        """
        self.status = status_str
        self.network = network
        self.snapshot = snapshot
        # for logical snapshot (else/physical: None)
        self.snapshot_pattern = None  # default
        if snapshot_pattern is not None:
            self.snapshot_pattern = self._uniform_snapshot_pattern(snapshot_pattern)

    @staticmethod
    def _uniform_snapshot_pattern(ss_pattern: Union[SnapshotPattern, SnapshotPatternDict]) -> SnapshotPattern:
        """Snapshot pattern dict to object
        Args:
            ss_pattern (Union[SnapshotPattern, SnapshotPatternDict]): Snapshot pattern dict or object
        Returns:
            SnapshotPattern: Snapshot pattern object
        """
        return ss_pattern if isinstance(ss_pattern, SnapshotPattern) else SnapshotPattern(**ss_pattern)

    def to_dict(self) -> RegisterStatusDict:
        """Convert to dict
        Returns:
            RegisterStatusDict: Snapshot pattern dict
        """
        return {
            "status": self.status,
            "network": self.network,
            "snapshot": self.snapshot,
            "snapshot_pattern": self.snapshot_pattern.to_dict(),
        }
