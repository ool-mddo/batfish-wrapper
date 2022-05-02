from __future__ import annotations
from re import Pattern
from typing import TypedDict
from pybatfish.datamodel.primitives import Interface


class L1TopologyEdgeTermPointDict(TypedDict):
    hostname: str
    interfaceName: str


class L1TopologyEdgeDict(TypedDict):
    node1: L1TopologyEdgeTermPointDict
    node2: L1TopologyEdgeTermPointDict


class L1TopologyEdgeTermPoint:
    """Termination point (interface) for layer1 topology"""

    def __init__(self, l1tp_dict: L1TopologyEdgeTermPointDict) -> None:
        """Constructor
        Args:
            l1tp_dict (L1TopologyEdgeTermPointDict): Term-point in L1 edge
        """
        self.host = l1tp_dict["hostname"]  # Case-sensitive in layer1_topology.json
        self.intf = l1tp_dict["interfaceName"]

    def __str__(self) -> str:
        """Convert to string
        Returns:
            str: term-point string
        """
        return f"{self.host}[{self.intf}]"

    def to_lower_host_str(self) -> str:
        """Convert to string (use lowercase hostname)
        Returns:
            str: term-point string
        Note:
            lowercase hostname: to make consistent with batfish query output
        """
        return f"{self.host.lower()}[{self.intf}]"

    def __eq__(self, other: L1TopologyEdgeTermPoint) -> bool:
        """Test term-points are same or not
        Returns:
            bool: True if these term-points are same
        Note:
            Host-name comparison is case-insensitive
        """
        return self.host.lower() == other.host.lower() and self.intf == other.intf

    def to_dict(self) -> L1TopologyEdgeTermPointDict:
        """Convert to dict
        Returns:
            L1TopologyEdgeTermPointDict: Term-point dict
        """
        return {"hostname": self.host, "interfaceName": self.intf}

    def to_bf_interface(self) -> Interface:
        """Convert to interface object for batfish
        Returns:
            Interface:Interface object for batfish
        """
        return Interface(hostname=self.host, interface=self.intf)

    def is_match(self, host: str, intf_re: Pattern) -> bool:
        """Test this term-point matches specified host and interface
        Args:
            host (str): Host name (case-insensitive)
            intf_re (Pattern): Interface name (regexp)
        Returns:
            bool: True if match
        """
        return self.host.lower() == host.lower() and intf_re.fullmatch(self.intf)

    def is_equal(self, host: str, intf: str) -> bool:
        """Test this term-point equals specified host and interface
        Args:
            host (str): Host name (case-insensitive)
            intf (str): Interface name (case-sensitive)
        Returns:
            bool: True if equal
        """
        return self.host.lower() == host.lower() and self.intf == intf


class L1TopologyEdge:
    def __init__(self, l1edge_dict: L1TopologyEdgeDict) -> None:
        """Constructor
        Args:
            l1edge_dict (L1TopologyEdgeDict): Edge in L1 topology
        """
        self.node1 = L1TopologyEdgeTermPoint(l1edge_dict["node1"])
        self.node2 = L1TopologyEdgeTermPoint(l1edge_dict["node2"])

    def __str__(self) -> str:
        """Convert to string
        Returns:
            str: Edge string
        """
        return f"{self.node1} <=> {self.node2}"

    def to_lower_host_str(self) -> str:
        """Convert to string
        Returns:
            str: Edge string
        Note:
            lowercase hostname: to make consistent with batfish query output
        """
        return f"{self.node1.to_lower_host_str()} <=> {self.node2.to_lower_host_str()}"

    def __eq__(self, other: L1TopologyEdge) -> bool:
        """Test edges are same or not
        Returns:
            bool: True if these edges are same
        Note:
            Direction-sensitive
        """
        return self.node1 == other.node1 and self.node2 == other.node2

    def is_same_edge(self, other: L1TopologyEdge) -> bool:
        """Test edges are same or not (ignore direction)
        Returns:
            bool: True if these edges are same
        Note:
            Direction-insensitive
        """
        return self == other or self == other.reverse()

    def reverse(self) -> L1TopologyEdge:
        """Return reverse direction edge
        Returns:
            L1TopologyEdge: Reverse edge
        """
        return L1TopologyEdge({"node1": self.node2.to_dict(), "node2": self.node1.to_dict()})

    def to_dict(self) -> L1TopologyEdgeDict:
        """Convert to dict
        Returns:
            L1TopologyEdgeDict: Edge dict
        """
        return {"node1": self.node1.to_dict(), "node2": self.node2.to_dict()}

    def is_match(self, host: str, intf_re: Pattern) -> bool:
        """Test this edge owns a term-point that matches specified host and interface
        Args:
            host (str): Host name
            intf_re (Pattern): Interface name (regexp)
        Returns:
            bool: True if this edge owns a matched edge
        Note:
            Direction-insensitive
        """
        return self.node1.is_match(host, intf_re) or self.node2.is_match(host, intf_re)

    def is_equal(self, host: str, intf: str) -> bool:
        """Test this edge owns a term-point that matches specified host and interface
        Args:
            host (str): Host name
            intf (str): Interface name
        Returns:
            bool: True if this edge owns a equaled edge
        Note:
            Direction-insensitive
        """
        return self.node1.is_equal(host, intf) or self.node2.is_equal(host, intf)
