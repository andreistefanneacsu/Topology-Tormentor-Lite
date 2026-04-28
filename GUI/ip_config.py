from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt

class IPConfigWidget(QWidget):
    def __init__(self, host_device):
        super().__init__()
        self.host = host_device
        self.intf = self.host.interfaces.get("FastEthernet0")
        self.resize(350, 200)
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma; font-size: 12px;")
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Internet Protocol (TCP/IP) Properties")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        form = QFormLayout()
        self.ip_input = QLineEdit(self.intf.ip if self.intf else "")
        self.sub_input = QLineEdit(self.intf.subnet if self.intf else "")
        self.gw_input = QLineEdit(self.host.config.get("default-gateway", ""))

        style = "background-color: white; border: 1px solid #7F9DB9; padding: 2px;"
        for box in [self.ip_input, self.sub_input, self.gw_input]: box.setStyleSheet(style)

        form.addRow("IP address:", self.ip_input)
        form.addRow("Subnet mask:", self.sub_input)
        form.addRow("Default gateway:", self.gw_input)

        layout.addLayout(form)
        
        save_btn = QPushButton("OK")
        save_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 5px 15px;")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def save_config(self):
        if self.intf:
            self.intf.ip = self.ip_input.text().strip()
            self.intf.subnet = self.sub_input.text().strip()
        self.host.config["default-gateway"] = self.gw_input.text().strip()
        self.window().close()