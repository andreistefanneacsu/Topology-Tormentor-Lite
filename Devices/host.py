import uuid
from interface import Interface

class Host:
    def __init__(self, name, host_type="Host"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.hostname = name
        self.type = host_type
        
        self._x = 0
        self._y = 0
        self.mac = "00:00:00:00:00:00" 
        
        self.config = {
            "default-gateway": ""
        }
        
        self.interfaces = {
            "FastEthernet0": Interface("FastEthernet0")
        }

    def get_prompt(self):
        return r"C:\> "

    def process_command(self, cmd_line):
        parts = cmd_line.strip().split()
        if not parts: return ""
        cmd = parts[0].lower()

        if cmd == "ipconfig":
            if len(parts) >= 3:
                intf = self.interfaces["FastEthernet0"]
                intf.ip, intf.subnet = parts[1], parts[2]
                if len(parts) >= 4: self.config["default-gateway"] = parts[3]
                return "\nIP Configuration updated.\n"
            elif len(parts) == 2 and parts[1].lower() == "/renew":
                return "Requesting IP via DHCP...\n"
            
            intf = self.interfaces["FastEthernet0"]
            gw = self.config.get("default-gateway", "0.0.0.0")
            status = "Up" if intf.is_up else "Down"
            
            return (f"\nFastEthernet0 Connection (Status: {status}):\n"
                    f"   IPv4 Address. . . : {intf.ip or '0.0.0.0'}\n"
                    f"   Subnet Mask . . . : {intf.subnet or '0.0.0.0'}\n"
                    f"   Default Gateway . : {gw or '0.0.0.0'}\n")

        elif cmd == "ping":
            return f"$PING:{parts[1]}$" if len(parts) > 1 else "Usage: ping <ip>\n"
            
        elif cmd == "ssh":
            if len(parts) >= 4 and parts[1] == "-l":
                user = parts[2]
                ip = parts[3]
                return f"\nConnecting to {ip} via SSH...\nPassword: \n"
            return "Usage: ssh -l <username> <ip>\n"
            
        elif cmd == "telnet":
            if len(parts) >= 2:
                ip = parts[1]
                return f"\nTrying {ip}...\nConnected to {ip}.\nUser Access Verification\nPassword: "
            return "Usage: telnet <ip>\n"

        return f"'{parts[0]}' is not recognized as an internal or external command.\n"

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "type": self.type,
            "hostname": self.hostname,
            "_x": self._x,
            "_y": self._y,
            "mac": self.mac,
            "config": self.config,
            "interfaces": [{n: i.to_dict()} for n, i in self.interfaces.items() if getattr(i, 'is_console', False) is False]
        }

    def from_dict(self, data):
        self.id = data.get("id", self.id)
        self.name = data.get("name", self.name)
        self.type = data.get("type", self.type)
        self.hostname = data.get("hostname", self.hostname)
        self._x = data.get("_x", self._x)
        self._y = data.get("_y", self._y)
        self.mac = data.get("mac", self.mac)
        
        config_data = data.get("config", {})
        for key, val in config_data.items():
            self.config[key] = val

        for entry in data.get("interfaces", []):
            for n, d in entry.items():
                if n in self.interfaces:
                    self.interfaces[n].from_dict(d)