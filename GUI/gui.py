import sys
import json
from PyQt6.QtWidgets import QApplication, QMainWindow, QToolBar, QStatusBar, QFileDialog
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from GUI.canvas import NetworkCanvas, DeviceNode, CableNode

from Devices.pc import PC
from Devices.laptop import Laptop
from Devices.router2911 import Router2911
from Devices.switch2960 import Switch2960
from Devices.link import Link

MODERN_STYLE = """
QMainWindow { background-color: #1E1E2E; }
QMenuBar { background-color: #181825; color: #CDD6F4; font-size: 14px; padding: 4px; }
QMenuBar::item:selected { background-color: #313244; border-radius: 4px; }
QMenu { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; }
QMenu::item:selected { background-color: #89B4FA; color: #11111B; }
QToolBar { background-color: #181825; border: none; padding: 5px; spacing: 10px; }
QToolButton { color: #CDD6F4; font-weight: bold; padding: 6px 12px; border-radius: 6px; background-color: transparent; }
QToolButton:hover { background-color: #313244; }
QStatusBar { background-color: #181825; color: #A6ADC8; font-weight: bold; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TTL-Topology Tormentor Lite")
        self.resize(1280, 800)
        
        self.canvas = NetworkCanvas(self)
        self.setCentralWidget(self.canvas)
        
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.canvas.status_message.connect(self.status.showMessage)
        
        self._create_menus()
        self._create_toolbar()

    def _create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        save_act = QAction("Save Topology", self)
        save_act.triggered.connect(self.save_topology)
        file_menu.addAction(save_act)
        
        load_act = QAction("Load Topology", self)
        load_act.triggered.connect(self.load_topology)
        file_menu.addAction(load_act)

    def _create_toolbar(self):
        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        for act in ["Add PC", "Add Laptop", "Add Router", "Add Switch"]:
            action = QAction(act, self)
            action.triggered.connect(lambda checked, a=act: self.canvas.set_mode('device', a.split()[1]))
            toolbar.addAction(action)

        toolbar.addSeparator()

        for cable in ["Straight-Through", "Cross-Over", "Console"]:
            action = QAction(f"Cable: {cable}", self)
            action.triggered.connect(lambda checked, c=cable: self.canvas.set_mode('cable', c))
            toolbar.addAction(action)

    def save_topology(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Topology", "", "JSON Files (*.json)")
        if not filename: return

        for item in self.canvas.scene.items():
            if isinstance(item, DeviceNode):
                item.device._x = item.scenePos().x()
                item.device._y = item.scenePos().y()

        data = {
            "devices": [d.to_dict() for d in self.canvas.devices],
            "links": [l.to_dict() for l in self.canvas.links]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        self.status.showMessage(f"Topology saved successfully to {filename}")

    def load_topology(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Topology", "", "JSON Files (*.json)")
        if not filename: return

        with open(filename, 'r') as f:
            data = json.load(f)

        self.canvas.clear_canvas()

        dev_classes = {"PC": PC, "Laptop": Laptop, "Router": Router2911, "Switch": Switch2960}
        id_to_device = {}

        for dev_data in data.get("devices", []):
            dtype = dev_data.get("type")
            if dtype in dev_classes:
                backend_dev = dev_classes[dtype](dev_data.get("name"))
                backend_dev.from_dict(dev_data)
                
                self.canvas.devices.append(backend_dev)
                id_to_device[backend_dev.id] = backend_dev
                
                node = DeviceNode(backend_dev, self.canvas)
                node.setPos(backend_dev._x, backend_dev._y)
                self.canvas.scene.addItem(node)

        for link_data in data.get("links", []):
            d1 = id_to_device.get(link_data["interface1"]["device_id"])
            d2 = id_to_device.get(link_data["interface2"]["device_id"])
            
            if d1 and d2:
                link = Link(d1, link_data["interface1"]["port"], d2, link_data["interface2"]["port"], link_data["cable_type"])
                link.from_dict(link_data)
                self.canvas.links.append(link)

                if link.cable_type == "Console":
                    laptop = d1 if d1.type == "Laptop" else d2
                    target = d2 if d1.type == "Laptop" else d1
                    if hasattr(laptop, 'connect_serial'):
                        laptop.connect_serial(target)

                node1 = self.canvas.get_node_by_device(d1)
                node2 = self.canvas.get_node_by_device(d2)
                
                if node1 and node2:
                    cable = CableNode(node1, node2, link.cable_type)
                    self.canvas.scene.addItem(cable)

        self.status.showMessage("Topology loaded successfully.")