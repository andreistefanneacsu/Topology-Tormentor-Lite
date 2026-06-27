import uuid
import json
import os
import time

class Device:
    def __init__(self, name, dev_type):
        self.id = str(uuid.uuid4())
        self.name = name
        self.hostname = name
        self.type = dev_type
        
        self._x = 0
        self._y = 0
        self.mac_address = "08:0B:AC:13:41:F4:AS:FA"
        
        self.config = {
            "default-gateway": "",
            "domain": "",
            "cdp_run": True,
            "ip_domain_lookup": True,
            "enable_password": "",
            "enable_secret": "",
            "banner_motd": "",
            "banner_login": "",
            "lines": {
                "con 0": {"password": "", "timeout": "0 0"},
                "vty 0 15": {"password": "", "timeout": "0 0", "transport_input": ["all"]}
            },
            "users": {}, 
            "rsa_key_bits": 0,
            "logging_host": "",
            "service_timestamps_log": False,
            "service_timestamps_debug": False,
            "login_block": {"attempts": 0, "within": 0, "block_for": 0},
            "min_password_length": 0,
            "service_password_encryption": False,
            "clock": "" 
        }
        
        self.interfaces = {}
        self.cli_mode = 0
        self.cli_prompt_pending = None
        self.current_interface = None
        self.current_line = None

    def to_dict(self):
        intf_export = {}
        for k, v in self.interfaces.items():
            if hasattr(v, 'to_dict'):
                intf_export[k] = v.to_dict()
            else:
                intf_export[k] = v
                
        return {
            "name": self.name,
            "id": getattr(self, 'id', ""),
            "type": getattr(self, 'type', ""),
            "hostname": self.hostname,
            "_x": getattr(self, '_x', 0),
            "_y": getattr(self, '_y', 0),
            "mac": getattr(self, 'mac_address', "08:0B:AC:13:41:F4:AS:FA"),
            "config": self.config,
            "interfaces": intf_export 
        }
        
    def from_dict(self, data):
        self.id = data.get("id", getattr(self, 'id', ""))
        self.name = data.get("name", getattr(self, 'name', ""))
        self.type = data.get("type", getattr(self, 'type', ""))
        self.hostname = data.get("hostname", getattr(self, 'hostname', ""))
        self._x = data.get("_x", getattr(self, '_x', 0))
        self._y = data.get("_y", getattr(self, '_y', 0))
        self.mac_address = data.get("mac", "08:0B:AC:13:41:F4:AS:FA")
        
        if "config" in data:
            self.config.update(data["config"])
            
        if "routes" in data:
            if "routes" not in self.config:
                self.config["routes"] = []
            for route in data["routes"]:
                if route not in self.config["routes"]:
                    self.config["routes"].append(route)
            
        if "interfaces" in data:
            if isinstance(data["interfaces"], dict):
                for k, v in data["interfaces"].items():
                    if k in self.interfaces:
                        self.interfaces[k].from_dict(v)
                    else:
                        from Devices.interface import Interface
                        new_intf = Interface(k)
                        new_intf.from_dict(v)
                        self.interfaces[k] = new_intf
            elif isinstance(data["interfaces"], list):
                for entry in data["interfaces"]:
                    if "name" in entry:
                        name = entry["name"]
                        resolved_name = self._resolve_interface([name])
                        if not resolved_name:
                            resolved_name = name
                        
                        if resolved_name in self.interfaces:
                            self.interfaces[resolved_name].from_dict(entry)
                        else:
                            from Devices.interface import Interface
                            new_intf = Interface(resolved_name)
                            new_intf.from_dict(entry)
                            self.interfaces[resolved_name] = new_intf
                    else:
                        for n, d in entry.items():
                            if n in self.interfaces:
                                self.interfaces[n].from_dict(d)
                            else:
                                from Devices.interface import Interface
                                new_intf = Interface(n)
                                new_intf.from_dict(d)
                                self.interfaces[n] = new_intf

    def save_device_state(self):
        filename = f"{self.id}.json" 
        try:
            with open(filename, 'w') as f:
                json.dump(self.to_dict(), f, indent=4)
            return True
        except Exception as e:
            return False

    def load_device_state(self):
        filename = f"{self.id}.json"
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            self.from_dict(data)
            return True
        except Exception as e:
            return False

    def get_prompt(self):
        if self.cli_prompt_pending:
            return self.cli_prompt_pending
            
        if self.cli_mode == 0: return f"{self.hostname}>"
        elif self.cli_mode == 1: return f"{self.hostname}#"
        elif self.cli_mode == 2: return f"{self.hostname}(config)#"
        elif self.cli_mode == 3: return f"{self.hostname}(config-line)#"
        elif self.cli_mode == 4: 
            if hasattr(self, 'current_range') and getattr(self, 'current_range'):
                return f"{self.hostname}(config-if-range)#"
            return f"{self.hostname}(config-if)#"
        return f"{self.hostname}>"

    def _handle_unknown_command(self, cmd):
        if self.config.get("ip_domain_lookup", True):
            time.sleep(2)
            return f"Translating \"{cmd}\"...domain server (255.255.255.255)\n% Unknown command or computer name, or unable to find computer address\n"
        return f"% Invalid input detected at '^' marker.\n"

    def _resolve_interface(self, name_parts):
        """Magically converts 'g0/0' to 'gigabitEthernet 0/0'"""
        raw = "".join(name_parts).lower()
        for actual in self.interfaces.keys():
            clean = actual.lower().replace(" ", "")
            if clean.startswith(raw) or clean == raw:
                return actual

            if raw.startswith('g') and 'gigabit' in clean and clean.endswith(raw[1:]): return actual
            if raw.startswith('f') and 'fast' in clean and clean.endswith(raw[1:]): return actual
            if raw.startswith('s') and 'serial' in clean and clean.endswith(raw[1:]): return actual
            
        return None

    def process_command(self, cmd_line):
        cmd = cmd_line.strip()
        if not cmd: return ""
            
        if self.cli_prompt_pending:
            if "bits in the modulus" in self.cli_prompt_pending:
                self.cli_prompt_pending = None
                try:
                    bits = int(cmd)
                    self.config["rsa_key_bits"] = bits
                    return f"OK\nGenerating {bits} bit RSA keys, keys will be non-exportable...\n[OK]\n"
                except:
                    return "% Invalid modulus.\n"
            self.cli_prompt_pending = None
            return ""

        parts = cmd.split()
        first = parts[0].lower()
        is_no = (first == "no")
        
        action_parts = parts[1:] if is_no else parts
        action = action_parts[0].lower() if action_parts else ""

        if first in ("exit", "ex"):
            if self.cli_mode in (3, 4): self.cli_mode = 2; self.current_line = None; self.current_interface = None
            elif self.cli_mode == 2: self.cli_mode = 1
            elif self.cli_mode == 1: self.cli_mode = 0
            return ""

        if self.cli_mode == 0:
            if first.startswith("en"):
                self.cli_mode = 1
                return ""
            return self._handle_unknown_command(first)

        elif self.cli_mode == 1:
            if first.startswith("conf"):
                self.cli_mode = 2
                return "Enter configuration commands, one per line.  End with CNTL/Z.\n"
            elif first == "clock" and len(parts) >= 4 and parts[1] == "set":
                self.config["clock"] = " ".join(parts[2:])
                return ""
            elif first == "copy":
                if len(parts) >= 3:
                    if parts[1].startswith("run") and parts[2].startswith("start"):
                        return "Destination filename [startup-config]? \nBuilding configuration...\n[OK]\n" if self.save_device_state() else "%Error saving\n"
                    elif parts[1].startswith("start") and parts[2].startswith("run"):
                        return "Destination filename [running-config]? \nLoading configuration...\n[OK]\n" if self.load_device_state() else "%Error loading\n"
                return "% Incomplete command.\n"
            return self._handle_unknown_command(first)

        elif self.cli_mode == 2: 
            if action.startswith("host") and len(action_parts) > 1:
                if is_no: 
                    self.hostname = "Router" if self.type == "Router" else "Switch"
                    self.name = self.hostname
                else:
                    self.hostname = action_parts[1]
                    self.name = action_parts[1]
                return ""
                
            elif action == "cdp" and len(action_parts) > 1 and action_parts[1] == "run":
                self.config["cdp_run"] = not is_no
                return ""

            elif action == "ip" and len(action_parts) > 1:
                sub_action = action_parts[1].lower()
                if sub_action == "domain-lookup":
                    self.config["ip_domain_lookup"] = not is_no
                    return ""
                elif sub_action == "domain-name" or sub_action == "domain":
                    self.config["domain"] = "" if is_no else (action_parts[2] if len(action_parts)>2 else "")
                    return ""
                elif sub_action == "default-gateway" and len(action_parts) == 3:
                    self.config["default-gateway"] = "" if is_no else action_parts[2]
                    return ""
                    
            elif action == "enable" and len(action_parts) >= 3:
                if action_parts[1] == "secret": self.config["enable_secret"] = "" if is_no else action_parts[2]
                elif action_parts[1] == "password": self.config["enable_password"] = "" if is_no else action_parts[2]
                return ""
                
            elif action == "banner" and len(action_parts) >= 3:
                banner_type = action_parts[1]
                text = " ".join(action_parts[2:]).strip('^#*"') 
                if banner_type == "motd": self.config["banner_motd"] = "" if is_no else text
                elif banner_type == "login": self.config["banner_login"] = "" if is_no else text
                return ""

            elif action == "username" and len(action_parts) >= 3:
                if is_no:
                    self.config["users"].pop(action_parts[1], None)
                else:
                    user_data = {"privilege": 1, "is_secret": False, "password": ""}
                    uname = action_parts[1]
                    idx = 2
                    if action_parts[idx] == "privilege":
                        user_data["privilege"] = int(action_parts[idx+1])
                        idx += 2
                    if idx < len(action_parts):
                        if action_parts[idx] in ("secret", "password"):
                            user_data["is_secret"] = (action_parts[idx] == "secret")
                            user_data["password"] = action_parts[idx+1]
                    self.config["users"][uname] = user_data
                return ""

            elif action == "line":
                if len(action_parts) >= 3:
                    line_type = action_parts[1] + " " + action_parts[2] 
                    if "vty" in line_type: line_type = "vty 0 15" 
                    if line_type in self.config["lines"]:
                        self.cli_mode = 3
                        self.current_line = line_type
                return ""

            elif action == "crypto" and "key" in action_parts:
                if is_no and "zeroize" in action_parts:
                    self.config["rsa_key_bits"] = 0
                    return "% All RSA keys will be removed.\n"
                elif "generate" in action_parts:
                    if not self.config.get("domain"): return "% Please define a domain-name first.\n"
                    self.cli_prompt_pending = "How many bits in the modulus [512]: "
                    return ""

            elif action == "logging" and len(action_parts) == 2: 
                self.config["logging_host"] = "" if is_no else action_parts[1]
                return ""

            elif action == "service":
                if len(action_parts) >= 3 and action_parts[1] == "timestamps":
                    if action_parts[2] == "log": self.config["service_timestamps_log"] = not is_no
                    if action_parts[2] == "debug": self.config["service_timestamps_debug"] = not is_no
                elif len(action_parts) == 2 and action_parts[1] == "password-encryption":
                    self.config["service_password_encryption"] = not is_no
                return ""
                
            elif action == "login" and "block-for" in action_parts:
                if is_no:
                    self.config["login_block"] = {"attempts": 0, "within": 0, "block_for": 0}
                else:
                    try:
                        bf = int(action_parts[action_parts.index("block-for")+1])
                        at = int(action_parts[action_parts.index("attempts")+1])
                        wi = int(action_parts[action_parts.index("within")+1])
                        self.config["login_block"] = {"attempts": at, "within": wi, "block_for": bf}
                    except: return "% Invalid syntax.\n"
                return ""
                
            elif action == "security" and "passwords" in action_parts and "min-length" in action_parts:
                self.config["min_password_length"] = 0 if is_no else int(action_parts[-1])
                return ""

            elif action.startswith("int") and len(action_parts) > 1:
                resolved = self._resolve_interface(action_parts[1:])
                if resolved:
                    self.cli_mode = 4
                    self.current_interface = resolved
                    return ""
                else:
                    return "% Invalid interface type and number\n"
            else:
                return f"% Invalid input detected at '^' marker.\n"

        elif self.cli_mode == 3: 
            if not self.current_line: return ""
            line_cfg = self.config["lines"][self.current_line]
            
            if action == "password" and len(action_parts) == 2:
                line_cfg["password"] = "" if is_no else action_parts[1]
                return ""
            elif action == "exec-timeout" and len(action_parts) >= 3:
                line_cfg["timeout"] = "0 0" if is_no else f"{action_parts[1]} {action_parts[2]}"
                return ""
            elif action == "transport" and action_parts[1] == "input":
                if self.current_line == "vty 0 15":
                    line_cfg["transport_input"] = ["all"] if is_no else action_parts[2:]
                return ""
            elif action == "login":
                return ""
            else:
                return f"% Invalid input detected at '^' marker.\n"
                
        elif self.cli_mode == 4: 
            if action == "ip" and len(action_parts) >= 3:
                if action_parts[1] == "address" and len(action_parts) >= 4:
                    if self.current_interface and self.current_interface in self.interfaces:
                        intf = self.interfaces[self.current_interface]
                        if hasattr(intf, 'ip'):
                            intf.ip = "" if is_no else action_parts[2]
                            intf.subnet = "" if is_no else action_parts[3]
                        else:
                            intf["ip"] = "" if is_no else action_parts[2]
                            intf["subnet"] = "" if is_no else action_parts[3]
                    return ""
                elif action_parts[1] == "helper-address":
                    if self.current_interface and self.current_interface in self.interfaces:
                        intf = self.interfaces[self.current_interface]
                        if hasattr(intf, 'ip_helper_address'):
                            intf.ip_helper_address = "" if is_no else action_parts[2]
                    return ""
                
            elif action == "description" and len(action_parts) >= 2:
                if self.current_interface and self.current_interface in self.interfaces:
                    desc_text = " ".join(action_parts[1:])
                    intf = self.interfaces[self.current_interface]
                    if hasattr(intf, 'description'):
                        intf.description = "" if is_no else desc_text
                    else:
                        intf["description"] = "" if is_no else desc_text
                return ""
                
            elif action in ("shutdown",):
                is_up = is_no 
                if self.current_interface and self.current_interface in self.interfaces:
                    intf = self.interfaces[self.current_interface]
                    if hasattr(intf, 'is_up'):
                        intf.is_up = is_up
                return ""

            elif action.startswith("int") and len(action_parts) > 1:
                resolved = self._resolve_interface(action_parts[1:])
                if resolved:
                    self.current_interface = resolved
                    return ""
                else:
                    return "% Invalid interface type and number\n"
            else:
                return f"% Invalid input detected at '^' marker.\n"

        return f"% Invalid input detected at '^' marker.\n"