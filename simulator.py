import ipaddress
from collections import deque

class NetworkSimulator:
    def __init__(self, devices, links):
        self.devices = {d.id: d for d in devices}
        self.links = links

    def _is_in_subnet(self, target_ip, intf_ip, intf_mask):
        try:
            net = ipaddress.IPv4Interface(f"{intf_ip}/{intf_mask}").network
            target = ipaddress.IPv4Address(target_ip)
            return target in net
        except Exception:
            return False

    def _get_links(self, device_id, port_name):
        res = []
        for link in self.links:
            if (link.interface1["device_id"] == device_id and link.interface1["port"] == port_name) or \
               (link.interface2["device_id"] == device_id and link.interface2["port"] == port_name):
                res.append(link)
        return res

    def _get_out_interface(self, device, next_hop_ip):
        for name, intf in device.interfaces.items():
            if not getattr(intf, 'is_up', False) or not getattr(intf, 'ip', "") or not getattr(intf, 'subnet', ""):
                continue
            if self._is_in_subnet(next_hop_ip, intf.ip, intf.subnet):
                return name
        return None

    def _l2_forward(self, start_dev, start_port, target_ip):
        queue = deque()
        if "vlan" in start_port.lower():
            for p_name, p_obj in start_dev.interfaces.items():
                if "vlan" not in p_name.lower() and getattr(p_obj, 'is_up', False):
                    queue.append((start_dev, p_name))
        elif start_dev.type == "WirelessRouter" and (start_port.startswith("Ethernet ") or start_port == "Wireless0"):
            lan_wlan_ports = list(start_dev.get_lan_ports().keys()) + ["Wireless0"]
            for p_name in lan_wlan_ports:
                if getattr(start_dev.interfaces[p_name], 'is_up', False):
                    queue.append((start_dev, p_name))
        else:
            queue.append((start_dev, start_port))
            
        visited_links = set()
        
        while queue:
            curr_dev, curr_port = queue.popleft()
            
            links = self._get_links(curr_dev.id, curr_port)
            for link in links:
                if link.id in visited_links:
                    continue
                    
                visited_links.add(link.id)
                
                if link.interface1["device_id"] == curr_dev.id:
                    peer_id, peer_port = link.interface2["device_id"], link.interface2["port"]
                else:
                    peer_id, peer_port = link.interface1["device_id"], link.interface1["port"]
                    
                peer_dev = self.devices.get(peer_id)
                if not peer_dev: continue
                
                peer_intf = peer_dev.interfaces.get(peer_port)
                if not peer_intf or not getattr(peer_intf, 'is_up', False):
                    continue 
                    
                if peer_dev.type == "Router":
                    if getattr(peer_intf, 'ip', "") == target_ip:
                        return peer_dev, target_ip
                elif peer_dev.type == "WirelessRouter":
                    lan_wlan_ports = list(peer_dev.get_lan_ports().keys()) + ["Wireless0"]
                    if peer_port in lan_wlan_ports:
                        if getattr(peer_dev.interfaces[lan_wlan_ports[0]], 'ip', "") == target_ip:
                            return peer_dev, target_ip
                        for p_name in lan_wlan_ports:
                            if (p_name != peer_port or p_name == "Wireless0") and getattr(peer_dev.interfaces[p_name], 'is_up', False):
                                queue.append((peer_dev, p_name))
                    else:
                        if getattr(peer_intf, 'ip', "") == target_ip:
                            return peer_dev, target_ip
                else:
                    if peer_dev.type == "Switch":
                        vlan1 = peer_dev.interfaces.get("Vlan1")
                        if vlan1 and getattr(vlan1, 'is_up', False) and getattr(vlan1, 'ip', "") == target_ip:
                            return peer_dev, target_ip
                    else:
                        if getattr(peer_intf, 'ip', "") == target_ip:
                            return peer_dev, target_ip
                    
                    for p_name, p_obj in peer_dev.interfaces.items():
                        if p_name != peer_port and "vlan" not in p_name.lower() and getattr(p_obj, 'is_up', False):
                            queue.append((peer_dev, p_name))
                    
        return None, None

    def _route_packet(self, curr_dev, target_ip, ttl=30, source_ip=None):
        if ttl <= 0:
            return False, "Reply from {}: TTL expired in transit.".format(source_ip or "unknown"), None, source_ip
            
        for intf in curr_dev.interfaces.values():
            if getattr(intf, 'ip', "") == target_ip and getattr(intf, 'is_up', False):
                return True, "Success", curr_dev, source_ip

        next_hop_ip = None
        out_intf = self._get_out_interface(curr_dev, target_ip)
        
        if out_intf:
            next_hop_ip = target_ip 
            
        if not next_hop_ip and curr_dev.type in ("Router", "WirelessRouter"):
            for route in curr_dev.config.get("routes", []):
                if self._is_in_subnet(target_ip, route["network"], route["mask"]):
                    next_hop_ip = route["next_hop"]
                    out_intf = self._get_out_interface(curr_dev, next_hop_ip)
                    break
                    
        if not next_hop_ip:
            gw = curr_dev.config.get("default-gateway")
            if gw:
                next_hop_ip = gw
                out_intf = self._get_out_interface(curr_dev, gw)
                
        if not next_hop_ip or not out_intf:
            if curr_dev.type in ("Host", "PC", "Laptop"):
                return False, f"Destination host unreachable.", None, source_ip
            else:
                fallback_ip = getattr(curr_dev.interfaces[out_intf or list(curr_dev.interfaces.keys())[0]], 'ip', 'unknown')
                return False, f"Reply from {fallback_ip}: Destination net unreachable.", None, source_ip

        if not source_ip:
            source_ip = getattr(curr_dev.interfaces[out_intf], 'ip', "")

        next_dev, _ = self._l2_forward(curr_dev, out_intf, next_hop_ip)
        
        if not next_dev:
            return False, "Request timed out. (ARP failed at L2)", None, source_ip

        return self._route_packet(next_dev, target_ip, ttl - 1, source_ip)

    def ping(self, source_device, target_ip):
        print(f"\nPinging {target_ip} from {source_device.name} with 32 bytes of data:")
        
        for intf in source_device.interfaces.values():
            if getattr(intf, 'ip', "") == target_ip:
                for _ in range(4):
                    print(f"Reply from {target_ip}: bytes=32 time<1ms TTL=128")
                return

        fwd_success, fwd_msg, target_dev, source_ip = self._route_packet(source_device, target_ip)
        
        if not fwd_success:
            for _ in range(4): print(fwd_msg)
            self._print_stats(target_ip, 0)
            return
            
        rev_success, rev_msg, _, _ = self._route_packet(target_dev, source_ip, source_ip=source_ip)
        
        if not rev_success:
            for _ in range(4): print("Request timed out. (Return path failed)")
            self._print_stats(target_ip, 0)
            return

        for _ in range(4):
            print(f"Reply from {target_ip}: bytes=32 time=1ms TTL=128")
        self._print_stats(target_ip, 4)

    def _print_stats(self, target_ip, successes):
        lost = 4 - successes
        loss_pct = int((lost / 4) * 100)
        print(f"\nPing statistics for {target_ip}:")
        print(f"    Packets: Sent = 4, Received = {successes}, Lost = {lost} ({loss_pct}% loss)")

    def request_dhcp(self, host_device):
        queue = deque()
        for p_name, p_obj in host_device.interfaces.items():
            if getattr(p_obj, 'is_up', False):
                queue.append((host_device, p_name, p_name, None))
        
        visited_links = set()
        dhcp_server = None
        successful_start_port = None
        final_helper_ip = None
        
        while queue:
            curr_dev, curr_port, start_port, relay_ip = queue.popleft()
            
            curr_intf = curr_dev.interfaces.get(curr_port)
            if not relay_ip and curr_intf and getattr(curr_intf, 'ip_helper_address', ''):
                relay_ip = curr_intf.ip

            links = self._get_links(curr_dev.id, curr_port)
            for link in links:
                if link.id in visited_links:
                    continue
                    
                visited_links.add(link.id)
                
                peer_id = link.interface2["device_id"] if link.interface1["device_id"] == curr_dev.id else link.interface1["device_id"]
                peer_port = link.interface2["port"] if link.interface1["device_id"] == curr_dev.id else link.interface1["port"]
                    
                peer_dev = self.devices.get(peer_id)
                if not peer_dev: continue
                
                peer_intf = peer_dev.interfaces.get(peer_port)
                if not peer_intf or not getattr(peer_intf, 'is_up', False):
                    continue
                    
                if peer_dev.type == "WirelessRouter" and getattr(peer_dev, 'dhcp_enabled', False):
                    dhcp_server = peer_dev
                    successful_start_port = start_port
                    final_helper_ip = relay_ip or peer_intf.ip
                    break
                
                if peer_dev.type == "Server" and peer_dev.services.get("DHCP", {}).get("enabled", False):
                    dhcp_server = peer_dev
                    successful_start_port = start_port
                    final_helper_ip = relay_ip or peer_intf.ip
                    break
                    
                if peer_dev.type == "Switch":
                    for p_name, p_obj in peer_dev.interfaces.items():
                        if p_name != peer_port and "vlan" not in p_name.lower() and getattr(p_obj, 'is_up', False):
                            queue.append((peer_dev, p_name, start_port, relay_ip))
            if dhcp_server:
                break
        
        if dhcp_server:
            if dhcp_server.type == "Server":
                result = dhcp_server.allocate_ip(host_device.id, final_helper_ip)
            else:
                result = dhcp_server.allocate_ip(host_device.id)
                
            if not result:
                return None

            if dhcp_server.type == "WirelessRouter":
                ip = result
                gw = dhcp_server.get_lan_ip()
                dns = gw
                sub = "255.255.255.0"
                return {"ip": ip, "subnet": sub, "gateway": gw, "dns": dns, "interface": successful_start_port}
            elif dhcp_server.type == "Server":
                ip, pool_cfg = result
                return {
                    "ip": ip,
                    "subnet": pool_cfg.get("subnet_mask", "255.255.255.0"),
                    "gateway": pool_cfg.get("default_gateway", ""),
                    "dns": pool_cfg.get("dns_server", ""),
                    "interface": successful_start_port
                }
        return None