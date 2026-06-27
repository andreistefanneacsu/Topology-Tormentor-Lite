import json
import random
import ipaddress
import copy
import uuid

# =========================================================
# 1. IP ALLOCATOR & DETERMINISM
# =========================================================
class IPAllocator:
    def __init__(self):
        self.used_subnets = set()
        
    def get_unique_subnet(self, prefix=24, max_retries=1000):
        for _ in range(max_retries):
            b1 = random.choice([10, 172, 192])
            b2 = random.randint(0, 255) if b1 == 10 else random.randint(16, 31) if b1 == 172 else 168
            b3 = random.randint(0, 255)
            net = ipaddress.IPv4Network(f"{b1}.{b2}.{b3}.0/{prefix}", strict=False)
            if net not in self.used_subnets:
                self.used_subnets.add(net)
                return net
        raise Exception("Subnet exhaustion.")

def allocate_host(subnet, index):
    """Safely allocates a specific host IP from a subnet."""
    return str(list(subnet.hosts())[index])

# =========================================================
# 2. TOPOLOGY BUILDERS (Using 'prefix' and precise allocation)
# =========================================================
def build_two_router_topo(allocator):
    lan_a, lan_b = allocator.get_unique_subnet(24), allocator.get_unique_subnet(24)
    wan = allocator.get_unique_subnet(30)
    
    la_gw, la_pc = allocate_host(lan_a, 0), allocate_host(lan_a, 9)
    lb_gw, lb_pc = allocate_host(lan_b, 0), allocate_host(lan_b, 9)
    w_r1, w_r2 = allocate_host(wan, 0), allocate_host(wan, 1)

    topo = {
        "type": "p2p_routers",
        "devices": [
            {"id": "R1", "type": "router", "interfaces": [{"name": "g0/0", "ip": la_gw, "prefix": 24, "admin_state": "up", "oper_state": "up"}, {"name": "g0/1", "ip": w_r1, "prefix": 30, "admin_state": "up", "oper_state": "up"}], "routes": [{"network": str(lan_b), "via": w_r2}]},
            {"id": "R2", "type": "router", "interfaces": [{"name": "g0/0", "ip": lb_gw, "prefix": 24, "admin_state": "up", "oper_state": "up"}, {"name": "g0/1", "ip": w_r2, "prefix": 30, "admin_state": "up", "oper_state": "up"}], "routes": [{"network": str(lan_a), "via": w_r1}]},
            {"id": "PC_A", "type": "pc", "interfaces": [{"name": "fa0", "ip": la_pc, "prefix": 24}], "routes": [{"network": "0.0.0.0/0", "via": la_gw}]},
            {"id": "PC_B", "type": "pc", "interfaces": [{"name": "fa0", "ip": lb_pc, "prefix": 24}], "routes": [{"network": "0.0.0.0/0", "via": lb_gw}]}
        ],
        "links": [["R1:g0/0", "PC_A:fa0"], ["R1:g0/1", "R2:g0/1"], ["R2:g0/0", "PC_B:fa0"]]
    }
    return topo, "PC_A", "PC_B"

def build_three_router_chain_topo(allocator):
    lan_a, lan_b = allocator.get_unique_subnet(24), allocator.get_unique_subnet(24)
    w1, w2 = allocator.get_unique_subnet(30), allocator.get_unique_subnet(30)
    
    la_gw, la_pc = allocate_host(lan_a, 0), allocate_host(lan_a, 9)
    lb_gw, lb_pc = allocate_host(lan_b, 0), allocate_host(lan_b, 9)
    w1_r1, w1_r2 = allocate_host(w1, 0), allocate_host(w1, 1)
    w2_r2, w2_r3 = allocate_host(w2, 0), allocate_host(w2, 1)

    topo = {
        "type": "chain_routers",
        "devices": [
            {"id": "R1", "type": "router", "interfaces": [{"name": "g0/0", "ip": la_gw, "prefix": 24, "admin_state": "up", "oper_state": "up"}, {"name": "g0/1", "ip": w1_r1, "prefix": 30, "admin_state": "up", "oper_state": "up"}], "routes": [{"network": "0.0.0.0/0", "via": w1_r2}]},
            {"id": "R2", "type": "router", "interfaces": [{"name": "g0/0", "ip": w1_r2, "prefix": 30, "admin_state": "up", "oper_state": "up"}, {"name": "g0/1", "ip": w2_r2, "prefix": 30, "admin_state": "up", "oper_state": "up"}], "routes": [{"network": str(lan_a), "via": w1_r1}, {"network": str(lan_b), "via": w2_r3}]},
            {"id": "R3", "type": "router", "interfaces": [{"name": "g0/0", "ip": lb_gw, "prefix": 24, "admin_state": "up", "oper_state": "up"}, {"name": "g0/1", "ip": w2_r3, "prefix": 30, "admin_state": "up", "oper_state": "up"}], "routes": [{"network": "0.0.0.0/0", "via": w2_r2}]},
            {"id": "PC_A", "type": "pc", "interfaces": [{"name": "fa0", "ip": la_pc, "prefix": 24}], "routes": [{"network": "0.0.0.0/0", "via": la_gw}]},
            {"id": "PC_B", "type": "pc", "interfaces": [{"name": "fa0", "ip": lb_pc, "prefix": 24}], "routes": [{"network": "0.0.0.0/0", "via": lb_gw}]}
        ],
        "links": [["R1:g0/0", "PC_A:fa0"], ["R1:g0/1", "R2:g0/0"], ["R2:g0/1", "R3:g0/1"], ["R3:g0/0", "PC_B:fa0"]]
    }
    return topo, "PC_A", "PC_B"

