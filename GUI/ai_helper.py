import uuid
import random
import ipaddress
import requests
import json
import re
from typing import Dict
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor
from .schema import TopologyModel

def generate_random_mac() -> str:
    return f"08:0B:AC:{random.randint(0, 255):02X}:{random.randint(0, 255):02X}:{random.randint(0, 255):02X}"

def expand_cidr(cidr_str: str):
    if not cidr_str: return "", ""
    try:
        intf = ipaddress.IPv4Interface(cidr_str)
        return str(intf.ip), str(intf.netmask)
    except Exception:
        return "", ""

def expand_intf(abbr_name: str) -> str:
    cleaned = abbr_name.strip().lower().replace(" ", "")
    if cleaned in ("fa0", "fa0/0", "fastethernet0", "fe0"):
        return "FastEthernet0"
    if cleaned.startswith("fa0/"):
        num = cleaned[4:]
        return f"fastEthernet 0/{num}"
    if cleaned.startswith("g0/") and not cleaned.startswith("gi"):
        num = cleaned[3:]
        return f"gigabitEthernet 0/{num}"
    if cleaned.startswith("g") and not cleaned.startswith("gi"):
        return "gigabitEthernet " + cleaned[1:]
    return abbr_name

def get_blank_intf(speed: str, is_console: bool = False) -> Dict:
    return {
        "ip": "", "subnet": "", "description": "AI Generated",
        "is_up": True, "mac": generate_random_mac(),
        "speed": speed, "is_console": is_console,
        "ip_helper_address": "", "default-gateway": "", "dns-server": ""
    }

def generate_device_interfaces(device_type: str, ai_configured_intfs: Dict) -> list:
    interfaces = []
    
    configured_map = {}
    for abbr_name, cidr in ai_configured_intfs.items():
        expanded_name = expand_intf(abbr_name)
        ip, mask = expand_cidr(cidr)
        configured_map[expanded_name] = {"ip": ip, "subnet": mask}

    def add_port(name, speed, is_console=False):
        port_data = get_blank_intf(speed, is_console)
        if name in configured_map:
            port_data["ip"] = configured_map[name]["ip"]
            port_data["subnet"] = configured_map[name]["subnet"]
        interfaces.append({name: port_data})

    if device_type == "Router":
        for i in range(3): add_port(f"gigabitEthernet 0/{i}", "1Gbps")
    elif device_type == "Switch":
        for i in range(1, 25): add_port(f"fastEthernet 0/{i}", "100Mbps")
        add_port("gigabitEthernet 0/1", "1Gbps")
        add_port("gigabitEthernet 0/2", "1Gbps")
        add_port("Vlan1", "Virtual")
        add_port("Console", "9600bps", True)
    elif device_type in ["PC", "Laptop", "Server"]:
        add_port("FastEthernet0", "100Mbps")
        if device_type == "Laptop":
             add_port("Wireless0", "10Mbps")
             
    return interfaces

def get_cable_type(type1: str, type2: str) -> str:
    mdi = ["Router", "PC", "Server", "Laptop"]
    mdix = ["Switch", "Hub"]
    
    if (type1 in mdi and type2 in mdi) or (type1 in mdix and type2 in mdix):
        return "Cross-Over"
    return "Straight-Through"

def import_from_ai(ai_json_string: str, uuid_to_short_map: Dict) -> Dict:
    try:
        ai_data = TopologyModel.model_validate_json(ai_json_string)
    except Exception as e:
        print(f"Validation Blocked Import: {e}")
        return None

    short_to_uuid = {v: k for k, v in uuid_to_short_map.items()}
    inflated_data = {"devices": [], "links": []}
    
    device_types = {}
    x_offset, y_offset = 200.0, 200.0

    for dev in ai_data.devices:
        if dev.id not in short_to_uuid:
            short_to_uuid[dev.id] = str(uuid.uuid4())
        dev_uuid = short_to_uuid[dev.id]
        device_types[dev.id] = dev.type

        inflated_dev = {
            "name": dev.id, 
            "id": dev_uuid,
            "type": dev.type,
            "hostname": dev.id,
            "_x": x_offset,
            "_y": y_offset,
            "mac": generate_random_mac(),
            "config": {
                "cdp_run": True,
                "routes": [],
                "dhcp_pools": dev.dhcp if dev.dhcp else {},
                "default-gateway": getattr(dev, "gateway", ""),
                "lines": {"con 0": {}, "vty 0 15": {}}
            },
            "interfaces": generate_device_interfaces(dev.type, dev.interfaces or {})
        }
        
        inflated_data["devices"].append(inflated_dev)
        
        x_offset += 200.0 
        if x_offset > 800:
            x_offset = 200.0
            y_offset += 150.0

    if ai_data.links:
        for link in ai_data.links:
            d1_short, p1_abbr = link[0].split(':')
            d2_short, p2_abbr = link[1].split(':')
            
            t1 = device_types.get(d1_short, "Unknown")
            t2 = device_types.get(d2_short, "Unknown")
            
            inflated_link = {
                "id": str(uuid.uuid4()),
                "cable_type": get_cable_type(t1, t2),
                "interface1": {
                    "device_id": short_to_uuid.get(d1_short),
                    "port": expand_intf(p1_abbr)
                },
                "interface2": {
                    "device_id": short_to_uuid.get(d2_short),
                    "port": expand_intf(p2_abbr)
                }
            }
            inflated_data["links"].append(inflated_link)

    return inflated_data

