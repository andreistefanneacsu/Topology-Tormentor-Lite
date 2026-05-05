from Devices.host import Host
import ipaddress

class Server(Host):
    def __init__(self, name):
        super().__init__(name, "Server")

        self.email_domain = ""
        # users format: "username": {"password": "pwd", "inbox": []}
        # inbox item format: {"from": "sender@domain", "subject": "subj", "body": "text"}
        self.email_users = {}

        self.dns_records = {}

        self.services = {
            "DHCP": {
                "enabled": False,
                "pools": {}
            }
        }
        self.dhcp_leases = {}

    def receive_email(self, to_email, from_email, subject, body):
        if "@" not in to_email:
            return False, "Invalid to email address"
        username, domain = to_email.split("@", 1)
        if domain != self.email_domain:
            return False, "Domain does not match server"
        if username not in self.email_users:
            return False, "User does not exist"
        self.email_users[username]["inbox"].append({
            "from": from_email,
            "subject": subject,
            "body": body
        })
        return True, "Email delivered successfully"

    def get_emails(self, username, password):
        if username not in self.email_users:
            return False, "Authentication failed"
        if self.email_users[username]["password"] != password:
            return False, "Authentication failed"
        return True, self.email_users[username]["inbox"]

    def resolve_dns(self, domain):
        return self.dns_records.get(domain, None)


    def allocate_ip(self, device_id, helper_ip=None):
        """Return (ip_str, pool_cfg) tuple or None if allocation fails.
        The pool is selected based on the helper_ip (IP‑helper address).
        """
        existing = self.dhcp_leases.get(device_id)
        if existing:
            pool_cfg = self.services["DHCP"]["pools"].get(existing["gateway"], {})
            return existing["ip"], pool_cfg

        dhcp_cfg = self.services.get("DHCP", {})
        if not dhcp_cfg.get("enabled"):
            return None

        pools = dhcp_cfg.get("pools", {})
        if helper_ip and helper_ip in pools:
            selected_pool_key = helper_ip
        else:
            return None

        pool = pools[selected_pool_key]
        used_ips = {v["ip"] for v in self.dhcp_leases.values()}
        try:
            start_int = int(ipaddress.IPv4Address(pool.get("start_ip", "192.168.1.100")))
            end_int   = int(ipaddress.IPv4Address(pool.get("end_ip",   "192.168.1.149")))
        except Exception:
            return None
        for ip_int in range(start_int, end_int + 1):
            ip_str = str(ipaddress.IPv4Address(ip_int))
            if ip_str not in used_ips:
                self.dhcp_leases[device_id] = {"ip": ip_str, "gateway": selected_pool_key}
                return ip_str, pool
        return None

    def release_ip(self, device_id):
        self.dhcp_leases.pop(device_id, None)

    def to_dict(self):
        data = super().to_dict()
        data["email_domain"] = self.email_domain
        data["email_users"] = self.email_users
        data["dns_records"] = self.dns_records
        data["services"] = self.services
        data["dhcp_leases"] = self.dhcp_leases
        return data

    def from_dict(self, data):
        super().from_dict(data)
        self.email_domain = data.get("email_domain", self.email_domain)
        self.email_users  = data.get("email_users",  self.email_users)
        self.dns_records  = data.get("dns_records",  self.dns_records)
        self.dhcp_leases  = data.get("dhcp_leases",  self.dhcp_leases)

        saved_services = data.get("services", self.services)
        dhcp = saved_services.get("DHCP", {})

        if isinstance(dhcp.get("pools"), list):
            new_pools = {}
            for p in dhcp.get("pools", []):
                key = p.get("default_gateway", "")
                if key:
                    new_pools[key] = p
            dhcp["pools"] = new_pools

        migrated_leases = {}
        for dev_id, lease in self.dhcp_leases.items():
            if isinstance(lease, str):
                migrated_leases[dev_id] = {"ip": lease, "gateway": ""}
            else:
                migrated_leases[dev_id] = lease
        self.dhcp_leases = migrated_leases

        self.services = saved_services
