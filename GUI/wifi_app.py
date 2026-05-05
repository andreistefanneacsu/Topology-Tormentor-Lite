from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLabel, QMessageBox, QLineEdit, QFormLayout, QGroupBox)
from PyQt6.QtCore import Qt
from Devices.link import Link

class WifiAppWidget(QWidget):
    def __init__(self, host_device, canvas):
        super().__init__()
        self.host = host_device
        self.canvas = canvas
        self.all_devices = self.canvas.devices
        self.all_links = self.canvas.links
        self.routers = []
        self.resize(400, 300)
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma; font-size: 12px;")
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Wireless Network Connection")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        group_net = QGroupBox("Available Networks")
        group_net.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #7F9DB9; border-radius: 4px; margin-top: 12px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        net_layout = QVBoxLayout(group_net)

        self.network_list = QListWidget()
        self.network_list.setStyleSheet("background-color: white; border: 1px solid #7F9DB9;")
        net_layout.addWidget(self.network_list)

        self.refresh_btn = QPushButton("Refresh Networks")
        self.refresh_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 5px;")
        self.refresh_btn.clicked.connect(self.scan_networks)
        net_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(group_net)

        group_auth = QGroupBox("Authentication")
        group_auth.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #7F9DB9; border-radius: 4px; margin-top: 12px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        auth_layout = QVBoxLayout(group_auth)

        form = QHBoxLayout()
        form.addWidget(QLabel("Password:"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 3px;")
        self.pass_input.setMinimumWidth(150)
        form.addWidget(self.pass_input)
        auth_layout.addLayout(form)
        
        layout.addWidget(group_auth)

        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 5px;")
        self.connect_btn.clicked.connect(self.connect_to_network)
        btn_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 5px;")
        self.disconnect_btn.clicked.connect(self.user_disconnect)
        btn_layout.addWidget(self.disconnect_btn)
        
        layout.addLayout(btn_layout)
        
        self.scan_networks()

    def user_disconnect(self):
        self.disconnect_network()
        QMessageBox.information(self, "Disconnected", "Successfully disconnected from wireless network.")

    def scan_networks(self):
        self.network_list.clear()
        self.routers = [d for d in self.all_devices if d.type == "WirelessRouter"]
        for r in self.routers:
            self.network_list.addItem(f"{r.ssid} ({r.wifi_security})")

    def disconnect_network(self):
        links_to_remove = []
        for link in list(self.all_links):
            if (link.interface1["device_id"] == self.host.id and link.interface1["port"] == "Wireless0") or \
               (link.interface2["device_id"] == self.host.id and link.interface2["port"] == "Wireless0"):
                links_to_remove.append(link)
                
        for link in links_to_remove:
            self.all_links.remove(link)
            
        from GUI.canvas import CableNode
        items_to_remove = []
        for item in self.canvas.scene.items():
            if isinstance(item, CableNode) and item.cable_type == "Wireless":
                if item.node1.device.id == self.host.id or item.node2.device.id == self.host.id:
                    items_to_remove.append(item)
                    
        for item in items_to_remove:
            self.canvas.scene.removeItem(item)
            
        self.host.interfaces["Wireless0"].is_up = False
        if "FastEthernet0" in self.host.interfaces:
            self.host.interfaces["FastEthernet0"].is_up = True

    def connect_to_network(self):
        idx = self.network_list.currentRow()
        if idx < 0 or idx >= len(self.routers):
            QMessageBox.warning(self, "Error", "Please select a network first.")
            return

        r = self.routers[idx]
        password = self.pass_input.text()

        if r.wifi_security != "Disabled" and password != r.wifi_password:
            QMessageBox.warning(self, "Error", "Incorrect password.")
            return

        self.disconnect_network()

        new_link = Link(self.host, "Wireless0", r, "Wireless0", "Wireless")
        self.all_links.append(new_link)
        
        self.host.interfaces["Wireless0"].is_up = True
        
        if "FastEthernet0" in self.host.interfaces:
            self.host.interfaces["FastEthernet0"].is_up = False
            
        from GUI.canvas import CableNode
        host_node = self.canvas.get_node_by_device(self.host)
        r_node = self.canvas.get_node_by_device(r)
        if host_node and r_node:
            cable_node = CableNode(host_node, r_node, "Wireless")
            self.canvas.scene.addItem(cable_node)
        
        QMessageBox.information(self, "Success", f"Connected to {r.ssid}!\n(Use IP Config to request a DHCP address if needed)")
