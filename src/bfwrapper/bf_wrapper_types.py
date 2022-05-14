from typing import List, Dict, Optional, TypedDict
from l1topology_edge import L1TopologyEdgeDict


class SnapshotPatternDict(TypedDict):
    index: int
    lost_edges: List[L1TopologyEdgeDict]
    orig_snapshot_dir: str
    orig_snapshot_name: str
    source_snapshot_name: str
    target_snapshot_name: str
    description: str


class L1TopologyDict:
    edges: List[L1TopologyEdgeDict]


class RegisterStatusDict(TypedDict):
    status: str
    network: str
    snapshot: str
    snapshot_pattern: Optional[SnapshotPatternDict]


class TracerouteQueryStatus(TypedDict):
    network: str
    snapshot: str
    result: List[Dict]
    snapshot_pattern: Optional[SnapshotPatternDict]


class QuerySummaryDict(TypedDict):
    query: str
    file: str


class WholeQuerySummaryDict(TypedDict):
    network: str
    snapshot: str
    snapshot_dir: str
    models_dir: str
    queries: List[QuerySummaryDict]
    snapshot_pattern: Optional[SnapshotPatternDict]