# =========================================================
# 3. L2/L3 STATE SIMULATOR
# =========================================================
def get_physical_peer(topo, dev_id, iface_name):
    port_str = f"{dev_id}:{iface_name}"
    for link in topo["links"]:
        if link[0] == port_str: return link[1].split(":")
        elif link[1] == port_str: return link[0].split(":")
    return None, None

def simulate_traffic(topo, src_id, dst_id):
    src_dev = next((d for d in topo["devices"] if d["id"] == src_id), None)
    dst_dev = next((d for d in topo["devices"] if d["id"] == dst_id), None)
    if not src_dev or not dst_dev: return {"success": False, "hops": [], "devices": [], "drop_reason": "Device not found"}
    
    dst_ip = dst_dev["interfaces"][0]["ip"] if dst_dev.get("interfaces") else "0.0.0.0"
    curr_dev = src_dev
    hops, crossed_device_ids = [], []
    ttl = 10
    visited = set()

    while ttl > 0:
        ttl -= 1
        crossed_device_ids.append(curr_dev["id"])
        
        if curr_dev["id"] in visited: return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Routing loop"}
        visited.add(curr_dev["id"])
        if curr_dev["id"] == dst_id: return {"success": True, "hops": hops, "devices": crossed_device_ids, "drop_reason": None}

        egress_iface_name, next_hop_expected_ip = None, None

        if curr_dev["type"] == "pc":
            ip, prefix = curr_dev["interfaces"][0]["ip"], curr_dev["interfaces"][0]["prefix"]
            host_iface = ipaddress.IPv4Interface(f"{ip}/{prefix}")
            if ip in [str(host_iface.network.network_address), str(host_iface.network.broadcast_address)]:
                return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Invalid IP configuration"}

            gw = curr_dev["routes"][0]["via"] if curr_dev.get("routes") else None
            if not gw: return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "No default gateway"}
            
            gw_iface = ipaddress.IPv4Interface(f"{gw}/{prefix}")
            if host_iface.network.network_address != gw_iface.network.network_address:
                return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Gateway unreachable"}

            next_hop_expected_ip, egress_iface_name = gw, curr_dev["interfaces"][0]["name"]

        elif curr_dev["type"] == "router":
            dst_obj = ipaddress.IPv4Address(dst_ip)
            for iface in curr_dev["interfaces"]:
                inet = ipaddress.IPv4Interface(f"{iface['ip']}/{iface['prefix']}").network
                if dst_obj in inet:
                    next_hop_expected_ip, egress_iface_name = dst_ip, iface["name"]
                    if iface["oper_state"] == "down": return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Egress interface down"}
                    break

            if not egress_iface_name:
                longest_match = -1
                for route in curr_dev.get("routes", []):
                    rnet = ipaddress.IPv4Network(route["network"], strict=False)
                    if dst_obj in rnet and rnet.prefixlen > longest_match:
                        next_hop_expected_ip, longest_match = route["via"], rnet.prefixlen

                if not next_hop_expected_ip: return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Network unreachable"}
                
                nh_obj = ipaddress.IPv4Address(next_hop_expected_ip)
                for iface in curr_dev["interfaces"]:
                    inet = ipaddress.IPv4Interface(f"{iface['ip']}/{iface['prefix']}").network
                    if nh_obj in inet:
                        egress_iface_name = iface["name"]
                        if iface["oper_state"] == "down": return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Egress interface down"}
                        break

            if not egress_iface_name: return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Routing failure"}

        peer_dev_id, peer_iface_name = get_physical_peer(topo, curr_dev["id"], egress_iface_name)
        if not peer_dev_id: return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Physical link down"}
        
        next_dev = next((d for d in topo["devices"] if d["id"] == peer_dev_id), None)
        peer_iface_data = next((i for i in next_dev.get("interfaces", []) if i["name"] == peer_iface_name), None)

        if not peer_iface_data or peer_iface_data.get("oper_state", "up") == "down":
            return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "Next-hop interface down"}

        hops.append(next_hop_expected_ip if next_hop_expected_ip else peer_iface_data.get("ip"))
        curr_dev = next_dev

    return {"success": False, "hops": hops, "devices": crossed_device_ids, "drop_reason": "TTL expired"}

