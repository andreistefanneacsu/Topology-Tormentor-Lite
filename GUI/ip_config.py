from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QLabel, QRadioButton, QButtonGroup, QMessageBox, QGroupBox
from PyQt6.QtCore import Qt

class IPConfigWidget(QWidget):
    def __init__(self, host_device, all_devices=None, all_links=None):
        super().__init__()
        self.host = host_device
        if all_devices is not None and all_links is not None:
            from simulator import NetworkSimulator
            self.simulator = NetworkSimulator(all_devices, all_links)
        else:
            self.simulator = None
            
        self.intf = self.host.interfaces.get("FastEthernet0")
        if "Wireless0" in self.host.interfaces and getattr(self.host.interfaces["Wireless0"], 'is_up', False):
            self.intf = self.host.interfaces["Wireless0"]
            
        self.resize(350, 350)
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma; font-size: 12px;")
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Internet Protocol (TCP/IP) Properties")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        self.dhcp_radio = QRadioButton("Obtain an IP address automatically")
        self.static_radio = QRadioButton("Use the following IP address:")
        
        self.radio_group = QButtonGroup()
        self.radio_group.addButton(self.dhcp_radio)
        self.radio_group.addButton(self.static_radio)
        
        
        group = QGroupBox("IP settings")
        group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #7F9DB9; border-radius: 4px; margin-top: 12px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        group_layout = QVBoxLayout(group)
        
        group_layout.addWidget(self.dhcp_radio)
        group_layout.addWidget(self.static_radio)

        form = QGridLayout()
        form.setSpacing(8)
        self.ip_input = QLineEdit(self.intf.ip if self.intf else "")
        self.sub_input = QLineEdit(self.intf.subnet if self.intf else "")
        self.gw_input = QLineEdit(self.host.config.get("default-gateway", ""))
        self.dns_input = QLineEdit(self.host.config.get("dns-server", ""))

        style = "background-color: white; border: 1px solid #7F9DB9; padding: 3px;"
        for box in [self.ip_input, self.sub_input, self.gw_input, self.dns_input]: 
            box.setStyleSheet(style)
            box.setMinimumSize(150, 24)

        form.addWidget(QLabel("IP address:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        form.addWidget(self.ip_input, 0, 1)
        form.addWidget(QLabel("Subnet mask:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        form.addWidget(self.sub_input, 1, 1)
        form.addWidget(QLabel("Default gateway:"), 2, 0, Qt.AlignmentFlag.AlignRight)
        form.addWidget(self.gw_input, 2, 1)
        form.addWidget(QLabel("DNS server:"), 3, 0, Qt.AlignmentFlag.AlignRight)
        form.addWidget(self.dns_input, 3, 1)

        group_layout.addLayout(form)
        layout.addWidget(group)
        
        self.dhcp_radio.toggled.connect(self.toggle_inputs)
        
        if self.host.config.get("dhcp_enabled", False):
            self.dhcp_radio.setChecked(True)
        else:
            self.static_radio.setChecked(True)
        
        save_btn = QPushButton("OK")
        save_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 5px 15px;")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def toggle_inputs(self):
        is_static = self.static_radio.isChecked()
        for box in [self.ip_input, self.sub_input, self.gw_input, self.dns_input]:
            box.setEnabled(is_static)
            if not is_static:
                box.setStyleSheet("background-color: #e0e0e0; border: 1px solid gray; padding: 2px; color: black; font-weight: bold;")
            else:
                box.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 2px; color: black; font-weight: normal;")

    def save_config(self):
        if self.dhcp_radio.isChecked():
            self.host.config["dhcp_enabled"] = True
            if self.simulator:
                res = self.simulator.request_dhcp(self.host)
                if res:
                    intf_name = res.get("interface")
                    intf = self.host.interfaces.get(intf_name)
                    if intf:
                        intf.ip = res["ip"]
                        intf.subnet = res["subnet"]
                        self.intf = intf
                        
                        self.ip_input.setText(intf.ip)
                        self.sub_input.setText(intf.subnet)
                        self.gw_input.setText(res["gateway"])
                        self.dns_input.setText(res["dns"])
                    self.host.config["default-gateway"] = res["gateway"]
                    self.host.config["dns-server"] = res["dns"]
                    QMessageBox.information(self, "DHCP", "Successfully obtained IP address via DHCP.")
                else:
                    QMessageBox.warning(self, "DHCP", "Failed to obtain IP address. No DHCP server found.")
            else:
                QMessageBox.warning(self, "Error", "Simulator context missing.")
        else:
            self.host.config["dhcp_enabled"] = False
            if self.intf:
                self.intf.ip = self.ip_input.text().strip()
                self.intf.subnet = self.sub_input.text().strip()
            self.host.config["default-gateway"] = self.gw_input.text().strip()
            self.host.config["dns-server"] = self.dns_input.text().strip()
            self.host.config["dns-server"] = self.dns_input.text().strip()
            QMessageBox.information(self, "Success", "Static IP configuration saved successfully.")