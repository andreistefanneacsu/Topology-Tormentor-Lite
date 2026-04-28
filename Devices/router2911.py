from Devices.devices import Device
from Devices.interface import Interface

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
        
        is_no = (parts[0].lower() == "no")
        action_parts = parts[1:] if is_no else parts
        if not action_parts: return ""
        
        cmd_lower = [p.lower() for p in action_parts]

        # --- Modul Global Config ---
        if self.cli_mode == 2:
            if cmd_lower[0:3] == ["ip", "dhcp", "excluded-address"] and len(action_parts) >= 4:
                exclusion = action_parts[3] + (" " + action_parts[4] if len(action_parts) > 4 else "")
                if is_no and exclusion in self.config["dhcp_excluded"]:
                    self.config["dhcp_excluded"].remove(exclusion)
                elif not is_no and exclusion not in self.config["dhcp_excluded"]:
                    self.config["dhcp_excluded"].append(exclusion)
                return ""

            elif cmd_lower[0:3] == ["ip", "dhcp", "pool"] and len(action_parts) >= 4:
                pool_name = action_parts[3] 
                if is_no:
                    self.config["dhcp_pools"].pop(pool_name, None)
                    return ""
                
                if pool_name not in self.config["dhcp_pools"]:
                    self.config["dhcp_pools"][pool_name] = {}
                self.current_dhcp_pool = pool_name
                self.cli_mode = 5 
                return ""

            elif cmd_lower[0:2] == ["ip", "route"] and len(action_parts) >= 5:
                route = {
                    "network": action_parts[2],
                    "mask": action_parts[3],
                    "next_hop": action_parts[4] 
                }
                if is_no:
                    self.config["routes"] = [r for r in self.config["routes"] if r != route]
                else:
                    if route not in self.config["routes"]:
                        self.config["routes"].append(route)
                return ""

        # --- Modul DHCP Config ---
        elif self.cli_mode == 5:
            if cmd_lower[0] == "exit":
                self.cli_mode = 2
                self.current_dhcp_pool = None
                return ""
            
            # Nu vom detalia stergerea parametrilor din pool cu no pentru simplificare
            if cmd_lower[0] == "default-router" and len(action_parts) >= 2:
                self.config["dhcp_pools"][self.current_dhcp_pool]["default-router"] = "" if is_no else action_parts[1]
                return ""
            elif cmd_lower[0] == "dns-server" and len(action_parts) >= 2:
                self.config["dhcp_pools"][self.current_dhcp_pool]["dns-server"] = "" if is_no else action_parts[1]
                return ""
            elif cmd_lower[0] == "domain-name" and len(action_parts) >= 2:
                self.config["dhcp_pools"][self.current_dhcp_pool]["domain-name"] = "" if is_no else action_parts[1]
                return ""
            elif cmd_lower[0] == "network" and len(action_parts) >= 3:
                self.config["dhcp_pools"][self.current_dhcp_pool]["network"] = "" if is_no else action_parts[1]
                self.config["dhcp_pools"][self.current_dhcp_pool]["mask"] = "" if is_no else action_parts[2]
                return ""

        output = super().process_command(cmd_line)
        if getattr(self, 'cli_mode', 0) != 5:
            self.current_dhcp_pool = None
            
        return output

    def to_dict(self):
        data = super().to_dict()
        data["interfaces"] = [
            {n: i.to_dict()} 
            for n, i in self.interfaces.items() 
            if not getattr(i, 'is_console', False)
        ]
        return data

    def from_dict(self, data):
        super().from_dict(data) 
        for entry in data.get("interfaces", []):
            for n, d in entry.items():
                if n in self.interfaces: self.interfaces[n].from_dict(d)