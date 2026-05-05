import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QPushButton, QLabel, QListWidget,
                             QMessageBox, QStackedWidget, QListWidgetItem, QTableWidget,
                             QTableWidgetItem, QHeaderView, QGroupBox, QCheckBox, QDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

_FIELD  = "background-color: white; border: 1px solid #7F9DB9; padding: 3px;"
_GROUP  = ("QGroupBox { font-weight: bold; border: 1px solid #7F9DB9; border-radius: 4px;"
           " margin-top: 12px; }"
           " QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
_BTN    = "background-color: #F0F0F0; border: 1px solid gray; padding: 2px 10px;"
_WIDGET = "background-color: #ECE9D8; color: black; font-family: Tahoma; font-size: 12px;"


class EmailServerWidget(QWidget):
    def __init__(self, host_device):
        super().__init__()
        self.server = host_device

        self.setStyleSheet(_WIDGET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)



        title = QLabel("Email Service Configuration")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        domain_group = QGroupBox("Domain Settings")
        domain_group.setStyleSheet(_GROUP)
        domain_layout = QHBoxLayout(domain_group)
        domain_layout.addWidget(QLabel("Domain Name:"))
        self.domain_input = QLineEdit(self.server.email_domain)
        self.domain_input.setStyleSheet(_FIELD)
        self.domain_input.setMinimumWidth(150)
        domain_layout.addWidget(self.domain_input)
        set_domain_btn = QPushButton("Set")
        set_domain_btn.setStyleSheet(_BTN)
        set_domain_btn.clicked.connect(self.set_domain)
        domain_layout.addWidget(set_domain_btn)
        layout.addWidget(domain_group)

        user_group = QGroupBox("User Accounts")
        user_group.setStyleSheet(_GROUP)
        user_group_layout = QVBoxLayout(user_group)

        user_form = QFormLayout()
        user_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        for box in [self.user_input, self.pass_input]:
            box.setStyleSheet(_FIELD)
            box.setMinimumWidth(150)
        user_form.addRow("User:", self.user_input)
        user_form.addRow("Password:", self.pass_input)
        user_group_layout.addLayout(user_form)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+")
        add_btn.setStyleSheet(_BTN)
        add_btn.clicked.connect(self.add_user)
        remove_btn = QPushButton("-")
        remove_btn.setStyleSheet(_BTN)
        remove_btn.clicked.connect(self.remove_user)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        user_group_layout.addLayout(btn_layout)

        self.user_list = QListWidget()
        self.user_list.setStyleSheet("background-color: white; border: 1px solid #7F9DB9;")
        user_group_layout.addWidget(self.user_list)
        layout.addWidget(user_group)


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
            
        if user in self.server.email_users:
            QMessageBox.warning(self, "Error", "User already exists.")
            return
            
        self.server.email_users[user] = {"password": password, "inbox": []}
        self.user_input.clear()
        self.pass_input.clear()
        self.refresh_user_list()

    def remove_user(self):
        selected = self.user_list.currentItem()
        if not selected:
            return


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

        self.setStyleSheet(_WIDGET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)


        title = QLabel("DNS Service Configuration")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        group = QGroupBox("DNS Records")
        group.setStyleSheet(_GROUP)
        group_layout = QVBoxLayout(group)

        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.domain_input = QLineEdit()
        self.ip_input = QLineEdit()
        for box in [self.domain_input, self.ip_input]:
            box.setStyleSheet(_FIELD)
            box.setMinimumWidth(150)
        form_layout.addRow("Domain:", self.domain_input)
        form_layout.addRow("IP Address:", self.ip_input)
        group_layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Record")
        add_btn.setStyleSheet(_BTN)
        add_btn.clicked.connect(self.add_record)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setStyleSheet(_BTN)
        remove_btn.clicked.connect(self.remove_record)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        group_layout.addLayout(btn_layout)


        self.records_table = QTableWidget(0, 2)
        self.records_table.setHorizontalHeaderLabels(["Domain", "IP Address"])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.records_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.records_table.setStyleSheet("background-color: white; border: 1px solid #7F9DB9;")

        group_layout.addWidget(self.records_table)
        layout.addWidget(group)




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

class ExcludedAddressesDialog(QDialog):
    def __init__(self, server, parent=None):
        super().__init__(parent)
        self.server = server
        self.setWindowTitle("Manage Excluded Addresses")
        self.resize(350, 300)
        self.setStyleSheet(_WIDGET)
        
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background-color: white; border: 1px solid #7F9DB9;")
        
        cfg = self.server.services.setdefault("DHCP", {})
        self.excluded_list = cfg.setdefault("excluded_addresses", [])
        
        for exc in self.excluded_list:
            self.list_widget.addItem(exc)
            
        layout.addWidget(QLabel("Global Excluded IPs / Ranges:"))
        layout.addWidget(self.list_widget)
        
        form = QFormLayout()
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet(_FIELD)
        self.input_field.setPlaceholderText("e.g. 192.168.1.1 or 192.168.1.1-192.168.1.10")
        form.addRow("Address/Range:", self.input_field)
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.setStyleSheet(_BTN)
        add_btn.clicked.connect(self.add_address)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setStyleSheet(_BTN)
        remove_btn.clicked.connect(self.remove_address)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)
        
    def add_address(self):
        val = self.input_field.text().strip()
        if not val: return
        if val not in self.excluded_list:
            self.excluded_list.append(val)
            self.list_widget.addItem(val)
        self.input_field.clear()
        
    def remove_address(self):
        item = self.list_widget.currentItem()
        if not item: return
        val = item.text()
        if val in self.excluded_list:
            self.excluded_list.remove(val)
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)


