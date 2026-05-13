import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QStatusBar, 
                             QFileDialog, QWidget, QHBoxLayout, QDockWidget)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from GUI.canvas import NetworkCanvas, DeviceNode, CableNode
from GUI.ai_helper import NetworkAssistantWidget

from Devices.pc import PC
from Devices.laptop import Laptop
from Devices.server import Server
from Devices.router2911 import Router2911
from Devices.switch2960 import Switch2960
from Devices.wireless_router import WirelessRouter
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
        self._setup_ai_dock()
    def _setup_ai_dock(self):
        self.ai_dock = QDockWidget("AI Topology Assistant", self)
        self.ai_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.ai_assistant = NetworkAssistantWidget(self.canvas)
        self.ai_dock.setWidget(self.ai_assistant)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ai_dock)
        self.ai_dock.hide() 

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

        for act in ["Add PC", "Add Laptop", "Add Server", "Add Router", "Add Switch", "Add Wireless Router"]:

            action = QAction(act, self)
            action.triggered.connect(lambda checked, a=act: self.canvas.set_mode('device', a.replace("Add ", "")))
            toolbar.addAction(action)

        toolbar.addSeparator()

        for cable in ["Straight-Through", "Cross-Over", "Console"]:
            action = QAction(f"Cable: {cable}", self)
            action.triggered.connect(lambda checked, c=cable: self.canvas.set_mode('cable', c))
            toolbar.addAction(action)

        toolbar.addSeparator()

        ai_toggle_act = QAction("Ask AI", self)
        ai_toggle_act.triggered.connect(self.toggle_ai_dock)
        ai_toggle_act.setCheckable(True)
        self.ai_toggle_action = ai_toggle_act
        toolbar.addAction(ai_toggle_act)

    def toggle_ai_dock(self):
        if self.ai_dock.isVisible():
            self.ai_dock.hide()
        else:
            self.ai_dock.show()
            self.ai_dock.raise_()

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

        self.canvas.import_topology(data)
        self.status.showMessage("Topology loaded successfully.")