class GlobalAIWorker(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    topology_generated = pyqtSignal(str)

    def __init__(self, prompt, full_topology, history=None, model="net-arch:latest"):
        super().__init__()
        self.prompt = prompt
        self.full_topology = full_topology
        self.history = history or []
        self.model = model

    def run(self):
        try:
            prompt_lower = self.prompt.lower()
            if any(w in prompt_lower for w in ["generate", "create", "build", "topology"]):
                system_prompt = "MODE=GENERATE\nGenerate ONLY valid topology JSON.\nNo explanations."
            elif any(w in prompt_lower for w in ["validate", "check"]):
                system_prompt = "MODE=VALIDATE\nValidate the given topology."
            else:
                system_prompt = "MODE=DEBUG\nProvide helpful networking assistance."

            url = "http://localhost:11434/api/chat"
            
            messages = [{"role": "system", "content": system_prompt}]
            for msg in self.history:
                role = "user" if msg['role'] == "You" else "assistant"
                messages.append({"role": role, "content": msg['content']})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": 3072,
                    "num_predict": -1
                }
            }
            
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=300
                )
                response.raise_for_status()
            except requests.exceptions.Timeout:
                self.error_occurred.emit("AI took too long to respond (120s timeout). The model might still be loading or your hardware is under heavy load.")
                return
            except requests.exceptions.ConnectionError:
                self.error_occurred.emit("Cannot connect to Local AI. Please ensure Ollama is running (ollama serve).")
                return
            except requests.exceptions.RequestException as e:
                self.error_occurred.emit(f"AI Connection Error: {str(e)}")
                return
            
            ai_text = response.json().get("message", {}).get("content", "")
            
            tag_patterns = [r"\[RANGE", r"\[SUBNET", r"\[EXERCISE", r"\[SUBLET"]
            for pat in tag_patterns:
                match = re.search(pat, ai_text, re.I)
                if match:
                    end_bracket = ai_text.find("]", match.start())
                    if end_bracket != -1:
                        after_tag = ai_text[end_bracket+1:].strip()
                        if len(after_tag) > 5:
                            ai_text = ai_text[:end_bracket+1]
                    break

            max_iterations = 5
            for _ in range(max_iterations):
                tool_triggered = False
                tool_result = ""
                
                range_match = re.search(r"\[RANGE(?:\s*TOOL)?:\s*([^\]]+)\]", ai_text, re.I)
                subnet_match = re.search(r"\[SUB(?:NET|LET)(?:\s*TOOL)?:\s*([^\]]+)\]", ai_text, re.I)
                exercise_match = re.search(r"\[EXERCISE(?:\s*TOOL)?:\s*([^\]]+)\]", ai_text, re.I)

                if range_match:
                    try:
                        param = range_match.group(1).strip()
                        if "," in param:
                            ip_p, mask_p = [x.strip() for x in param.split(",")]
                            net = ipaddress.IPv4Network(f"{ip_p}/{mask_p}", strict=False)
                        else:
                            net = ipaddress.IPv4Network(param, strict=False)
                        
                        tool_result = f"\n[TOOL RESULT: {param} -> Network: {net.network_address}, Range: {net[1]} - {net[-2]}, Mask: {net.netmask}]"
                        tool_triggered = True
                    except Exception as e: tool_result = f"\n[TOOL ERROR: {str(e)}]"

                elif subnet_match:
                    try:
                        params = subnet_match.group(1).strip()
                        parts = [p.strip() for p in params.split(",")]
                        base_cidr = parts[0]
                        hosts = []
                        for p in parts[1:]:
                            clean_p = p.split("=")[-1] if "=" in p else p
                            hosts.append(int(clean_p))
                        
                        base_net = ipaddress.IPv4Network(base_cidr, strict=False)
                        hosts.sort(reverse=True)
                        
                        current_start = base_net.network_address
                        results = []
                        for h in hosts:
                            needed = h + 2
                            prefix = 32 - (needed - 1).bit_length()
                            sub = ipaddress.IPv4Network((current_start, prefix), strict=False)
                            results.append(f"- {h} hosts: {sub.network_address}/{prefix} (Range: {sub[1]} - {sub[-2]})")
                            current_start = sub.broadcast_address + 1
                        
                        tool_result = "\n[TOOL RESULT: Optimized Subnets]\n" + "\n".join(results)
                        tool_triggered = True
                    except Exception as e: tool_result = f"\n[TOOL ERROR: {str(e)}]"

                elif exercise_match:
                    try:
                        params = exercise_match.group(1).strip()
                        parts = [p.strip() for p in params.split(",")]
                        base_net = ipaddress.IPv4Network(parts[0], strict=False)
                        
                        branches = []
                        server_branch = ""
                        for p in parts[1:]:
                            if p.startswith("server_branch:"):
                                server_branch = p.split(":")[1]
                            else:
                                name, count = p.split(":")
                                branches.append({"name": name, "hosts": int(count)})
                        
                        branches.sort(key=lambda x: x['hosts'], reverse=True)
                        
                        current_start = base_net.network_address
                        results = ["| Branch | Network | Mask | Gateway (.1) | Server (Last Usable) | PC Range |", "|---|---|---|---|---|---|"]
                        for b in branches:
                            needed = b['hosts'] + 2
                            prefix = 32 - (needed - 1).bit_length()
                            sub = ipaddress.IPv4Network((current_start, prefix), strict=False)
                            
                            gw = sub[1]
                            server = sub[-2] if b['name'] == server_branch else "N/A"
                            pc_start = sub[2]
                            pc_end = sub[-3] if b['name'] == server_branch else sub[-2]
                            
                            results.append(f"| {b['name']} | {sub.network_address}/{prefix} | {sub.netmask} | {gw} | {server} | {pc_start} - {pc_end} |")
                            current_start = sub.broadcast_address + 1
                        
                        tool_result = "\n[TOOL RESULT: Lab Exercise Setup]\n" + "\n".join(results)
                        tool_triggered = True
                    except Exception as e: tool_result = f"\n[TOOL ERROR: {str(e)}]"

                if not tool_triggered:
                    break

                clean_tag = ""
                if range_match: clean_tag = range_match.group(0)
                elif subnet_match: clean_tag = subnet_match.group(0)
                elif exercise_match: clean_tag = exercise_match.group(0)

                messages.append({"role": "assistant", "content": clean_tag})
                messages.append({"role": "system", "content": tool_result + "\n\nPlease provide the final answer based on the tool result."})
                final_payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_ctx": 3072, "num_predict": -1}
                }
                final_resp = requests.post(url, json=final_payload, timeout=300)
                ai_text = final_resp.json().get("message", {}).get("content", ai_text + tool_result)
            
            json_match = re.search(r'(\{.*\})', ai_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                try:
                    TopologyModel.model_validate_json(json_str)
                    self.topology_generated.emit(json_str)
                except Exception:
                    pass
                
            self.response_received.emit(ai_text)
            
        except Exception as e:
            self.error_occurred.emit(f"Unexpected Error: {str(e)}")

class NetworkAssistantWidget(QWidget):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.history = [] 
        self.setWindowTitle("AI Topology Assistant")
        self.setFixedWidth(350)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI';")

        layout = QVBoxLayout(self)
        
        header = QLabel("AI Network Assistant")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa; margin-top: 5px;")
        layout.addWidget(header)

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 8px; padding: 10px; font-size: 12px;")
        layout.addWidget(self.chat_area)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about the topology...")
        self.input_field.setStyleSheet("background-color: #313244; border: none; border-radius: 5px; padding: 10px; color: white;")
        self.input_field.returnPressed.connect(self.send_query)
        layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Analyze Topology")
        self.send_btn.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; border-radius: 5px; padding: 10px;")
        self.send_btn.clicked.connect(self.send_query)
        layout.addWidget(self.send_btn)

        initial_challenge = "Hello! I am your AI assistant. You can ask me to generate a topology, or ask any networking questions!"
        self.append_message("Assistant", initial_challenge)

    def append_message(self, role, text):
        self.history.append({"role": role, "content": text})
        if len(self.history) > 10:
            self.history = self.history[-10:]
            
        color = "#00ffcc" if role == "Assistant" else "#ffffff"
        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_area.setTextCursor(cursor)
        
        import re
        processed_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        processed_text = re.sub(r'`(.*?)`', r'<code style="background-color: #313244; color: #f5c2e7; padding: 2px;">\1</code>', processed_text)
        processed_text = processed_text.replace("\n", "<br>")

        self.chat_area.insertHtml(f"<b style='color:{color}'>{role}:</b><br>{processed_text}<br><br>")
        
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def send_query(self):
        query = self.input_field.text().strip()
        if not query: return
        
        self.append_message("You", query)
        self.input_field.clear()
        self.send_btn.setEnabled(False)

        full_topology = {
            "devices": [d.to_dict() for d in self.canvas.devices],
            "links": [l.to_dict() for l in self.canvas.links]
        }
        
        self.worker = GlobalAIWorker(query, full_topology, history=self.history)
        self.worker.response_received.connect(self.handle_response)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.topology_generated.connect(self.handle_topology_generated)
        self.worker.start()

    def handle_response(self, text):
        self.append_message("Assistant", text)
        self.send_btn.setEnabled(True)

    def handle_error(self, error):
        self.append_message("Assistant", f"Error: {error}")
        self.send_btn.setEnabled(True)

    def handle_topology_generated(self, json_str):
        inflated_data = import_from_ai(json_str, {})
        if inflated_data:
            self.canvas.import_topology(inflated_data)
            self.append_message("System", "Topology automatically added to the canvas!")
        else:
            self.append_message("System", "Failed to parse AI topology.")