# =========================================================
# 4. TOOL WRAPPERS & CANONICAL SCHEMA
# =========================================================
def format_tool_args(args_dict): 
    return json.dumps(args_dict, separators=(',', ':'), sort_keys=True)

def make_tool_call(name, arguments): 
    return {"id": f"call_{uuid.uuid4().hex[:8]}", "type": "function", "function": {"name": name, "arguments": format_tool_args(arguments)}}

def sim_ping(res): 
    return json.dumps({"success": True, "hops": len(res["hops"]), "rtt": random.randint(1,15)}) if res["success"] else json.dumps({"success": False, "drop_reason": res["drop_reason"]})

def sim_traceroute(res):
    trace = {f"hop{i}": hop for i, hop in enumerate(res["hops"], 1)}
    if not res["success"]: trace[f"hop{len(res['hops']) + 1}"] = "*"
    return json.dumps(trace)

def sim_show_device(topo, dev_id):
    dev = next((d for d in topo["devices"] if d["id"] == dev_id), None)
    if not dev: return '{"error": "Not found"}'
    return json.dumps({"type": dev["type"], "interfaces_count": len(dev.get("interfaces", []))}) if dev["type"] == "router" else json.dumps({"type": dev["type"], "ip": dev["interfaces"][0]["ip"], "gateway": dev["routes"][0]["via"]})

def sim_show_interfaces(topo, dev_id): 
    return json.dumps({"interfaces": next((d for d in topo["devices"] if d["id"] == dev_id), {}).get("interfaces", [])})

def sim_show_routes(topo, dev_id): 
    return json.dumps({"routes": next((d for d in topo["devices"] if d["id"] == dev_id), {}).get("routes", [])})

# =========================================================
# 5. CAUSAL FAULT & RED HERRING INJECTOR
# =========================================================
def apply_faults_and_noise(topo, fault_type, allocator, path_devices):
    fault_data = {"issue": "", "fix": "", "dev": "", "noise_dev": None}
    
    path_pcs = [d for d in topo["devices"] if d["id"] in path_devices and d["type"] == "pc"]
    path_routers = [d for d in topo["devices"] if d["id"] in path_devices and d["type"] == "router"]
    
    target_pc = random.choice(path_pcs) if path_pcs else next(d for d in topo["devices"] if d["type"] == "pc")
    local_router = random.choice(path_routers) if path_routers else next(d for d in topo["devices"] if d["type"] == "router")

    # High Value Faults
    if fault_type == "PREFIX_MISMATCH": 
        target_pc["interfaces"][0]["prefix"] = 30
        fault_data.update({"issue": "Prefix mismatch on host.", "fix": "Match subnet prefix.", "dev": target_pc["id"]})
    elif fault_type == "PARTIAL_ROUTE_LOSS":
        if local_router.get("routes"): 
            local_router["routes"][0]["via"] = "198.51.100.1" # Dead next-hop
            fault_data.update({"issue": "Unreachable next-hop.", "fix": "Update route via.", "dev": local_router["id"]})
    elif fault_type == "ROUTER_INTERFACE_DOWN":
        local_router["interfaces"][0]["oper_state"] = "down"
        fault_data.update({"issue": "Interface down.", "fix": "Issue no shutdown.", "dev": local_router["id"]})
        
    # High-quality Red Herring (Connected to Causal Path)
    all_links = [l for l in topo["links"]]
    connected_to_path = set()
    for link in all_links:
        d1, d2 = link[0].split(":")[0], link[1].split(":")[0]
        if d1 in path_devices and d2 not in path_devices: connected_to_path.add(d2)
        elif d2 in path_devices and d1 not in path_devices: connected_to_path.add(d1)
        
    if connected_to_path and random.random() < 0.4:
        noise_dev_id = random.choice(list(connected_to_path))
        noise_r = next((d for d in topo["devices"] if d["id"] == noise_dev_id), None)
        if noise_r and noise_r.get("interfaces"):
            noise_r["interfaces"][0]["oper_state"] = "down"
            fault_data["noise_dev"] = noise_r["id"]

    return fault_data

