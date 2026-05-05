from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QGridLayout, QLineEdit, QTextEdit, QPushButton, QMessageBox, QListWidget, QLabel, QGroupBox
from PyQt6.QtCore import Qt
from simulator import NetworkSimulator

class EmailClientWidget(QWidget):
    def __init__(self, host_device, all_devices, all_links):
        super().__init__()
        self.host = host_device
        self.simulator = NetworkSimulator(all_devices, all_links)
        
        self.resize(500, 450)
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma; font-size: 12px;")
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #7F9DB9; }")
        
        self.setup_config_tab()
        self.setup_compose_tab()
        self.setup_inbox_tab()
        
        layout.addWidget(self.tabs)

    def setup_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        cfg = self.host.config.get("email_client", {})
        
        self.name_input = QLineEdit(cfg.get("name", ""))
        self.email_input = QLineEdit(cfg.get("email", ""))
        self.inc_server_input = QLineEdit(cfg.get("incoming_server", ""))
        self.out_server_input = QLineEdit(cfg.get("outgoing_server", ""))
        self.user_input = QLineEdit(cfg.get("username", ""))
        self.pass_input = QLineEdit(cfg.get("password", ""))
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        group = QGroupBox("Account Settings")
        group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #7F9DB9; border-radius: 4px; margin-top: 12px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        group_layout = QVBoxLayout(group)
        
        form_layout = QGridLayout()
        form_layout.setSpacing(8)
        
        for box in [self.name_input, self.email_input, self.inc_server_input, self.out_server_input, self.user_input, self.pass_input]:
            box.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 3px;")
            box.setMinimumWidth(150)
            
        form_layout.addWidget(QLabel("Your Name:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.name_input, 0, 1)
        form_layout.addWidget(QLabel("Email Address:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.email_input, 1, 1)
        form_layout.addWidget(QLabel("Incoming Mail Server:"), 2, 0, Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.inc_server_input, 2, 1)
        form_layout.addWidget(QLabel("Outgoing Mail Server:"), 3, 0, Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.out_server_input, 3, 1)
        form_layout.addWidget(QLabel("User Name:"), 4, 0, Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.user_input, 4, 1)
        form_layout.addWidget(QLabel("Password:"), 5, 0, Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.pass_input, 5, 1)
        
        group_layout.addLayout(form_layout)
        layout.addWidget(group)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 5px;")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)
        
        self.tabs.addTab(tab, "Configure")

    def save_config(self):
        self.host.config["email_client"] = {
            "name": self.name_input.text().strip(),
            "email": self.email_input.text().strip(),
            "incoming_server": self.inc_server_input.text().strip(),
            "outgoing_server": self.out_server_input.text().strip(),
            "username": self.user_input.text().strip(),
            "password": self.pass_input.text().strip()
        }
        QMessageBox.information(self, "Success", "Configuration saved.")

    def setup_compose_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        form = QGridLayout()
        form.setSpacing(8)
        self.to_input = QLineEdit()
        self.subject_input = QLineEdit()
        for box in [self.to_input, self.subject_input]:
            box.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 3px;")
            box.setMinimumWidth(150)
            
        form.addWidget(QLabel("To:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        form.addWidget(self.to_input, 0, 1)
        form.addWidget(QLabel("Subject:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        form.addWidget(self.subject_input, 1, 1)
        layout.addLayout(form)
        
        self.body_input = QTextEdit()
        self.body_input.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 2px;")
        layout.addWidget(self.body_input)
        
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 5px;")
        send_btn.clicked.connect(self.send_email)
        layout.addWidget(send_btn)
        
        self.tabs.addTab(tab, "Compose")

    def send_email(self):
        cfg = self.host.config.get("email_client", {})
        if not cfg.get("outgoing_server") or not cfg.get("email"):
            QMessageBox.warning(self, "Error", "Please configure Email settings first.")
            return
            
        target_ip = cfg.get("outgoing_server")
        success, msg, target_dev, source_ip = self.simulator._route_packet(self.host, target_ip)
        
        if not success:
            QMessageBox.critical(self, "Network Error", f"Cannot reach mail server {target_ip}:\n{msg}")
            return
            
        if target_dev.type != "Server":
            QMessageBox.critical(self, "Error", "Target device is not an Email Server.")
            return
            
        delivered, srv_msg = target_dev.receive_email(
            self.to_input.text().strip(),
            cfg.get("email"),
            self.subject_input.text().strip(),
            self.body_input.toPlainText()
        )
        
        if delivered:
            QMessageBox.information(self, "Success", "Email sent successfully.")
            self.to_input.clear()
            self.subject_input.clear()
            self.body_input.clear()
        else:
            QMessageBox.critical(self, "Server Error", f"Delivery failed: {srv_msg}")

    def setup_inbox_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        recv_btn = QPushButton("Receive")
        recv_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 5px;")
        recv_btn.clicked.connect(self.receive_emails)
        layout.addWidget(recv_btn)
        
        self.inbox_list = QListWidget()
        self.inbox_list.setStyleSheet("background-color: white; border: 1px solid #7F9DB9;")
        self.inbox_list.itemClicked.connect(self.show_email)
        layout.addWidget(self.inbox_list)
        
        self.email_view = QTextEdit()
        self.email_view.setReadOnly(True)
        self.email_view.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 2px;")
        layout.addWidget(self.email_view)
        
        self.tabs.addTab(tab, "Inbox")
        self.current_emails = []

    def receive_emails(self):
        cfg = self.host.config.get("email_client", {})
        if not cfg.get("incoming_server") or not cfg.get("username"):
            QMessageBox.warning(self, "Error", "Please configure Email settings first.")
            return
            
        target_ip = cfg.get("incoming_server")
        success, msg, target_dev, source_ip = self.simulator._route_packet(self.host, target_ip)
        
        if not success:
            QMessageBox.critical(self, "Network Error", f"Cannot reach mail server {target_ip}:\n{msg}")
            return
            
        if target_dev.type != "Server":
            QMessageBox.critical(self, "Error", "Target device is not an Email Server.")
            return
            
        auth_ok, data = target_dev.get_emails(cfg.get("username"), cfg.get("password"))
        
        if auth_ok:
            self.inbox_list.clear()
            self.current_emails = data
            for mail in data:
                self.inbox_list.addItem(f"From: {mail['from']} | Subject: {mail['subject']}")
            self.email_view.clear()
            QMessageBox.information(self, "Success", f"Retrieved {len(data)} emails.")
        else:
            QMessageBox.critical(self, "Authentication Error", f"Failed to retrieve emails: {data}")

    def show_email(self, item):
        idx = self.inbox_list.row(item)
        if idx >= 0 and idx < len(self.current_emails):
            mail = self.current_emails[idx]
            content = f"From: {mail['from']}\nSubject: {mail['subject']}\n\n{mail['body']}"
            self.email_view.setPlainText(content)
