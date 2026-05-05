from Devices.devices import Device
from Devices.interface import Interface


class WirelessRouter(Device):
    def __init__(self, name):
        super().__init__(name, "WirelessRouter")

        self.interfaces["Internet"] = Interface("Internet", is_console=False)

        for i in range(1, 5):
            port_name = f"Ethernet {i}"
            iface = Interface(port_name, is_console=False)
            iface.ip = "192.168.0.1"
            iface.subnet = "255.255.255.0"
            self.interfaces[port_name] = iface

        self.interfaces["Wireless0"] = Interface("Wireless0", is_console=False)
        self.interfaces["Wireless0"].is_wireless = True
        self.interfaces["Wireless0"].ip = "192.168.0.1"
        self.interfaces["Wireless0"].subnet = "255.255.255.0"

        self.ssid = "WirelessNet"
        self.wifi_password = ""
        self.wifi_security = "WPA2-Personal"  

        self.admin_username = "admin"
        self.admin_password = "admin"

        self.dhcp_enabled = True
        self.dhcp_start = "192.168.0.100"
        self.dhcp_end = "192.168.0.149"
        self.dhcp_leases = {}

        self.internet_connection_type = "DHCP"  

    def get_lan_ports(self):
        """Returns dict of all Ethernet LAN Interface objects (Ethernet 1-4)."""
        return { name: interface for name, interface in self.interfaces.items() if name.startswith("Ethernet ") }

    def get_internet_port(self):
        return self.interfaces.get("Internet")

    def get_wireless_interface(self):
        return self.interfaces.get("Wireless0")

    def get_lan_ip(self):
        """Returns the IP address of the first up LAN port (the router gateway IP)."""
        for iface in self.get_lan_ports().values():
            if getattr(iface, 'ip', ""):
                return iface.ip
        return "192.168.0.1"

    def set_lan_ip(self, ip, subnet="255.255.255.0"):
        """Sets the same IP/subnet on all LAN ports and Wireless0."""
        for port_name in list(self.get_lan_ports().keys()) + ["Wireless0"]:
            iface = self.interfaces.get(port_name)
            if iface:
                iface.ip = ip
                iface.subnet = subnet

    def check_login(self, username, password):
        return username == self.admin_username and password == self.admin_password

    def allocate_ip(self, device_id):
        if device_id in self.dhcp_leases:
            return self.dhcp_leases[device_id]
            
        import ipaddress
        try:
            start_ip_int = int(ipaddress.IPv4Address(self.dhcp_start))
            end_ip_int = int(ipaddress.IPv4Address(self.dhcp_end))
        except Exception:
            return None
            
        used_ips = set(self.dhcp_leases.values())
        for ip_int in range(start_ip_int, end_ip_int + 1):
            ip_str = str(ipaddress.IPv4Address(ip_int))
            if ip_str not in used_ips:
                self.dhcp_leases[device_id] = ip_str
                return ip_str
        return None

    def release_ip(self, device_id):
        if device_id in self.dhcp_leases:
            del self.dhcp_leases[device_id]

    def to_dict(self):
        data = super().to_dict()
        data["ssid"] = self.ssid
        data["wifi_password"] = self.wifi_password
        data["wifi_security"] = self.wifi_security
        data["admin_username"] = self.admin_username
        data["admin_password"] = self.admin_password
        data["dhcp_enabled"] = self.dhcp_enabled
        data["dhcp_start"] = self.dhcp_start
        data["dhcp_end"] = self.dhcp_end
        data["dhcp_leases"] = self.dhcp_leases
        data["internet_connection_type"] = self.internet_connection_type
        return data

    def from_dict(self, data):
        super().from_dict(data)
        self.ssid = data.get("ssid", self.ssid)
        self.wifi_password = data.get("wifi_password", self.wifi_password)
        self.wifi_security = data.get("wifi_security", self.wifi_security)
        self.admin_username = data.get("admin_username", self.admin_username)
        self.admin_password = data.get("admin_password", self.admin_password)
        self.dhcp_enabled = data.get("dhcp_enabled", self.dhcp_enabled)
        self.dhcp_start = data.get("dhcp_start", self.dhcp_start)
        self.dhcp_end = data.get("dhcp_end", self.dhcp_end)
        self.dhcp_leases = data.get("dhcp_leases", self.dhcp_leases)
        self.internet_connection_type = data.get("internet_connection_type", self.internet_connection_type)
