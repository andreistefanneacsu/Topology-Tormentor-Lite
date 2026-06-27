from Devices.devices import Device
from Devices.interface import Interface

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
        parts = cmd_line.strip().split()
        if not parts: return ""
        
        is_no = (parts[0].lower() == "no")
        action_parts = parts[1:] if is_no else parts
        if not action_parts: return ""
        cmd_lower = [p.lower() for p in action_parts]

        if self.cli_mode in (2, 4):
            if cmd_lower[0:2] == ["interface", "range"]:
                try:
                    prefix = action_parts[2]
                    start_end = action_parts[3].split("/")[-1].split("-") 
                    start, end = int(start_end[0]), int(start_end[1])
                    self.current_range = [f"{prefix} 0/{i}" for i in range(start, end + 1)]
                    self.cli_mode = 4
                    return ""
                except:
                    return "% Incomplete command or invalid range."

            if cmd_lower[0:2] == ["interface", "vlan"]:
                self.cli_mode = 4
                self.current_interface = "Vlan1"
                self.current_range = []
                return ""

        if self.cli_mode == 4:
            if cmd_lower[0:2] == ["ip", "address"]:
                if not is_no and len(action_parts) < 4:
                    return "% Incomplete command.\n"
                target = self.current_interface if not self.current_range else ""
                if target == "Vlan1":
                    self.interfaces["Vlan1"].ip = "" if is_no else action_parts[2]
                    self.interfaces["Vlan1"].subnet = "" if is_no else action_parts[3]
                    return ""
                else:
                    return "% IP addresses may not be configured on physical interfaces.\n"

            if "shutdown" in cmd_lower:
                status = is_no # no shutdown = True
                targets = self.current_range if self.current_range else [self.current_interface]
                for t in targets:
                    if t in self.interfaces: self.interfaces[t].is_up = status
                return ""

        return super().process_command(cmd_line)

    def to_dict(self):
        data = super().to_dict()
        data["interfaces"] = [
            {n: i.to_dict()} 
            for n, i in self.interfaces.items()
        ]
        return data

    def from_dict(self, data):
        super().from_dict(data)
        for entry in data.get("interfaces", []):
            for n, d in entry.items():
                if n in self.interfaces: self.interfaces[n].from_dict(d)