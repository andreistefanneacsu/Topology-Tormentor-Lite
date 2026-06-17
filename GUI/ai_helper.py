import uuid
import random
import ipaddress
import requests
import json
import re
from typing import Dict
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QLabel, QComboBox, QTextBrowser, QCheckBox)
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
    import json
    try:
        raw_data = json.loads(ai_json_string)
        if "devices" in raw_data:
            for d in raw_data["devices"]:
                if "type" in d and isinstance(d["type"], str):
                    d["type"] = d["type"].title() if d["type"].lower() != "pc" else "PC"
                if "interfaces" in d and isinstance(d["interfaces"], list):
                    new_intfs = {}
                    for item in d["interfaces"]:
                        if "name" in item:
                            ip = item.get("ip", "")
                            prefix = item.get("prefix", "24")
                            if ip:
                                new_intfs[item["name"]] = f"{ip}/{prefix}"
                    d["interfaces"] = new_intfs
        ai_json_string = json.dumps(raw_data)
        ai_data = TopologyModel.model_validate_json(ai_json_string)
    except Exception as e:
        import traceback
        traceback.print_exc()
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
    topology_modified = pyqtSignal(str)
    finished_generating = pyqtSignal()

    def __init__(self, prompt, full_topology, history=None, model="net-arch:latest", user_id="default", allow_modification=True, send_topology=True):
        super().__init__()
        self.prompt = prompt
        self.full_topology = full_topology
        self.history = history or []
        self.model = model
        self.user_id = user_id
        self.allow_modification = allow_modification
        self.send_topology = send_topology
        
        # Determine model
        from .ai_config_manager import get_ai_config
        cfg = get_ai_config(self.user_id)

    def run(self):
        try:
            prompt_lower = self.prompt.lower()
            
            # Check exam mode Tormentor
            is_exam = getattr(self, 'mode', 'practice') == 'exam'
            if is_exam:
                system_prompt = "MODE=TORMENTOR. You are 'Topology Tormentor', a highly sarcastic, mocking, and aggressive networking exam proctor. You must make fun of the user's mistakes, be incredibly ironic, and refuse to give direct answers or commands. Ridicule their lack of knowledge and give only cryptic, frustrating hints. Speak strictly in the language they used (Romanian or English). DO NOT BE HELPFUL OR POLITE. Never say 'The topology appears structurally valid', ALWAYS find a way to insult the lack of connections or configuration.\n"
            elif any(w in prompt_lower for w in ["generate", "create", "build", "topology"]):
                system_prompt = "MODE=GENERATE\nGenerate ONLY valid topology JSON.\nNo explanations.\n"
            else:
                system_prompt = (
                    "MODE=INVESTIGATE\n"
                    "You are an autonomous diagnostic AI.\n"
                    "When asked to trace, ping, or investigate connectivity, YOU MUST ALWAYS use a <think> block to announce your intent (e.g. 'Testing end-to-end reachability') and the tool you want to call BEFORE generating a <result> block.\n"
                    "DO NOT output a <result> block until you have gathered information via tools."
                )

            if self.allow_modification:
                if any(w in prompt_lower for w in ["generate", "create", "build", "topology"]):
                    system_prompt += """
IMPORTANT: You must output ONLY valid JSON matching this exact structure:
```json
{
  "devices": [
    {"id": "unique-id", "type": "Router", "interfaces": {"g0/0": "10.0.0.1/24"}}
  ],
  "links": [
    ["id1:g0/0", "id2:fa0"]
  ]
}
```
DO NOT output any prefix like 'type: topology' or 'data:'. Output ONLY the raw JSON object. No explanations.
"""
                else:
                    system_prompt += """
IMPORTANT: 
If the user asks you to FIX, REPAIR, OPEN, or CLOSE interfaces in the topology, DO NOT describe the fix in text.
INSTEAD, output the ENTIRE modified topology JSON inside a ```json block (or raw json).
We will automatically apply your JSON to the live workspace. Do not use any tools.
If the user just asks a question, answer it in plain text.
"""
            else:
                system_prompt += """
IMPORTANT: Do not output JSON or attempt to modify the topology. Reply only in plain text format to assist the user.
"""

            # Load AI Config
            from .ai_config_manager import get_ai_config
            cfg = get_ai_config(self.user_id)
            active_name = cfg.get("active_profile", "Default Ollama")
            provider = "Ollama"
            api_key = ""
            model_name = self.model
            
            for p in cfg.get("profiles", []):
                if p["name"] == active_name:
                    provider = p.get("provider", "Ollama")
                    api_key = p.get("api_key", "")
                    model_name = p.get("model", self.model)
                    break

            # Send the topology explicitly to the AI but filter out raw uuids and coordinate data to save context window
            clean_topo = {"devices": [], "links": []}
            for d in self.full_topology.get("devices", []):
                c_dev = {"name": d.get("name"), "type": d.get("type")}
                if d.get("type", "").lower() in ("pc", "laptop", "server"):
                    c_dev["config"] = {"default-gateway": d.get("config", {}).get("default-gateway", "")}
                else:
                    c_dev["config"] = d.get("config", {})
                
                intfs = d.get("interfaces", [])
                if isinstance(intfs, dict):
                    intfs = [{k: v} for k, v in intfs.items()]
                    
                c_intfs = {}
                for item in intfs:
                    for name, data in item.items():
                        c_intfs[name] = {"ip": data.get("ip", ""), "subnet": data.get("subnet", ""), "is_up": data.get("is_up", False)}
                c_dev["interfaces"] = c_intfs
                clean_topo["devices"].append(c_dev)
                
            for l in self.full_topology.get("links", []):
                d1 = l.get("interface1", {})
                d2 = l.get("interface2", {})
                if isinstance(d1, dict) and isinstance(d2, dict):
                    clean_topo["links"].append(f"{d1.get('device_id')}:{d1.get('port')} <-> {d2.get('device_id')}:{d2.get('port')}")

            if self.send_topology:
                system_prompt += f"\n\nCurrent Topology State:\n{json.dumps(clean_topo)}\n"

            # ----------------------------------------------------
            # Adapter for Tools (generator.py compatible format)
            # ----------------------------------------------------
            tool_topo = {"devices": [], "links": []}
            uuid_to_name = {}
            import ipaddress
            for d in self.full_topology.get("devices", []):
                uuid_to_name[d.get("id")] = d.get("name")
                t_dev = {
                    "id": d.get("name"),
                    "type": "pc" if d.get("type", "").lower() in ("pc", "laptop", "server") else "router",
                    "interfaces": [],
                    "routes": []
                }
                cfg_routes = d.get("config", {}).get("routes", [])
                for r in cfg_routes:
                    if "network" in r and "next-hop" in r:
                        t_dev["routes"].append({"network": r["network"], "via": r["next-hop"]})
                gw = d.get("config", {}).get("default-gateway")
                if gw:
                    t_dev["routes"].append({"network": "0.0.0.0/0", "via": gw})
                
                intfs = d.get("interfaces", [])
                if isinstance(intfs, dict):
                    intfs = [{k: v} for k, v in intfs.items()]
                for item in intfs:
                    for name, data in item.items():
                        subnet_str = data.get("subnet", "255.255.255.0")
                        prefix = 24
                        try:
                            prefix = ipaddress.IPv4Network(f"0.0.0.0/{subnet_str}", strict=False).prefixlen
                        except Exception:
                            pass
                        t_intf = {
                            "name": name,
                            "ip": data.get("ip", ""),
                            "prefix": prefix,
                            "admin_state": "up" if data.get("is_up", False) else "down",
                            "oper_state": "up" if data.get("is_up", False) else "down"
                        }
                        t_dev["interfaces"].append(t_intf)
                tool_topo["devices"].append(t_dev)
                
            for l in self.full_topology.get("links", []):
                d1 = l.get("interface1", {})
                d2 = l.get("interface2", {})
                if isinstance(d1, dict) and isinstance(d2, dict):
                    n1 = uuid_to_name.get(d1.get('device_id'), "Unknown")
                    n2 = uuid_to_name.get(d2.get('device_id'), "Unknown")
                    tool_topo["links"].append([f"{n1}:{d1.get('port')}", f"{n2}:{d2.get('port')}"])

            messages = [{"role": "system", "content": system_prompt}]
            for msg in self.history:
                role = "user" if msg['role'] == "You" else "assistant"
                content = msg['content'].replace("&lt;", "<").replace("&gt;", ">")
                messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": self.prompt})
            
            ai_text = ""
            
            if provider == "Google Gemini":
                if not api_key:
                    self.error_occurred.emit("Google Gemini API Key is missing. Please configure it in AI Settings.")
                    return
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    actual_model = model_name if model_name else 'gemini-1.5-flash'
                    gemini_model = genai.GenerativeModel(actual_model)
                    
                    prompt_str = system_prompt + "\n\n"
                    for m in self.history:
                        prompt_str += f"{m['role']}: {m['content']}\n"
                    prompt_str += "You: " + self.prompt
                    
                    resp = gemini_model.generate_content(prompt_str)
                    ai_text = resp.text
                except Exception as e:
                    self.error_occurred.emit(f"Gemini API Error: {str(e)}")
                    return
                    
            elif provider == "OpenAI":
                if not api_key:
                    self.error_occurred.emit("OpenAI API Key is missing. Please configure it in AI Settings.")
                    return
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    actual_model = model_name if model_name else 'gpt-4o'
                    messages_list = [{"role": "system", "content": system_prompt}]
                    for msg in self.history:
                        role = "user" if msg['role'] == "You" else "assistant"
                        messages_list.append({"role": role, "content": msg['content']})
                    messages_list.append({"role": "user", "content": self.prompt})

                    payload = {"model": actual_model, "messages": messages_list}
                    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
                    resp.raise_for_status()
                    ai_text = resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    self.error_occurred.emit(f"OpenAI API Error: {str(e)}")
                    return

            elif provider == "Anthropic":
                if not api_key:
                    self.error_occurred.emit("Anthropic API Key is missing. Please configure it in AI Settings.")
                    return
                try:
                    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                    actual_model = model_name if model_name else 'claude-3-haiku-20240307'
                    
                    anthropic_messages = []
                    for msg in self.history:
                        role = "user" if msg['role'] == "You" else "assistant"
                        anthropic_messages.append({"role": role, "content": msg['content']})
                    anthropic_messages.append({"role": "user", "content": self.prompt})
                    
                    payload = {
                        "model": actual_model,
                        "max_tokens": 1024,
                        "system": system_prompt,
                        "messages": anthropic_messages
                    }
                    resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=60)
                    resp.raise_for_status()
                    ai_text = resp.json()["content"][0]["text"]
                except Exception as e:
                    self.error_occurred.emit(f"Anthropic API Error: {str(e)}")
                    return
                    
            else: # Default: Ollama
                url = "http://localhost:11434/api/chat"
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from generator import simulate_traffic, sim_ping, sim_traceroute, sim_show_device, sim_show_interfaces, sim_show_routes
                
                max_steps = 10
                for _ in range(max_steps):
                    payload = {
                        "model": model_name,
                        "messages": messages,
                        "stream": False,
                        "options": {"num_ctx": 8192, "num_predict": -1}
                    }
                    try:
                        response = requests.post(url, json=payload, timeout=120)
                        response.raise_for_status()
                        resp_data = response.json().get("message", {})
                        
                        messages.append(resp_data)
                        
                        ai_text = resp_data.get("content", "")
                        
                        # The fine-tuned model drops native tool calls and only outputs <think> blocks.
                        # We must parse its intent from the think text to execute the simulated tools!
                        tool_executed = False
                        if "<think>" in ai_text:
                            # Extract src and dst from the original prompt
                            src_match = re.search(r'reports\s+(\S+)\s+cannot reach\s+(\S+)', self.prompt)
                            if not src_match:
                                src_match = re.search(r'from\s+(\S+)\s+to\s+(\S+)', self.prompt, re.IGNORECASE)
                            
                            src = src_match.group(1).strip() if src_match else "PC_A"
                            dst = src_match.group(2).strip().rstrip('.') if src_match else "PC_B"
                            
                            think_text = ai_text.lower()
                            
                            if "traceroute" in think_text:
                                sim = simulate_traffic(tool_topo, src, dst)
                                tr = sim_traceroute(sim)
                                messages.append({"role": "user", "content": "Tool Output (traceroute):\n" + tr})
                                self.response_received.emit(f"[AI ran traceroute from {src} to {dst}]")
                                tool_executed = True
                            elif "ping" in think_text or "reachability" in think_text:
                                sim = simulate_traffic(tool_topo, src, dst)
                                tr = sim_ping(sim)
                                messages.append({"role": "user", "content": "Tool Output (ping):\n" + tr})
                                self.response_received.emit(f"[AI ran ping from {src} to {dst}]")
                                tool_executed = True
                            elif "device state" in think_text or "show_device" in think_text:
                                r1 = sim_show_device(tool_topo, src)
                                r2 = sim_show_interfaces(tool_topo, src)
                                messages.append({"role": "user", "content": "Tool Output (show_device):\n" + r1 + "\n" + r2})
                                self.response_received.emit(f"[AI ran show_device & show_interfaces on {src}]")
                                tool_executed = True
                            elif "routes" in think_text or "show_routes" in think_text or "interface state" in think_text:
                                target_dev = src
                                dev_match = re.search(r'post-([^.]+)', think_text)
                                if dev_match:
                                    target_dev = dev_match.group(1).strip()
                                # Fix case mismatch if any
                                for d in tool_topo["devices"]:
                                    if d["id"].lower() == target_dev.lower():
                                        target_dev = d["id"]
                                        break
                                r1 = sim_show_routes(tool_topo, target_dev)
                                r2 = sim_show_interfaces(tool_topo, target_dev)
                                messages.append({"role": "user", "content": "Tool Output (show_routes):\n" + r1 + "\n" + r2})
                                self.response_received.emit(f"[AI ran show_routes & show_interfaces on {target_dev}]")
                                tool_executed = True
                                
                        if tool_executed:
                            continue
                            
                        if "<result>" in ai_text:
                            break
                        else:
                            break
                        
                    except Exception as e:
                        self.error_occurred.emit(f"Ollama API Error: {str(e)}")
                        return
            
            if ai_text.strip():
                ai_text = ai_text.replace("<result>", "&lt;result&gt;").replace("</result>", "&lt;/result&gt;")
                ai_text = ai_text.replace("<think>", "&lt;think&gt;").replace("</think>", "&lt;/think&gt;")
                
                json_match = re.search(r'```(?:json)?(.*?)```', ai_text, re.DOTALL | re.IGNORECASE)
                if not json_match:
                    json_match = re.search(r'(\{.*\})', ai_text, re.DOTALL)
                    
                if json_match:
                    json_str = json_match.group(1).strip()
                    try:
                        data = json.loads(json_str)
                        
                        is_generate = any(w in self.prompt.lower() for w in ["generate", "create", "build", "topology"])
                        
                        if is_generate and "devices" in data and "links" in data:
                            self.topology_generated.emit(json_str)
                        elif "devices" in data or data.get("type") in ("update_route", "fix", "repair"):
                            self.topology_modified.emit(json_str)
                    except Exception:
                        pass
                
                # Remove the JSON from the chat so it doesn't clutter
                if json_match:
                    ai_text = ai_text.replace(json_match.group(0), "").strip()
                    
                if ai_text:
                    self.response_received.emit(ai_text)
            
            self.finished_generating.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"Unexpected Error: {str(e)}")

