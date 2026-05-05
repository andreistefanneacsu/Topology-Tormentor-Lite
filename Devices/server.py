from Devices.host import Host

class Server(Host):
    def __init__(self, name):
        super().__init__(name, "Server")
        
        self.email_domain = ""
        # users format: "username": {"password": "pwd", "inbox": []}
        # inbox item format: {"from": "sender@domain", "subject": "subj", "body": "text"}
        self.email_users = {}
        
        self.dns_records = {}

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

    def to_dict(self):
        data = super().to_dict()
        data["email_domain"] = self.email_domain
        data["email_users"] = self.email_users
        data["dns_records"] = self.dns_records
        return data

    def from_dict(self, data):
        super().from_dict(data)
        self.email_domain = data.get("email_domain", self.email_domain)
        self.email_users = data.get("email_users", self.email_users)
        self.dns_records = data.get("dns_records", self.dns_records)
