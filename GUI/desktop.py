import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QMenu, QMdiArea, QToolButton, QLabel)
from PyQt6.QtGui import QColor, QBrush, QAction, QIcon, QPixmap
from PyQt6.QtCore import Qt, QTime, QTimer, QSize

from GUI.ip_config import IPConfigWidget
from GUI.cmd_app import CmdWidget
from GUI.cli_app import CLIWidget
from GUI.notepad import NotepadWidget
from GUI.calculator import CalculatorWidget
from GUI.services_server_app import ServicesWidget
from GUI.email_client_app import EmailClientWidget
from GUI.web_browser_app import WebBrowserWidget
from GUI.wifi_app import WifiAppWidget


class DesktopEnvironment(QMainWindow):
    def __init__(self, device, canvas):
        super().__init__()
        self.device = device
        self.canvas = canvas
        self.setWindowTitle(f"Windows XP - {self.device.name}")
        self.setMinimumSize(600, 400)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.mdi = QMdiArea()
        self.mdi.setBackground(QBrush(QColor("#245EDC")))
        layout.addWidget(self.mdi)

        self.taskbar = QWidget()
        self.taskbar.setFixedHeight(40)
        self.taskbar.setStyleSheet("background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #245EDC, stop:1 #173E98); border-top: 1px solid #111;")
        taskbar_layout = QHBoxLayout(self.taskbar)
        taskbar_layout.setContentsMargins(2, 2, 2, 2)
        taskbar_layout.setSpacing(5)

        self.start_btn = QPushButton() 
        self.start_btn.setFixedSize(100, 35)
        
        start_icon_path = os.path.join("GUI", "icons", "start.png")
        if os.path.exists(start_icon_path):
            self.start_btn.setIcon(QIcon(start_icon_path))
            self.start_btn.setIconSize(QSize(100, 35)) 

        self.start_btn.setStyleSheet("""
            QPushButton { 
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:pressed { 
                margin-top: 1px; 
                margin-left: 1px;
            }
        """)
        taskbar_layout.addWidget(self.start_btn)

        self.window_buttons_layout = QHBoxLayout()
        self.window_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        taskbar_layout.addLayout(self.window_buttons_layout)
        taskbar_layout.addStretch()

        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: white; font-weight: bold; padding-right: 15px; font-size: 14px;")
        taskbar_layout.addWidget(self.time_label)
        self.update_time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        layout.addWidget(self.taskbar)

        self.setup_apps()
        self.setup_start_menu()
        self.setup_desktop_icons()

    def update_time(self):
        self.time_label.setText(QTime.currentTime().toString("hh:mm A"))

    def load_icon(self, filename):
        path = os.path.join("GUI", "icons", filename)
        if os.path.exists(path):
            return QIcon(path)
        return QIcon()

    def setup_apps(self):
        self.available_apps = [
            {"name": "Command\nPrompt", "icon_file": "cmd.png", "factory": lambda: CmdWidget(self.device, self.canvas.devices, self.canvas.links)},
            {"name": "IP Config", "icon_file": "settings.png", "factory": lambda: IPConfigWidget(self.device, self.canvas.devices, self.canvas.links)},
            {"name": "Notepad", "icon_file": "notepad.png", "factory": NotepadWidget},
            {"name": "Calculator", "icon_file": "calculator.png", "factory": CalculatorWidget}
        ]
        if self.device.type in ["PC", "Laptop"]:
            self.available_apps.append({"name": "Email", "icon_file": "pc_email_unread.png", "factory": lambda: EmailClientWidget(self.device, self.canvas.devices, self.canvas.links)})
            self.available_apps.append({"name": "Web\nBrowser", "icon_file": "browser.png", "factory": lambda: WebBrowserWidget(self.device, self.canvas.devices, self.canvas.links)})
        if self.device.type == "Server":
            self.available_apps.append({"name": "Services", "icon_file": "services.png", "factory": lambda: ServicesWidget(self.device)})
            

        if self.device.type == "Laptop":
            self.available_apps.append({"name": "Terminal", "icon_file": "terminal.png", "factory": lambda: CLIWidget(self.device)})
            self.available_apps.append({"name": "WiFi App", "icon_file": "wireless.png", "factory": lambda: WifiAppWidget(self.device, self.canvas)})

    def setup_start_menu(self):
        self.start_menu = QMenu(self)
        self.start_menu.setStyleSheet("""
            QMenu { background-color: white; border: 2px solid #245EDC; border-top-right-radius: 10px; }
            QMenu::item { padding: 12px 40px 12px 10px; font-weight: bold; font-size: 14px; color: black;}
            QMenu::item:selected { background-color: #245EDC; color: white; }
        """)
        for app in self.available_apps:
            action = QAction(self.load_icon(app["icon_file"]), app["name"].replace("\n", " "), self)
            action.triggered.connect(lambda checked, a=app: self.launch_app(a))
            self.start_menu.addAction(action)
            
        self.start_btn.clicked.connect(self.show_start_menu)

    def show_start_menu(self):
        menu_height = self.start_menu.sizeHint().height()
        pos = self.start_btn.mapToGlobal(self.start_btn.rect().topLeft())
        pos.setY(pos.y() - menu_height)
        self.start_menu.exec(pos)

    def setup_desktop_icons(self):
        x, y = 20, 20
        for app in self.available_apps:
            btn = QToolButton(self.mdi.viewport())
            
            btn.setIcon(self.load_icon(app["icon_file"]))
            btn.setIconSize(QSize(48, 48))
            btn.setText(app["name"])
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            
            btn.setFixedSize(80, 90)
            btn.setStyleSheet("""
                QToolButton { 
                    color: white; font-weight: bold; font-family: Tahoma; font-size: 11px;
                    background: transparent; border: none; padding-top: 5px;
                } 
                QToolButton:hover { 
                    background-color: rgba(255,255,255,50); border: 1px dotted white; border-radius: 3px;
                }
            """)
            
            btn.move(x, y)
            btn.clicked.connect(lambda checked, a=app: self.launch_app(a))
            
            y += 100
            if y > 500:
                y = 20; x += 100

    def launch_app(self, app_data):
        app_name = app_data["name"].replace("\n", " ")
        if app_name in ["IP Config", "Email", "Services", "WiFi App"]:
            for sub in self.mdi.subWindowList():
                if sub.windowTitle() == app_name:
                    self.mdi.setActiveSubWindow(sub)
                    sub.showNormal()
                    sub.raise_()
                    return
        widget = app_data["factory"]()
        sub = self.mdi.addSubWindow(widget)
        sub.setWindowTitle(app_data["name"].replace("\n", " ")) 
        sub.resize(widget.width(), widget.height())
        
        sub.setWindowIcon(self.load_icon(app_data["icon_file"]))
        sub.show()

        btn = QPushButton(app_data["name"].replace("\n", " "))
        btn.setFixedSize(140, 30)
        btn.setIcon(self.load_icon(app_data["icon_file"]))
        btn.setStyleSheet("QPushButton { background-color: #3B72E4; color: white; border: 1px solid #173E98; border-radius: 3px; font-weight: bold; text-align: left; padding-left: 5px; } QPushButton:pressed { background-color: #173E98; }")
        
        btn.clicked.connect(lambda: self.mdi.setActiveSubWindow(sub))
        self.window_buttons_layout.addWidget(btn)
        sub.destroyed.connect(lambda: btn.deleteLater())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10, self.update_bg)

    def update_bg(self):
        from PyQt6.QtGui import QPixmap, QBrush
        from PyQt6.QtCore import Qt
        import os
        bg_path = os.path.join("GUI", "bg.jpg")
        if os.path.exists(bg_path) and hasattr(self, 'mdi') and self.mdi.size().width() > 0:
            pixmap = QPixmap(bg_path).scaled(
                self.mdi.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.mdi.setBackground(QBrush(pixmap))