import random

class Interface:
    def __init__(self, name, is_console=False):
        self.name = name
        self.is_console = is_console
        self.ip = ""
        self.subnet = ""
        self.description = "atentiune!"
        self.is_up = True  # Statusul administrativ (shutdown/no shutdown)
        self.speed = self._determine_speed(name)
        self.mac = self._generate_mac() if not is_console else ""

    def _determine_speed(self, name):
        n = name.lower()
        if "gigabit" in n: return "1Gbps"
        if "fast" in n: return "100Mbps"
        if "vlan" in n: return "Virtual"
        if "serial" in n or "console" in n or "rs232" in n: return "9600bps"
        return "10Mbps"

    def _generate_mac(self):
        h = [f"{random.randint(0, 255):02X}" for _ in range(3)]
        return f"08:0B:AC:{h[0]}:{h[1]}:{h[2]}:AS:FA"

    def to_dict(self):
        return {
            "ip": self.ip,
            "subnet": self.subnet,
            "description": self.description,
            "is_up": self.is_up,
            "mac": self.mac,
            "speed": self.speed,
            "is_console": self.is_console
        }

    def from_dict(self, data):
        self.ip = data.get("ip", "")
        self.subnet = data.get("subnet", "")
        self.description = data.get("description", "atentiune!")
        self.is_up = data.get("is_up", True)
        self.mac = data.get("mac", self.mac)
        self.speed = data.get("speed", self.speed)
        self.is_console = data.get("is_console", self.is_console)