class NetworkAssistantWidget(QWidget):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.mode = getattr(self.canvas.window(), 'mode', 'practice')
        self.user_id = getattr(self.canvas.window(), 'user_id', 'default')
        self.history = [] 
        self.setWindowTitle("AI Topology Assistant")
        self.setFixedWidth(350)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI';")

        layout = QVBoxLayout(self)
        
        header = QLabel("AI Network Assistant")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa; margin-top: 5px;")
        layout.addWidget(header)

        self.chat_area = QTextBrowser()
        self.chat_area.setOpenLinks(False)
        self.chat_area.anchorClicked.connect(self.handle_link_clicked)
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 8px; padding: 10px; font-size: 12px;")
        layout.addWidget(self.chat_area)

        # Model Selector
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("AI Profile:"))
        self.model_selector = QComboBox()
        self.model_selector.setStyleSheet("QComboBox { background-color: #313244; color: #CDD6F4; padding: 5px; border-radius: 4px; border: 1px solid #45475A; }")
        
        # Load from config manager
        from .ai_config_manager import get_ai_config
        self.config = get_ai_config(self.user_id)
        
        for p in self.config.get("profiles", []):
            self.model_selector.addItem(p["name"])
            
        active = self.config.get("active_profile", "")
        idx = self.model_selector.findText(active)
        if idx >= 0: self.model_selector.setCurrentIndex(idx)
            
        self.model_selector.currentTextChanged.connect(self.save_model_selection)
        model_layout.addWidget(self.model_selector)
        layout.addLayout(model_layout)
        
        self.cb_allow_mod = QCheckBox("Allow Canvas Modification")
        self.cb_allow_mod.setStyleSheet("color: #CDD6F4;")
        
        self.cb_send_topo = QCheckBox("Send Current Topology")
        self.cb_send_topo.setStyleSheet("color: #CDD6F4;")
        self.cb_send_topo.setChecked(True)
        
        options_layout = QHBoxLayout()
        options_layout.addWidget(self.cb_allow_mod)
        options_layout.addWidget(self.cb_send_topo)
        layout.addLayout(options_layout)
        
        # Apply initial state
        if active == "Default":
            self.cb_allow_mod.setChecked(True)
            self.cb_allow_mod.setEnabled(True)
        else:
            self.cb_allow_mod.setChecked(False)
            self.cb_allow_mod.setEnabled(False)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask a networking question or ask to generate a topology...")
        self.input_field.setStyleSheet("QLineEdit { background-color: #313244; color: #CDD6F4; padding: 8px; border-radius: 4px; border: 1px solid #45475A; }")
        self.input_field.returnPressed.connect(self.send_query)
        layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Analyze Topology")
        self.send_btn.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; border-radius: 5px; padding: 10px;")
        self.send_btn.clicked.connect(self.send_query)
        layout.addWidget(self.send_btn)

        initial_challenge = "Hello! I am your AI assistant. You can ask me to generate a topology, or ask any networking questions!"
        self.append_message("Assistant", initial_challenge)
        self._check_ai_configured()

    def _check_ai_configured(self):
        import subprocess
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(["ollama", "list"], startupinfo=startupinfo).decode("utf-8")
            if "network-assistant-ultimate" not in output:
                self.append_message("System", "The default AI model is not installed. Please open Configure -> AI Settings to install it.")
        except Exception:
            self.append_message("System", "Ollama is not installed. Please open Configure -> AI Settings to install it.")


    def refresh_profiles(self):
        from .ai_config_manager import get_ai_config
        self.config = get_ai_config(self.user_id)
        
        self.model_selector.blockSignals(True)
        self.model_selector.clear()
        
        for p in self.config.get("profiles", []):
            self.model_selector.addItem(p["name"])
            
        active = self.config.get("active_profile", "")
        idx = self.model_selector.findText(active)
        if idx >= 0:
            self.model_selector.setCurrentIndex(idx)
            
        self.model_selector.blockSignals(False)

    def save_model_selection(self, profile_name):
        from .ai_config_manager import get_ai_config, save_ai_config
        cfg = get_ai_config(self.user_id)
        cfg["active_profile"] = profile_name
        save_ai_config(cfg, self.user_id)
        
        if profile_name == "Default":
            self.cb_allow_mod.setEnabled(True)
            self.cb_allow_mod.setChecked(True)
        else:
            self.cb_allow_mod.setChecked(False)
            self.cb_allow_mod.setEnabled(False)

    def handle_link_clicked(self, url):
        url_str = url.toString()
        if url_str.startswith("toggle_think:"):
            try:
                idx = int(url_str.split(":")[1])
                self.history[idx]["show_think"] = not self.history[idx].get("show_think", False)
                self.render_chat()
            except Exception:
                pass

    def append_message(self, role, text):
        import re
        text = re.sub(
            r'<think>', 
            r'<div style="background-color: #313244; color: #a6adc8; padding: 10px; margin: 10px 0; border-left: 4px solid #89b4fa; border-radius: 4px;"><i>Thinking:</i><br>', 
            text, flags=re.IGNORECASE
        )
        text = re.sub(
            r'</think>', 
            r'</div><br>', 
            text, flags=re.IGNORECASE
        )

        self.history.append({"role": role, "content": text})
        if len(self.history) > 20:
            self.history = self.history[-20:]
            
        self.render_chat()

    def render_chat(self):
        self.chat_area.clear()
        import re
        for i, msg in enumerate(self.history):
            role = msg.get("role", "Assistant")
            text = msg.get("content", "")
            
            color = "#00ffcc" if role == "Assistant" else "#ffffff" if role == "You" else "#f9e2af"
            
            text = re.sub(
                r'<tool_call>(.*?)</tool_call>',
                r'<div style="background-color: #181825; color: #6c7086; padding: 10px; margin: 8px 0; border: 1px solid #45475a; border-radius: 4px; font-family: monospace; font-size: 11px;">\1</div>',
                text, flags=re.IGNORECASE | re.DOTALL
            )
            
            processed_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            processed_text = re.sub(r'`(.*?)`', r'<code style="background-color: #313244; color: #f5c2e7; padding: 2px;">\1</code>', processed_text)
            processed_text = processed_text.replace("\n", "<br>")
            
            html = f"<b style='color:{color}'>{role}:</b><br>"
            html += f"{processed_text}<br><br>"
            self.chat_area.insertHtml(html)
            
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_topology_generated(self, json_str):
        import json
        try:
            data = json.loads(json_str)
            if data.get("type") == "update_route":
                device_name = data.get("device")
                via = data.get("via")
                network = data.get("network", "0.0.0.0")
                mask = data.get("mask", "0.0.0.0")
                if device_name and via:
                    for d in self.canvas.devices:
                        if getattr(d, 'name', '') == device_name or getattr(d, 'id', '') == device_name:
                            if "routes" not in d.config:
                                d.config["routes"] = []
                            d.config["routes"].append({
                                "network": network,
                                "mask": mask,
                                "next_hop": via
                            })
                            d.save_device_state()
                            self.append_message("System", f"Applied fix: Added route {network} via {via} on {device_name}.")
                            return
                self.append_message("System", "Failed to apply fix: Invalid device or via address.")
                return

            inflated_data = import_from_ai(json_str, {})
            if inflated_data:
                self.canvas.import_topology(inflated_data)
                self.append_message("System", "Topology automatically added to the canvas!")
            else:
                self.append_message("System", "Failed to parse AI topology.")
        except Exception as e:
            self.append_message("System", f"Failed to load generated topology: {str(e)}")

    def send_query(self):
        query = self.input_field.text().strip()
        if not query: return
        
        self.append_message("You", query)
        self.input_field.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ Thinking...")
        self.input_field.setEnabled(False)

        full_topology = {
            "devices": [d.to_dict() for d in self.canvas.devices],
            "links": [l.to_dict() for l in self.canvas.links]
        }
        
        allow_mod = self.cb_allow_mod.isChecked()
        send_topo = self.cb_send_topo.isChecked()
        
        self.worker = GlobalAIWorker(query, full_topology, history=self.history, user_id=self.user_id, 
                                     allow_modification=allow_mod, send_topology=send_topo)
        self.worker.mode = getattr(self, 'mode', 'practice')
        self.worker.response_received.connect(self.handle_response)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.topology_generated.connect(self.handle_topology_generated)
        self.worker.topology_modified.connect(self.handle_topology_modified)
        self.worker.finished_generating.connect(self.handle_finished)
        self.worker.start()

    def handle_response(self, text):
        self.append_message("Assistant", text)

    def handle_error(self, error):
        self.append_message("Assistant", f"Error: {error}")
        self.handle_finished()

    def handle_finished(self):
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Analyze Topology")
        self.input_field.setEnabled(True)

    def handle_topology_modified(self, topo_json):
        """Apply AI-made config changes back to the live canvas devices."""
        import json
        try:
            new_topo = json.loads(topo_json)
            
            if new_topo.get("type") in ("fix", "repair"):
                fix_data = new_topo.get("fix", {})
                if isinstance(fix_data, dict):
                    if fix_data.get("type") == "update_route":
                        self.handle_topology_generated(json.dumps(fix_data))
                        return
            
            for new_dev in new_topo.get("devices", []):
                for canvas_dev in self.canvas.devices:
                    if getattr(canvas_dev, 'name', '') == new_dev.get('name') or getattr(canvas_dev, 'id', '') == new_dev.get('id'):
                        # Sync config
                        new_config = new_dev.get("config", {})
                        if "default-gateway" in new_config:
                            canvas_dev.config["default-gateway"] = new_config["default-gateway"]
                        if "routes" in new_config:
                            canvas_dev.config["routes"] = new_config["routes"]
                        # Sync interface states
                        new_intfs = new_dev.get("interfaces", [])
                        
                        # Normalize to a single dictionary mapping name -> data
                        normalized_intfs = {}
                        if isinstance(new_intfs, dict):
                            normalized_intfs = new_intfs
                        elif isinstance(new_intfs, list):
                            for item in new_intfs:
                                if "name" in item:
                                    # Format: {"name": "fa0", "ip": "...", "subnet": "..."}
                                    name = item.pop("name")
                                    normalized_intfs[name] = item
                                else:
                                    # Format: {"fa0": {"ip": "...", "subnet": "..."}}
                                    for k, v in item.items():
                                        normalized_intfs[k] = v

                        for intf_name, intf_data in normalized_intfs.items():
                            if intf_name in canvas_dev.interfaces:
                                intf_obj = canvas_dev.interfaces[intf_name]
                                if intf_data.get("ip"):
                                    intf_obj.ip = intf_data["ip"]
                                if intf_data.get("subnet"):
                                    intf_obj.subnet = intf_data["subnet"]
                                if "is_up" in intf_data:
                                    intf_obj.is_up = intf_data["is_up"]
                        
                        if hasattr(canvas_dev, 'save_device_state'):
                            canvas_dev.save_device_state()
                        break
            
            self.canvas.update()
            
            try:
                data = {
                    "devices": [d.to_dict() for d in self.canvas.devices],
                    "links": [l.to_dict() for l in self.canvas.links]
                }
                with open('uhhhh.json', 'w') as f:
                    json.dump(data, f, indent=4)
            except Exception:
                pass
                
        except Exception as e:
            self.append_message("System", f"Failed to apply AI fix: {str(e)}")