import ipaddress
from pydantic import BaseModel, model_validator, field_validator
from typing import List, Dict, Optional

VALID_PORTS = {
    "Router": ["g0/0", "g0/1", "g0/2"],
    "Switch": [f"fa0/{i}" for i in range(1, 25)] + ["g0/1", "g0/2"],
    "PC": ["fa0"],
    "Laptop": ["fa0"],
    "Server": ["fa0"]
}

class DeviceModel(BaseModel):
    id: str
    type: str
    interfaces: Optional[Dict[str, str]] = None
    gateway: Optional[str] = None
    dhcp: Optional[Dict] = None

    @field_validator("interfaces")
    def validate_ports_and_ips(cls, v, info):
        if not v:
            return v
            
        dev_type = info.data.get("type", "Unknown")
        allowed = VALID_PORTS.get(dev_type, [])

        for port, cidr in v.items():
            if port not in allowed:
                raise ValueError(f"{dev_type} cannot use port {port}")
            try:
                ipaddress.IPv4Interface(cidr)
            except ValueError:
                raise ValueError(f"Invalid IP/Subnet format on port {port}: {cidr}")
        return v

class TopologyModel(BaseModel):
    devices: List[DeviceModel]
    links: List[List[str]]

    @model_validator(mode="after")
    def validate_graph_connectivity(self):
        if not self.devices:
            return self

        graph = {d.id: set() for d in self.devices}

        for link in self.links or []:
            (a_dev, a_port), (b_dev, b_port) = [x.split(":") for x in link]
            if a_dev in graph and b_dev in graph:
                graph[a_dev].add(b_dev)
                graph[b_dev].add(a_dev)

        start = self.devices[0].id
        visited = set([start])
        queue = [start]

        while queue:
            node = queue.pop()
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if len(visited) != len(self.devices):
            raise ValueError(f"Topology is disconnected: only {len(visited)}/{len(self.devices)} reachable")

        return self