# =========================================================
# 6. INVESTIGATE GENERATOR (Multi-tool, Evidence loops)
# =========================================================
def format_result(t_type, status, issue, fix, data=None):
    """Enforces the strict, unified schema output across all modes."""
    base = f"<result>\ntype: {t_type}\nstatus: {status}\nissue: {issue}\nfix: {fix}"
    if data:
        base += f"\ndata: {json.dumps(data)}"
    return base + "\n</result>"

def generate_investigate_scenario(topo, src_id, dst_id, fault_data):
    messages = [
        {"role": "system", "content": "MODE=INVESTIGATE\nYou are an autonomous diagnostic AI. You may use <think> blocks. Call tools sequentially or in parallel. End with a strict <result> block."},
        {"role": "user", "content": f"User reports {src_id} cannot reach {dst_id}. Investigate."}
    ]

    sim_res = simulate_traffic(topo, src_id, dst_id)
    ping_payload = sim_ping(sim_res)
    
    tc_ping = make_tool_call("ping", {"src": src_id, "dst": dst_id})
    messages.append({"role": "assistant", "content": "<think>\nTesting end-to-end reachability.\n</think>", "tool_calls": [tc_ping]})
    messages.append({"role": "tool", "tool_call_id": tc_ping["id"], "name": "ping", "content": ping_payload})
    
    if sim_res["success"]:
        messages.append({"role": "assistant", "content": format_result("diagnosis", "OK", "none", "none")})
        return messages

    drop_reason = sim_res["drop_reason"]

    # LOCAL / GATEWAY FAILURE (Parallel Tool Call Example)
    if "Invalid" in drop_reason or "Gateway" in drop_reason or "configuration" in drop_reason:
        tc_dev = make_tool_call("show_device", {"device": src_id})
        tc_int = make_tool_call("show_interfaces", {"device": src_id})
        messages.append({
            "role": "assistant", 
            "content": "<think>\nPing failed locally. Gathering device state and L2 configurations simultaneously.\n</think>", 
            "tool_calls": [tc_dev, tc_int]
        })
        messages.append({"role": "tool", "tool_call_id": tc_dev["id"], "name": "show_device", "content": sim_show_device(topo, src_id)})
        messages.append({"role": "tool", "tool_call_id": tc_int["id"], "name": "show_interfaces", "content": sim_show_interfaces(topo, src_id)})
        
        messages.append({"role": "assistant", "content": format_result("diagnosis", "FAIL", fault_data['issue'], fault_data['fix'])})

    # DOWNSTREAM FAILURE
    else:
        tc_trace = make_tool_call("traceroute", {"src": src_id, "dst": dst_id})
        messages.append({"role": "assistant", "content": "<think>\nPath failed in transit. Isolating drop hop via traceroute.\n</think>", "tool_calls": [tc_trace]})
        
        trace_payload = sim_traceroute(sim_res)
        messages.append({"role": "tool", "tool_call_id": tc_trace["id"], "name": "traceroute", "content": trace_payload})
        
        trace_res_dict = json.loads(trace_payload)
        valid_hops = [v for k, v in trace_res_dict.items() if v != "*"]
        last_hop_ip = valid_hops[-1] if valid_hops else "Unknown"
        last_hop_dev = next((d["id"] for d in topo["devices"] for i in d.get("interfaces", []) if i.get("ip") == last_hop_ip), "R1")
        
        # Checking Route and Interface in parallel on the drop node
        tc_routes = make_tool_call("show_routes", {"device": last_hop_dev})
        tc_int2 = make_tool_call("show_interfaces", {"device": last_hop_dev})
        messages.append({
            "role": "assistant", 
            "content": f"<think>\nTrace timed out post-{last_hop_dev}. Fetching route and physical interface state to isolate failure.\n</think>", 
            "tool_calls": [tc_routes, tc_int2]
        })
        messages.append({"role": "tool", "tool_call_id": tc_routes["id"], "name": "show_routes", "content": sim_show_routes(topo, last_hop_dev)})
        messages.append({"role": "tool", "tool_call_id": tc_int2["id"], "name": "show_interfaces", "content": sim_show_interfaces(topo, last_hop_dev)})

        # Explicit Red Herring acknowledgement in thought
        noise_text = f" Verified connected non-path interfaces are irrelevant." if fault_data.get("noise_dev") else ""
        messages.append({"role": "assistant", "content": f"<think>\nFault localized based on correlated state evidence.{noise_text}\n</think>\n" + format_result("diagnosis", "FAIL", fault_data['issue'], fault_data['fix'])})

    return messages

