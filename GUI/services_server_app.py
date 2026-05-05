import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QPushButton, QLabel, QListWidget, 
                             QMessageBox, QStackedWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

class EmailServerWidget(QWidget):
    def __init__(self, host_device):
        super().__init__()
        self.server = host_device
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma; font-size: 12px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Email Service Configuration")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Domain config
        domain_layout = QHBoxLayout()
        domain_layout.addWidget(QLabel("Domain Name:"))
        self.domain_input = QLineEdit(self.server.email_domain)
        self.domain_input.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 2px;")
        domain_layout.addWidget(self.domain_input)
        
        set_domain_btn = QPushButton("Set")
        set_domain_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 2px 10px;")
        set_domain_btn.clicked.connect(self.set_domain)
        domain_layout.addWidget(set_domain_btn)
        
        layout.addLayout(domain_layout)
        
        layout.addWidget(QLabel("User Accounts:"))
        
        # User management
        user_form = QFormLayout()
        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        for box in [self.user_input, self.pass_input]: 
            box.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 2px;")
        
        user_form.addRow("User:", self.user_input)
        user_form.addRow("Password:", self.pass_input)
        layout.addLayout(user_form)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+")
        add_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 2px 10px;")
        add_btn.clicked.connect(self.add_user)
        
        remove_btn = QPushButton("-")
        remove_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 2px 10px;")
        remove_btn.clicked.connect(self.remove_user)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.user_list = QListWidget()
        self.user_list.setStyleSheet("background-color: white; border: 1px solid #7F9DB9;")
        layout.addWidget(self.user_list)
        
        self.refresh_user_list()

    def set_domain(self):
        self.server.email_domain = self.domain_input.text().strip()
        QMessageBox.information(self, "Success", f"Domain set to {self.server.email_domain}")

    def add_user(self):
        user = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        if not user or not password:
            QMessageBox.warning(self, "Error", "User and Password cannot be empty.")
            return
            
        if user in self.server.email_users:
            QMessageBox.warning(self, "Error", "User already exists.")
            return
            
        self.server.email_users[user] = {"password": password, "inbox": []}
        self.user_input.clear()
        self.pass_input.clear()
        self.refresh_user_list()

    def remove_user(self):
        selected = self.user_list.currentItem()
        if not selected: return
        
        user = selected.text()
        if user in self.server.email_users:
            del self.server.email_users[user]
            self.refresh_user_list()

    def refresh_user_list(self):
        self.user_list.clear()
        for user in self.server.email_users.keys():
            self.user_list.addItem(user)


class DnsServerWidget(QWidget):
    def __init__(self, host_device):
        super().__init__()
        self.server = host_device
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma; font-size: 12px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("DNS Service Configuration")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        self.domain_input = QLineEdit()
        self.ip_input = QLineEdit()
        for box in [self.domain_input, self.ip_input]: 
            box.setStyleSheet("background-color: white; border: 1px solid #7F9DB9; padding: 2px;")
            
        form_layout.addRow("Domain:", self.domain_input)
        form_layout.addRow("IP Address:", self.ip_input)
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Record")
        add_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 2px 10px;")
        add_btn.clicked.connect(self.add_record)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setStyleSheet("background-color: #F0F0F0; border: 1px solid gray; padding: 2px 10px;")
        remove_btn.clicked.connect(self.remove_record)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.records_table = QTableWidget(0, 2)
        self.records_table.setHorizontalHeaderLabels(["Domain", "IP Address"])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.records_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.records_table.setStyleSheet("background-color: white; border: 1px solid #7F9DB9;")
        layout.addWidget(self.records_table)
        
        self.refresh_records()

    def add_record(self):
        domain = self.domain_input.text().strip()
        ip = self.ip_input.text().strip()
        
        if not domain or not ip:
            QMessageBox.warning(self, "Error", "Domain and IP Address cannot be empty.")
            return
            
        self.server.dns_records[domain] = ip
        self.domain_input.clear()
        self.ip_input.clear()
        self.refresh_records()

    def remove_record(self):
        current_row = self.records_table.currentRow()
        if current_row < 0:
            return
            
        domain = self.records_table.item(current_row, 0).text()
        if domain in self.server.dns_records:
            del self.server.dns_records[domain]
            self.refresh_records()

    def refresh_records(self):
        self.records_table.setRowCount(0)
        for domain, ip in self.server.dns_records.items():
            row_idx = self.records_table.rowCount()
            self.records_table.insertRow(row_idx)
            self.records_table.setItem(row_idx, 0, QTableWidgetItem(domain))
            self.records_table.setItem(row_idx, 1, QTableWidgetItem(ip))


class ServicesWidget(QWidget):
    def __init__(self, host_device):
        super().__init__()
        self.server = host_device
        self.resize(550, 450)
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma; font-size: 12px;")
        
        main_layout = QHBoxLayout(self)
        
        # Sidebar for service selection
        self.service_list = QListWidget()
        self.service_list.setFixedWidth(150)
        self.service_list.setStyleSheet("""
            QListWidget {
                background-color: white; 
                border: 1px solid #7F9DB9;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #E0E0E0;
            }
            QListWidget::item:selected {
                background-color: #316AC5;
                color: white;
            }
        """)
        self.service_list.setIconSize(QSize(24, 24))
        
        # Stacked widget for the configuration panels
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #ECE9D8;")
        
        # Initialize services
        self.init_services()
        
        main_layout.addWidget(self.service_list)
        main_layout.addWidget(self.stacked_widget)
        
        self.service_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        if self.service_list.count() > 0:
            self.service_list.setCurrentRow(0)

    def init_services(self):
        # Email Service
        email_widget = EmailServerWidget(self.server)
        email_item = QListWidgetItem("Email")
        
        email_icon_path = os.path.join("GUI", "icons", "pc_email_unread.png")
        if os.path.exists(email_icon_path):
            email_item.setIcon(QIcon(email_icon_path))
            
        self.service_list.addItem(email_item)
        self.stacked_widget.addWidget(email_widget)
        
        # DNS Service
        dns_widget = DnsServerWidget(self.server)
        dns_item = QListWidgetItem("DNS")
        
        # Use terminal/settings or leave without specific icon for DNS
        self.service_list.addItem(dns_item)
        self.stacked_widget.addWidget(dns_widget)
