import uuid

class Link:
    def __init__(self, device1, port1, device2, port2, cable_type="Copper Straight-Through"):
        self.id = str(uuid.uuid4())
        self.cable_type = cable_type
        
        self.interface1 = {
            "device_id": device1.id,
            "port": port1
        }
        
        self.interface2 = {
            "device_id": device2.id,
            "port": port2
        }

    def to_dict(self):
        """Exports the link to your requested JSON format."""
        return {
            "id": self.id,
            "cable_type": self.cable_type,
            "interface1": self.interface1,
            "interface2": self.interface2
        }

    def from_dict(self, data):
        """Loads the link from a JSON dictionary."""
        self.id = data.get("id", self.id)
        self.cable_type = data.get("cable_type", self.cable_type)
        self.interface1 = data.get("interface1", self.interface1)
        self.interface2 = data.get("interface2", self.interface2)