# =========================================================
# 7. MAIN DATASET GENERATOR
# =========================================================
def generate_dataset(filename="raw-data.jsonl", total_samples=4000, base_seed=42):
    fault_types = ["PREFIX_MISMATCH", "PARTIAL_ROUTE_LOSS", "ROUTER_INTERFACE_DOWN"]
    
    with open(filename, "w", encoding="utf-8") as f:
        for i in range(total_samples):
            # Strict determinism seed per sample execution trace
            random.seed(base_seed + i)
            
            allocator = IPAllocator()
            topo_choice = random.choice([build_two_router_topo, build_three_router_chain_topo])
            valid_topo, src_id, dst_id = topo_choice(allocator)
            
            healthy_sim = simulate_traffic(valid_topo, src_id, dst_id)
            causal_path = healthy_sim["devices"]

            mode = random.choices(["GENERATE", "REPAIR", "DEBUG", "INVESTIGATE"], weights=[0.20, 0.20, 0.20, 0.40], k=1)[0]
            entry = {"task_type": mode.lower(), "messages": []}
            
            if mode == "GENERATE":
                entry["messages"] = [
                    {"role": "system", "content": "MODE=GENERATE\nReturn ONLY valid topology JSON. <think> is optional."},
                    {"role": "user", "content": f"Generate a valid {valid_topo['type']} routed topology."},
                    {"role": "assistant", "content": format_result("topology", "OK", "none", "none", valid_topo)}
                ]
            elif mode == "REPAIR":
                broken_topo = copy.deepcopy(valid_topo)
                apply_faults_and_noise(broken_topo, random.choice(fault_types), allocator, causal_path)
                entry["messages"] = [
                    {"role": "system", "content": "MODE=REPAIR\nRepair the topology. Return JSON."},
                    {"role": "user", "content": f"Fix mistakes in this topology:\n{json.dumps(broken_topo)}"},
                    {"role": "assistant", "content": format_result("topology", "OK", "none", "none", valid_topo)}
                ]
            elif mode == "DEBUG":
                broken_topo = copy.deepcopy(valid_topo)
                if random.random() < 0.25:
                    entry["messages"] = [
                        {"role": "system", "content": "MODE=DEBUG\nDiagnose statically."},
                        {"role": "user", "content": f"Analyze topology:\n{json.dumps(valid_topo)}"},
                        {"role": "assistant", "content": "<think>\nScanning L2 and L3 prefixes for logic consistency.\n</think>\n" + format_result("diagnosis", "OK", "none", "none")}
                    ]
                else:
                    fault_data = apply_faults_and_noise(broken_topo, random.choice(fault_types), allocator, causal_path)
                    entry["messages"] = [
                        {"role": "system", "content": "MODE=DEBUG\nDiagnose statically."},
                        {"role": "user", "content": f"Analyze topology:\n{json.dumps(broken_topo)}"},
                        {"role": "assistant", "content": f"<think>\nIdentified constraint violation regarding {fault_data['dev']}.\n</think>\n" + format_result("diagnosis", "FAIL", fault_data['issue'], fault_data['fix'])}
                    ]
            elif mode == "INVESTIGATE":
                broken_topo = copy.deepcopy(valid_topo)
                if random.random() < 0.25: 
                    entry["messages"] = generate_investigate_scenario(broken_topo, src_id, dst_id, None)
                else:
                    fault_data = apply_faults_and_noise(broken_topo, random.choice(fault_types), allocator, causal_path)
                    entry["messages"] = generate_investigate_scenario(broken_topo, src_id, dst_id, fault_data)
            
            f.write(json.dumps(entry) + "\n")
            
    print(f"Success! Dataset saved as {filename}.")

if __name__ == "__main__":
    generate_dataset()