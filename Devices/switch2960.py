from device import Device
from interface import Interface

class Switch2960(Device):
    def __init__(self, name):
        super().__init__(name, "Switch")
        self.current_range = []
        
        for i in range(1, 25):
            n = f"fastEthernet 0/{i}"
            self.interfaces[n] = Interface(n)
        for i in range(1, 3):
            n = f"gigabitEthernet 0/{i}"
            self.interfaces[n] = Interface(n)
            
        self.interfaces["Vlan1"] = Interface("Vlan1")

    def process_command(self, cmd_line):
        parts = cmd_line.strip().lower().split()
        if not parts: return ""

        if self.cli_mode == 2:
            if parts[0:2] == ["ip", "default-gateway"]:
                self.config["default-gateway"] = parts[2]
                return ""
            
            if parts[0:2] == ["interface", "range"]:
                try:
                    prefix = parts[2]
                    start_end = parts[3].split("/")[-1].split("-") # "1-10"
                    start, end = int(start_end[0]), int(start_end[1])
                    self.current_range = [f"{prefix} 0/{i}" for i in range(start, end + 1)]
                    self.cli_mode = 4
                    return f"{self.hostname}(config-if-range)#"
                except:
                    return "% Incomplete command or invalid range."

            if parts[0:2] == ["interface", "vlan"]:
                self.cli_mode = 4
                self.current_interface = "Vlan1"
                self.current_range = []
                return f"{self.hostname}(config-if)#"

        if self.cli_mode == 4:
            if parts[0:2] == ["ip", "address"]:
                target = self.current_interface if not self.current_range else ""
                if target == "Vlan1":
                    self.interfaces["Vlan1"].ip = parts[2]
                    self.interfaces["Vlan1"].subnet = parts[3]
                    return ""
                else:
                    return "% IP addresses may not be configured on physical interfaces.\n"

            if "shutdown" in parts:
                status = False if parts[0] == "shutdown" else True
                targets = self.current_range if self.current_range else [self.current_interface]
                for t in targets:
                    if t in self.interfaces: self.interfaces[t].is_up = status
                return ""

        return super().process_command(cmd_line)

    def to_dict(self):
        return {
            "name": self.name, "id": self.id, "type": self.type, "hostname": self.hostname,
            "_x": getattr(self, "_x", 0), "_y": getattr(self, "_y", 0),
            "mac": getattr(self, "mac", "00:00:00:00:00:00"),
            "config": self.config,
            "interfaces": [{n: i.to_dict()} for n, i in self.interfaces.items()]
        }

    def from_dict(self, data):
        super().from_dict(data)
        for entry in data.get("interfaces", []):
            for n, d in entry.items():
                if n in self.interfaces: self.interfaces[n].from_dict(d)