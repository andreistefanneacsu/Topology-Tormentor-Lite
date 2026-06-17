import os
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt

from Devices.interface import Interface
from GUI.desktop import DesktopEnvironment
from GUI.cli_app import CLIWidget

class DeviceWindow(QDialog):
    HOST_MODULES = {
        "PT-HOST-NM-1CFE": ["RS232", "FastEthernet0"],
        "PT-HOST-NM-1CGE": ["RS232", "GigabitEthernet0"]
    }

    ROUTER_HWIC_PORTS = [
        ["Serial0/0/0", "Serial0/0/1"],
        ["Serial0/1/0", "Serial0/1/1"],
        ["Serial0/2/0", "Serial0/2/1"],
        ["Serial0/3/0", "Serial0/3/1"]
    ]

    def __init__(self, device, canvas=None):
        super().__init__(canvas)
        from GUI.gui import MODERN_STYLE
        self.setStyleSheet(MODERN_STYLE)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.device = device
        self.canvas = canvas
        self.desktop_widget = None
        self.cli_widget = None

        self.setWindowTitle(f"{device.type} Window - {device.name}")
        self.resize(840, 620)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.main_layout.addWidget(self.tabs)

        self.physical_tab = QWidget()
        self.tabs.addTab(self.physical_tab, "Physical")
        self.setup_physical_tab()

        if self.device.type in ["PC", "Laptop", "Server"]:
            self.desktop_tab = QWidget()
            self.tabs.addTab(self.desktop_tab, "Desktop")
            self.setup_desktop_tab()
        elif self.device.type in ["Router", "Switch"]:
            self.cli_tab = QWidget()
            self.tabs.addTab(self.cli_tab, "CLI")
            self.setup_cli_tab()

    def setup_physical_tab(self):
        layout = QVBoxLayout(self.physical_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        info_group = QGroupBox("Device Information")
        info_layout = QFormLayout(info_group)
        info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        info_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        self.name_label = QLabel(self.device.name)
        self.type_label = QLabel(self.device.type)
        self.module_combo = QComboBox()

        if self.device.type in ["PC", "Laptop", "Server"]:
            self.module_combo.addItems(self.HOST_MODULES.keys())
            if not hasattr(self.device, "nic_module") or self.device.nic_module not in self.HOST_MODULES:
                self.device.nic_module = list(self.HOST_MODULES.keys())[0]
            self.module_combo.setCurrentText(self.device.nic_module)
            self.module_combo.currentTextChanged.connect(self.on_module_changed)
            info_layout.addRow("NIC Module:", self.module_combo)
        else:
            self.module_combo.setEnabled(False)

        info_layout.addRow("Name:", self.name_label)
        info_layout.addRow("Type:", self.type_label)

        self.card_label = QLabel(self.get_card_description())
        self.ports_label = QLabel(self.get_ports_description())
        info_layout.addRow("Card:", self.card_label)
        info_layout.addRow("Ports:", self.ports_label)

        layout.addWidget(info_group)

        self.interfaces_table = QTableWidget(0, 5)
        self.interfaces_table.setHorizontalHeaderLabels(["Interface", "IP Address", "Subnet", "Description", "Status"])
        self.interfaces_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.interfaces_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.interfaces_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked)
        self.interfaces_table.verticalHeader().setVisible(False)
        self.interfaces_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.interfaces_table)

        if self.device.type == "Switch":
            vlan_layout = QHBoxLayout()
            self.vlan_input = QComboBox()
            self.vlan_input.setEditable(True)
            self.vlan_input.setMinimumWidth(80)
            self.vlan_input.setMinimumHeight(28)
            self.vlan_input.addItems([str(i) for i in range(2, 11)])
            self.add_vlan_btn = QPushButton("Add VLAN")
            self.add_vlan_btn.clicked.connect(self.create_vlan)
            vlan_layout.addWidget(QLabel("VLAN ID:"))
            vlan_layout.addWidget(self.vlan_input)
            vlan_layout.addWidget(self.add_vlan_btn)
            vlan_layout.addStretch()
            layout.addLayout(vlan_layout)

        if self.device.type == "Router":
            hwic_layout = QHBoxLayout()
            self.hwic_info_label = QLabel(self.get_hwic_description())
            self.add_hwic_btn = QPushButton("Add HWIC-2T Module")
            self.add_hwic_btn.clicked.connect(self.add_hwic_module)
            self.remove_hwic_btn = QPushButton("Remove HWIC-2T Module")
            self.remove_hwic_btn.clicked.connect(self.remove_hwic_module)
            hwic_layout.addWidget(self.hwic_info_label)
            hwic_layout.addWidget(self.add_hwic_btn)
            hwic_layout.addWidget(self.remove_hwic_btn)
            hwic_layout.addStretch()
            layout.addLayout(hwic_layout)


        if self.device.type in ["PC", "Laptop", "Server"]:
            if not hasattr(self.device, "nic_module") or self.device.nic_module not in self.HOST_MODULES:
                self.device.nic_module = list(self.HOST_MODULES.keys())[0]
            self.rebuild_host_interfaces(self.device.nic_module)
        elif self.device.type == "Router":
            if not self.device.interfaces:
                self.initialize_router_interfaces()
            if "Console" not in self.device.interfaces:
                self.device.interfaces["Console"] = Interface("Console", is_console=True)
        elif self.device.type == "Switch":
            if not self.device.interfaces:
                for i in range(0, 25):
                    self.device.interfaces[f"fastEthernet 0/{i}"] = Interface(f"fastEthernet 0/{i}")
                self.device.interfaces["gigabitEthernet 0/1"] = Interface("gigabitEthernet 0/1")
                self.device.interfaces["gigabitEthernet 0/2"] = Interface("gigabitEthernet 0/2")
                self.device.interfaces["Vlan1"] = Interface("Vlan1")
            if "Console" not in self.device.interfaces:
                self.device.interfaces["Console"] = Interface("Console", is_console=True)

        self.populate_interface_table()
        self.update_physical_info()

    def setup_desktop_tab(self):
        layout = QVBoxLayout(self.desktop_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.desktop_widget = DesktopEnvironment(self.device, self.canvas)
        self.desktop_widget.setParent(self.desktop_tab)
        self.desktop_widget.setWindowFlags(Qt.WindowType.Widget)
        self.desktop_widget.resize(820, 520)
        layout.addWidget(self.desktop_widget)

    def setup_cli_tab(self):
        layout = QVBoxLayout(self.cli_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.cli_widget = CLIWidget(self.device)
        layout.addWidget(self.cli_widget)

    def on_module_changed(self, module_name):
        self.device.nic_module = module_name
        self.rebuild_host_interfaces(module_name)
        self.populate_interface_table()
        self.update_physical_info()

    def rebuild_host_interfaces(self, module_name):
        module_ports = self.HOST_MODULES.get(module_name, [])

        existing_ifaces = dict(self.device.interfaces)

        for name in module_ports:
            if name not in existing_ifaces:
                is_console = (name == "RS232")
                existing_ifaces[name] = Interface(name, is_console=is_console)

        if "RS232" not in existing_ifaces:
            existing_ifaces["RS232"] = Interface("RS232", is_console=True)

        if self.device.type == "Laptop" and "Wireless0" not in existing_ifaces:
            w = Interface("Wireless0", is_console=False)
            w.is_wireless = True
            existing_ifaces["Wireless0"] = w

        ports_to_remove = []
        for name in list(existing_ifaces.keys()):
            if name in module_ports or name in ("RS232", "Wireless0"):
                continue
            ports_to_remove.append(name)

        if hasattr(self, 'canvas') and getattr(self.canvas, 'links', None) is not None:
            links_to_remove = []
            for link in list(self.canvas.links):
                if (link.interface1.get("device_id") == self.device.id and link.interface1.get("port") in ports_to_remove) or \
                   (link.interface2.get("device_id") == self.device.id and link.interface2.get("port") in ports_to_remove):
                    links_to_remove.append(link)
            
            for link in links_to_remove:
                self.canvas.links.remove(link)
                
                cables_to_remove = []
                for scene_item in self.canvas.scene.items():
                    if hasattr(scene_item, '__class__') and scene_item.__class__.__name__ == 'CableNode':
                        dev1_id = link.interface1.get("device_id")
                        dev2_id = link.interface2.get("device_id")
                        node1_device_id = scene_item.node1.device.id if hasattr(scene_item, 'node1') else None
                        node2_device_id = scene_item.node2.device.id if hasattr(scene_item, 'node2') else None
                        
                        match_1 = (node1_device_id == dev1_id and node2_device_id == dev2_id)
                        match_2 = (node1_device_id == dev2_id and node2_device_id == dev1_id)
                        
                        if (match_1 or match_2) and scene_item.cable_type == link.cable_type:
                            cables_to_remove.append(scene_item)
                
                for cable in cables_to_remove:
                    self.canvas.scene.removeItem(cable)

        for p in ports_to_remove:
            existing_ifaces.pop(p, None)

        self.device.interfaces.clear()
        for k, v in existing_ifaces.items():
            self.device.interfaces[k] = v

    def initialize_router_interfaces(self):
        base_ports = [f"gigabitEthernet 0/{i}" for i in range(3)]
        for name in base_ports:
            self.device.interfaces[name] = Interface(name)

    def get_hwic_description(self):
        count = self.count_router_hwic()
        return f"HWIC-2T modules installed: {count}/4"

    def count_router_hwic(self):
        return sum(1 for name in self.device.interfaces if name.startswith("Serial0/") and name.count("/") == 2) // 2

    def create_vlan(self):
        vlan_id = self.vlan_input.currentText().strip()
        if not vlan_id.isdigit():
            QMessageBox.warning(self, "Invalid VLAN", "Please enter a numeric VLAN ID.")
            return
        vlan_name = f"Vlan{vlan_id}"
        if vlan_name in self.device.interfaces:
            QMessageBox.information(self, "VLAN Exists", f"{vlan_name} already exists.")
            return
        self.device.interfaces[vlan_name] = Interface(vlan_name)
        self.populate_interface_table()
        self.update_physical_info()
        QMessageBox.information(self, "VLAN Created", f"{vlan_name} was added successfully.")

    def add_hwic_module(self):
        installed = self.count_router_hwic()
        if installed >= len(self.ROUTER_HWIC_PORTS):
            QMessageBox.warning(self, "HWIC Limit", "You can only install up to 4 HWIC-2T modules.")
            return
        for name in self.ROUTER_HWIC_PORTS[installed]:
            self.device.interfaces[name] = Interface(name)
        self.hwic_info_label.setText(self.get_hwic_description())
        self.populate_interface_table()
        self.update_physical_info()
        QMessageBox.information(self, "Module Added", "HWIC-2T module added and serial ports created.")

    def remove_hwic_module(self):
        installed = self.count_router_hwic()
        if installed == 0:
            QMessageBox.warning(self, "No Modules", "There are no HWIC-2T modules installed to remove.")
            return

        last_index = installed - 1
        removed_ports = self.ROUTER_HWIC_PORTS[last_index]
        for port in removed_ports:
            self.device.interfaces.pop(port, None)

        self.hwic_info_label.setText(self.get_hwic_description())
        self.populate_interface_table()
        self.update_physical_info()
        QMessageBox.information(self, "Module Removed", "The most recently installed HWIC-2T module has been removed.")

    def get_card_description(self):
        if self.device.type in ["PC", "Laptop", "Server"]:
            return self.device.nic_module
        if self.device.type == "Router":
            return f"Router chassis with {self.count_router_hwic()} HWIC-2T module(s)"
        if self.device.type == "Switch":
            return "Default switch module"
        return "Standard device"

    def get_ports_description(self):
        interfaces = [iface for name, iface in self.device.interfaces.items() if not getattr(iface, "is_console", False)]
        total = len(interfaces)
        active = sum(1 for iface in interfaces if iface.is_up)
        return f"{total} total, {active} active, {total - active} inactive"

    def populate_interface_table(self):
        self.interfaces_table.setRowCount(0)
        for interface_name, interface in self.device.interfaces.items():
            if getattr(interface, "is_console", False):
                continue
            row = self.interfaces_table.rowCount()
            self.interfaces_table.insertRow(row)

            item_iface = QTableWidgetItem(interface_name)
            item_iface.setFlags(item_iface.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.interfaces_table.setItem(row, 0, item_iface)
            self.interfaces_table.setItem(row, 1, QTableWidgetItem(interface.ip))
            self.interfaces_table.setItem(row, 2, QTableWidgetItem(interface.subnet))
            self.interfaces_table.setItem(row, 3, QTableWidgetItem(interface.description))
            self.interfaces_table.setItem(row, 4, QTableWidgetItem("Up" if interface.is_up else "Down"))

    def update_physical_info(self):
        self.card_label.setText(self.get_card_description())
        self.ports_label.setText(self.get_ports_description())

    def on_tab_changed(self, index):
        if self.tabs.tabText(index) == "Desktop" and self.device.type in ["PC", "Laptop", "Server"]:
            if self.desktop_widget is None:
                self.setup_desktop_tab()
