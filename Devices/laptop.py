from Devices.host import Host
from Devices.interface import Interface

class Laptop(Host):
    def __init__(self, name):
        super().__init__(name, host_type="Laptop")
        self.interfaces["RS232"] = Interface("RS232", is_console=True)
        self.interfaces["Wireless0"] = Interface("Wireless0", is_console=False)
        self.interfaces["Wireless0"].is_wireless = True
        self.console_target = None 

    def connect_serial(self, device):
        self.console_target = device

    def disconnect_serial(self):
        self.console_target = None