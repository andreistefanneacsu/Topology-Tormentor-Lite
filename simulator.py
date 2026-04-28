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

    def _get_link(self, device_id, port_name):
        for link in self.links:
            if (link.interface1["device_id"] == device_id and link.interface1["port"] == port_name) or \
               (link.interface2["device_id"] == device_id and link.interface2["port"] == port_name):
                return link
        return None

    def _get_out_interface(self, device, next_hop_ip):
        for name, intf in device.interfaces.items():
            if not getattr(intf, 'is_up', False) or not getattr(intf, 'ip', "") or not getattr(intf, 'subnet', ""):
                continue
            if self._is_in_subnet(next_hop_ip, intf.ip, intf.subnet):
                return name
        return None

    def _l2_forward(self, start_dev, start_port, target_ip):
        if "vlan" in start_port.lower():
            queue = deque()
            for p_name, p_obj in start_dev.interfaces.items():
                if "vlan" not in p_name.lower() and getattr(p_obj, 'is_up', False):
                    queue.append((start_dev, p_name))
        else:
            queue = deque([(start_dev, start_port)])
            
        visited_links = set()
        
        while queue:
            curr_dev, curr_port = queue.popleft()
            
            link = self._get_link(curr_dev.id, curr_port)
            if not link or link.id in visited_links:
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
                
            if peer_dev.type == "Switch":
                vlan1 = peer_dev.interfaces.get("Vlan1")
                if vlan1 and getattr(vlan1, 'is_up', False) and getattr(vlan1, 'ip', "") == target_ip:
                    return peer_dev, target_ip
                    
                for p_name, p_obj in peer_dev.interfaces.items():
                    if p_name != peer_port and "vlan" not in p_name.lower() and getattr(p_obj, 'is_up', False):
                        queue.append((peer_dev, p_name))
            else:
                if getattr(peer_intf, 'ip', "") == target_ip:
                    return peer_dev, target_ip
                    
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
            
        if not next_hop_ip and curr_dev.type == "Router":
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