class DhcpServerWidget(QWidget):
    def __init__(self, host_device):
        super().__init__()
        self.server = host_device
        self.setStyleSheet(_WIDGET)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        title = QLabel("DHCP Service Configuration")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        root.addWidget(title)

        svc_group = QGroupBox("Service")
        svc_group.setStyleSheet(_GROUP)
        svc_row = QHBoxLayout(svc_group)
        self.enabled_cb = QCheckBox("Enable DHCP Server")
        cfg = self.server.services.get("DHCP", {})
        self.enabled_cb.setChecked(cfg.get("enabled", False))
        svc_row.addWidget(self.enabled_cb)
        
        manage_exc_btn = QPushButton("Manage Excluded Addresses")
        manage_exc_btn.setStyleSheet(_BTN)
        manage_exc_btn.clicked.connect(self.open_excluded_dialog)
        svc_row.addWidget(manage_exc_btn)
        
        svc_row.addStretch()
        root.addWidget(svc_group)

        pool_group = QGroupBox("Address Pools")
        pool_group.setStyleSheet(_GROUP)
        pool_h = QHBoxLayout(pool_group)

        left_v = QVBoxLayout()
        self.pool_list = QListWidget()
        self.pool_list.setFixedWidth(110)
        self.pool_list.setStyleSheet(
            "QListWidget { background-color: white; border: 1px solid #7F9DB9; }"
            "QListWidget::item { padding: 4px; }"
            "QListWidget::item:selected { background-color: #316AC5; color: white; }"
        )
        left_v.addWidget(self.pool_list)

        pool_btn_row = QHBoxLayout()
        add_pool_btn = QPushButton("+")
        add_pool_btn.setStyleSheet(_BTN)
        add_pool_btn.setFixedWidth(36)
        add_pool_btn.setToolTip("Add pool")
        add_pool_btn.clicked.connect(self.add_pool)
        remove_pool_btn = QPushButton("−")
        remove_pool_btn.setStyleSheet(_BTN)
        remove_pool_btn.setFixedWidth(36)
        remove_pool_btn.setToolTip("Remove selected pool")
        remove_pool_btn.clicked.connect(self.remove_pool)
        pool_btn_row.addWidget(add_pool_btn)
        pool_btn_row.addWidget(remove_pool_btn)
        pool_btn_row.addStretch()
        left_v.addLayout(pool_btn_row)
        pool_h.addLayout(left_v)

        right_v = QVBoxLayout()
        detail_form = QFormLayout()
        detail_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.pool_name    = QLineEdit()
        self.pool_enabled = QCheckBox("Enabled")
        self.pool_start   = QLineEdit()
        self.pool_end     = QLineEdit()
        self.pool_subnet  = QLineEdit()
        self.pool_gateway = QLineEdit()
        self.pool_dns     = QLineEdit()

        for field in (self.pool_name, self.pool_start, self.pool_end,
                      self.pool_subnet, self.pool_gateway, self.pool_dns):
            field.setStyleSheet(_FIELD)

        detail_form.addRow("Pool Name:",       self.pool_name)
        detail_form.addRow("",                 self.pool_enabled)
        detail_form.addRow("Start IP:",        self.pool_start)
        detail_form.addRow("End IP:",          self.pool_end)
        detail_form.addRow("Subnet Mask:",     self.pool_subnet)
        detail_form.addRow("Default Gateway:", self.pool_gateway)
        detail_form.addRow("DNS Server:",      self.pool_dns)
        right_v.addLayout(detail_form)

        save_pool_btn = QPushButton("Save Pool")
        save_pool_btn.setStyleSheet(_BTN)
        save_pool_btn.clicked.connect(self.save_pool)
        right_v.addWidget(save_pool_btn)
        right_v.addStretch()
        pool_h.addLayout(right_v)
        root.addWidget(pool_group)

        save_all_btn = QPushButton("Save All Settings")
        save_all_btn.setStyleSheet(_BTN)
        save_all_btn.clicked.connect(self.save_all)
        root.addWidget(save_all_btn)

        leases_group = QGroupBox("Active Leases")
        leases_group.setStyleSheet(_GROUP)
        leases_v = QVBoxLayout(leases_group)

        self.leases_table = QTableWidget(0, 3)
        self.leases_table.setHorizontalHeaderLabels(["Device ID", "Pool", "Assigned IP"])
        self.leases_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.leases_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.leases_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.leases_table.setStyleSheet("background-color: white; border: 1px solid #7F9DB9;")
        leases_v.addWidget(self.leases_table)

        lease_btn_row = QHBoxLayout()
        release_btn = QPushButton("Release Selected")
        release_btn.setStyleSheet(_BTN)
        release_btn.clicked.connect(self.release_lease)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(_BTN)
        refresh_btn.clicked.connect(self.refresh_leases)
        lease_btn_row.addWidget(release_btn)
        lease_btn_row.addWidget(refresh_btn)
        lease_btn_row.addStretch()
        leases_v.addLayout(lease_btn_row)
        root.addWidget(leases_group)

        self.pool_list.currentRowChanged.connect(self._on_pool_selected)

        self._rebuild_pool_list()
        self.refresh_leases()

    def open_excluded_dialog(self):
        dialog = ExcludedAddressesDialog(self.server, self)
        dialog.exec()

    def _pools(self):
        return self.server.services.setdefault("DHCP", {}).setdefault("pools", {})

    def _rebuild_pool_list(self, select_key=None):
        self.pool_list.blockSignals(True)
        self.pool_list.clear()
        pools = self._pools()
        for gw, p_data in pools.items():
            item_text = p_data.get("name", f"Pool {gw}")
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, gw)
            self.pool_list.addItem(item)
        self.pool_list.blockSignals(False)
        
        if self.pool_list.count() > 0:
            if select_key:
                for i in range(self.pool_list.count()):
                    item = self.pool_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == select_key:
                        self.pool_list.setCurrentItem(item)
                        break
            else:
                self.pool_list.setCurrentRow(0)
            self._on_pool_selected()
        else:
            self._clear_detail_fields()

    def _clear_detail_fields(self):
        for w in (self.pool_name, self.pool_start, self.pool_end,
                  self.pool_subnet, self.pool_gateway, self.pool_dns):
            w.clear()
            w.setEnabled(True)
        self.pool_enabled.setChecked(False)

    def _on_pool_selected(self, *args):
        pools = self._pools()
        curr_item = self.pool_list.currentItem()
        if not curr_item:
            self._clear_detail_fields()
            return
            
        gw = curr_item.data(Qt.ItemDataRole.UserRole)
        p = pools.get(gw, {})
        self.pool_name.setText(p.get("name", ""))
        self.pool_enabled.setChecked(p.get("enabled", True))
        self.pool_start.setText(p.get("start_ip", ""))
        self.pool_end.setText(p.get("end_ip", ""))
        self.pool_subnet.setText(p.get("subnet_mask", "255.255.255.0"))
        self.pool_gateway.setText(gw)
        self.pool_dns.setText(p.get("dns_server", ""))
        
        self.pool_gateway.setEnabled(False)

    def add_pool(self):
        from PyQt6.QtWidgets import QInputDialog
        gateway, ok = QInputDialog.getText(self, "Add DHCP Pool", "Enter Default Gateway (unique):")
        if not ok or not gateway.strip():
            return
        gateway = gateway.strip()
        pools = self._pools()
        if gateway in pools:
            QMessageBox.warning(self, "Error", "A pool with this gateway already exists.")
            return
            
        pools[gateway] = {
            "name": f"Pool {len(pools) + 1}",
            "enabled": True,
            "start_ip": "192.168.1.100",
            "end_ip": "192.168.1.149",
            "subnet_mask": "255.255.255.0",
            "default_gateway": gateway,
            "dns_server": ""
        }
        self._rebuild_pool_list(select_key=gateway)

    def remove_pool(self):
        curr_item = self.pool_list.currentItem()
        if not curr_item:
            return
        gw = curr_item.data(Qt.ItemDataRole.UserRole)
        pools = self._pools()
        if gw in pools:
            pools.pop(gw)
            
        self._rebuild_pool_list()
        self.refresh_leases()

    def save_pool(self):
        curr_item = self.pool_list.currentItem()
        if not curr_item:
            return
        old_gw = curr_item.data(Qt.ItemDataRole.UserRole)
        pools = self._pools()
        if old_gw not in pools:
            return
            
        pools[old_gw].update({
            "name":            self.pool_name.text().strip() or f"Pool {old_gw}",
            "enabled":         self.pool_enabled.isChecked(),
            "start_ip":        self.pool_start.text().strip(),
            "end_ip":          self.pool_end.text().strip(),
            "subnet_mask":     self.pool_subnet.text().strip(),
            "default_gateway": old_gw, # Enforced
            "dns_server":      self.pool_dns.text().strip()
        })
        self._rebuild_pool_list(select_key=old_gw)

    def save_all(self):
        self.save_pool()
        self.server.services.setdefault("DHCP", {})["enabled"] = self.enabled_cb.isChecked()
        QMessageBox.information(self, "DHCP", "DHCP settings saved.")

    def refresh_leases(self):
        pools = self._pools()
        self.leases_table.setRowCount(0)
        for dev_id, lease in self.server.dhcp_leases.items():
            if isinstance(lease, dict):
                ip = lease.get("ip", "")
                gw = lease.get("gateway", "")
                pool_name = pools[gw].get("name", f"Pool {gw}") if gw in pools else "?"
            else:
                ip = str(lease)
                pool_name = "?"
            row = self.leases_table.rowCount()
            self.leases_table.insertRow(row)
            self.leases_table.setItem(row, 0, QTableWidgetItem(str(dev_id)))
            self.leases_table.setItem(row, 1, QTableWidgetItem(pool_name))
            self.leases_table.setItem(row, 2, QTableWidgetItem(ip))

    def release_lease(self):
        row = self.leases_table.currentRow()
        if row < 0:
            return
        dev_id = self.leases_table.item(row, 0).text()
        self.server.release_ip(dev_id)
        self.refresh_leases()

class ServicesWidget(QWidget):
    def __init__(self, host_device):
        super().__init__()
        self.server = host_device
        self.resize(750, 600)
        self.setStyleSheet(_WIDGET)

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


        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #ECE9D8;")

        self.init_services()

        main_layout.addWidget(self.service_list)
        main_layout.addWidget(self.stacked_widget)


        self.service_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        if self.service_list.count() > 0:
            self.service_list.setCurrentRow(0)

    def init_services(self):
        email_widget = EmailServerWidget(self.server)
        email_item = QListWidgetItem("Email")
        email_icon_path = os.path.join("GUI", "icons", "pc_email_unread.png")
        if os.path.exists(email_icon_path):
            email_item.setIcon(QIcon(email_icon_path))
        self.service_list.addItem(email_item)
        self.stacked_widget.addWidget(email_widget)

        dns_widget = DnsServerWidget(self.server)
        dns_item = QListWidgetItem("DNS")
        self.service_list.addItem(dns_item)
        self.stacked_widget.addWidget(dns_widget)

        dhcp_widget = DhcpServerWidget(self.server)
        dhcp_item = QListWidgetItem("DHCP")
        self.service_list.addItem(dhcp_item)
        self.stacked_widget.addWidget(dhcp_widget)
