from device import Device
from interface import Interface

class Router2911(Device):
    def __init__(self, name):
        super().__init__(name, "Router")
        
        for i in range(3):
            n = f"gigabitEthernet 0/{i}"
            self.interfaces[n] = Interface(n)

        if "dhcp_pools" not in self.config: 
            self.config["dhcp_pools"] = {}
        if "dhcp_excluded" not in self.config: 
            self.config["dhcp_excluded"] = []
        if "routes" not in self.config: 
            self.config["routes"] = []
            
        self.current_dhcp_pool = None

    def get_prompt(self):
        if getattr(self, "cli_mode", 0) == 5:
            return f"{self.hostname}(dhcp-config)#"
        return super().get_prompt()

    def process_command(self, cmd_line):
        parts = cmd_line.strip().split()
        if not parts: return ""
        cmd_lower = [p.lower() for p in parts]

        if self.cli_mode == 2:
            
            if cmd_lower[0:3] == ["ip", "dhcp", "excluded-address"] and len(parts) >= 4:
                exclusion = parts[3] + (" " + parts[4] if len(parts) > 4 else "")
                if exclusion not in self.config["dhcp_excluded"]:
                    self.config["dhcp_excluded"].append(exclusion)
                return ""

            elif cmd_lower[0:3] == ["ip", "dhcp", "pool"] and len(parts) >= 4:
                pool_name = parts[3] # Numele pool-ului rămâne case-sensitive
                if pool_name not in self.config["dhcp_pools"]:
                    self.config["dhcp_pools"][pool_name] = {}
                
                self.current_dhcp_pool = pool_name
                self.cli_mode = 5
                return ""

            elif cmd_lower[0:2] == ["ip", "route"] and len(parts) >= 5:
                route = {
                    "network": parts[2],
                    "mask": parts[3],
                    "next_hop": parts[4] 
                }
                self.config["routes"].append(route)
                return ""

        elif self.cli_mode == 5:
            if cmd_lower[0] == "exit":
                self.cli_mode = 2
                self.current_dhcp_pool = None
                return ""
                
            elif cmd_lower[0] == "default-router" and len(parts) >= 2:
                self.config["dhcp_pools"][self.current_dhcp_pool]["default-router"] = parts[1]
                return ""
            elif cmd_lower[0] == "dns-server" and len(parts) >= 2:
                self.config["dhcp_pools"][self.current_dhcp_pool]["dns-server"] = parts[1]
                return ""
            elif cmd_lower[0] == "domain-name" and len(parts) >= 2:
                self.config["dhcp_pools"][self.current_dhcp_pool]["domain-name"] = parts[1]
                return ""
            elif cmd_lower[0] == "network" and len(parts) >= 3:
                self.config["dhcp_pools"][self.current_dhcp_pool]["network"] = parts[1]
                self.config["dhcp_pools"][self.current_dhcp_pool]["mask"] = parts[2]
                return ""

        elif self.cli_mode == 4:
            
            if cmd_lower[0:2] == ["ip", "address"] and len(parts) >= 4:
                if self.current_interface in self.interfaces:
                    self.interfaces[self.current_interface].ip = parts[2]
                    self.interfaces[self.current_interface].subnet = parts[3]
                return ""
                
            elif "shutdown" in cmd_lower:
                status = False if cmd_lower[0] == "shutdown" else True
                if self.current_interface in self.interfaces:
                    self.interfaces[self.current_interface].is_up = status
                return ""

        output = super().process_command(cmd_line)
        
        if self.cli_mode != 5:
            self.current_dhcp_pool = None
            
        return output

    def to_dict(self):
        return {
            "name": self.name, "id": self.id, "type": self.type, "hostname": self.hostname,
            "_x": getattr(self, "_x", 0), "_y": getattr(self, "_y", 0),
            "mac": getattr(self, "mac", "00:00:00:00:00:00"),
            "config": self.config,  # DHCP-ul și rutele se salvează automat aici!
            "interfaces": [{n: i.to_dict()} for n, i in self.interfaces.items() if not i.is_console]
        }

    def from_dict(self, data):
        super().from_dict(data) # Acesta încarcă și config-ul
        for entry in data.get("interfaces", []):
            for n, d in entry.items():
                if n in self.interfaces: self.interfaces[n].from_dict(d)