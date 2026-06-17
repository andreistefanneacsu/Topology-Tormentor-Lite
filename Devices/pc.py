from Devices.host import Host

class PC(Host):
    def __init__(self, name):
        super().__init__(name, "PC")