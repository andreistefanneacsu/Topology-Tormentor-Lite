from host import Host
from interface import Interface

class Laptop(Host):
    def __init__(self, name):
        super().__init__(name, host_type="Laptop")
        self.interfaces["RS232"] = Interface("RS232", is_console=True)
        self.console_target = None 

    def connect_serial(self, device):
        self.console_target = device

    def disconnect_serial(self):
        self.console_target = None

    def get_prompt(self):
        if self.console_target:
            return self.console_target.get_prompt()
        return super().get_prompt()

    def process_command(self, cmd_line):
        if self.console_target:
            return self.console_target.process_command(cmd_line)
        return super().process_command(cmd_line)