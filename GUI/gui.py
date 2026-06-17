import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QStatusBar, 
                             QFileDialog, QWidget, QHBoxLayout, QDockWidget, QDialog, QComboBox, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QListWidget, QListWidgetItem, QFormLayout, QRadioButton, QGroupBox, QStackedWidget)
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
QMainWindow, QDialog { background-color: #1E1E2E; color: #CDD6F4; }
QLabel { color: #CDD6F4; }
QLineEdit { background-color: #313244; color: #CDD6F4; border: 1px solid #45475A; padding: 5px; border-radius: 4px; }
QComboBox { background-color: #313244; color: #CDD6F4; border: 1px solid #45475A; padding: 5px; border-radius: 4px; }
QComboBox QAbstractItemView { background-color: #313244; color: #CDD6F4; selection-background-color: #89B4FA; }
QRadioButton { color: #CDD6F4; }
QGroupBox { color: #89B4FA; border: 1px solid #45475A; margin-top: 20px; padding-top: 10px; border-radius: 4px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 5px; top: 0px; }
QMenuBar { background-color: #181825; color: #CDD6F4; font-size: 14px; padding: 4px; }
QMenuBar::item:selected { background-color: #313244; border-radius: 4px; }
QMenu { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; }
QMenu::item:selected { background-color: #89B4FA; color: #11111B; }
QToolBar { background-color: #181825; border: none; padding: 5px; spacing: 10px; }
QToolButton { color: #CDD6F4; font-weight: bold; padding: 6px 12px; border-radius: 6px; background-color: transparent; }
QToolButton:hover { background-color: #313244; }
QStatusBar { background-color: #181825; color: #A6ADC8; font-weight: bold; }
QTabWidget::pane { background-color: #1E1E2E; border: none; }
QTabBar::tab { background-color: #181825; color: #CDD6F4; padding: 10px; border: 1px solid #313244; }
QTabBar::tab:selected { background-color: #313244; color: #89B4FA; font-weight: bold; }
QScrollArea { border: none; background-color: transparent; }
QTableWidget { background-color: #1E1E2E; color: #CDD6F4; gridline-color: #45475A; border: 1px solid #45475A; }
QHeaderView::section { background-color: #313244; color: #CDD6F4; padding: 4px; border: 1px solid #45475A; }
"""

from GUI.ai_config_manager import get_ai_config, save_ai_config
from PyQt6.QtWidgets import QListWidget, QInputDialog, QFormLayout, QRadioButton, QGroupBox, QStackedWidget, QProgressDialog
from PyQt6.QtCore import QThread, pyqtSignal
import os
import time
import subprocess
import urllib.request

class AIInstallerWorker(QThread):
    progress = pyqtSignal(int, str)
    finished_install = pyqtSignal(bool, str)

    def run(self):
        # Calculate hidden directory path
        base_dir = os.path.dirname(os.path.dirname(__file__))
        hidden_dir = os.path.join(base_dir, ".topology_tormentor", "downloads")
        os.makedirs(hidden_dir, exist_ok=True)

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.check_output(["ollama", "--version"], startupinfo=startupinfo)
            self.progress.emit(10, "Ollama is installed.")
        except Exception:
            self.progress.emit(0, "Downloading Ollama...")
            exe_path = os.path.join(hidden_dir, "OllamaSetup.exe")
            try:
                def reporthook(blocknum, blocksize, totalsize):
                    readsofar = blocknum * blocksize
                    if totalsize > 0:
                        percent = readsofar * 40 / totalsize
                        self.progress.emit(int(percent), "Downloading Ollama...")

                urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", exe_path, reporthook)
                self.progress.emit(40, "Installing Ollama silently...")
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run([exe_path, "/S"], check=True, startupinfo=startupinfo)
                
                time.sleep(5)
                self.progress.emit(50, "Ollama installed successfully.")
            except Exception as e:
                self.finished_install.emit(False, f"Failed to install Ollama: {str(e)}")
                return
            
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(["ollama", "list"], startupinfo=startupinfo).decode("utf-8")
            if "network-assistant-ultimate" in output:
                self.progress.emit(100, "All dependencies are installed.")
                self.finished_install.emit(True, "Success")
                return
        except Exception as e:
            self.finished_install.emit(False, f"Failed to check models: {str(e)}")
            return
            
        model_url = "https://huggingface.co/iamandreistef/qwen-2.5-coder-7b-instruct-network-assistant-ultimate-gguf/resolve/main/qwen2.5-coder-7b-instruct.Q4_K_M.gguf"
        modelfile_url = "https://huggingface.co/iamandreistef/qwen-2.5-coder-7b-instruct-network-assistant-ultimate-gguf/resolve/main/Modelfile"
        
        gguf_path = os.path.join(hidden_dir, "qwen2.5-coder-7b-instruct.Q4_K_M.gguf")
        modelfile_path = os.path.join(hidden_dir, "Modelfile")
        
        self.progress.emit(50, "Downloading model...")
        try:
            def model_reporthook(blocknum, blocksize, totalsize):
                readsofar = blocknum * blocksize
                if totalsize > 0:
                    percent = 50 + (readsofar * 40 / totalsize)
                    self.progress.emit(int(percent), "Downloading model (this may take a while)...")

            urllib.request.urlretrieve(model_url, gguf_path, model_reporthook)
            
            self.progress.emit(90, "Downloading Modelfile...")
            urllib.request.urlretrieve(modelfile_url, modelfile_path)
            
            self.progress.emit(92, "Loading model into Ollama...")
            
            # Read the downloaded Modelfile and modify the FROM line to point to our local gguf_path
            with open(modelfile_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            with open(modelfile_path, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.strip().startswith("FROM"):
                        f.write(f'FROM "{gguf_path}"\n')
                    else:
                        f.write(line)
                
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(["ollama", "create", "network-assistant-ultimate", "-f", modelfile_path], check=True, startupinfo=startupinfo)
            
            try:
                os.remove(modelfile_path)
                os.remove(gguf_path)
            except: pass
            
            self.progress.emit(100, "Model installed successfully.")
            self.finished_install.emit(True, "Success")
        except Exception as e:
            self.finished_install.emit(False, f"Failed to install model: {str(e)}")

class AISettingsDialog(QDialog):
    def __init__(self, parent=None, user_id="default"):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("AI Profile Manager")
        self.setStyleSheet(MODERN_STYLE)
        self.setFixedSize(650, 450)
        
        self.config = get_ai_config(self.user_id)
        self.profiles = self.config.get("profiles", [])
        self.active_profile = self.config.get("active_profile", "")
        
        main_layout = QHBoxLayout(self)
        
        # Left side - List of profiles
        left_layout = QVBoxLayout()
        self.profile_list = QListWidget()
        self.profile_list.setStyleSheet("background-color: #313244; color: #CDD6F4; border: none; border-radius: 4px;")
        self.profile_list.itemClicked.connect(self.load_profile_details)
        left_layout.addWidget(self.profile_list)
        
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_del = QPushButton("Delete")
        self.btn_add.clicked.connect(self.add_profile)
        self.btn_del.clicked.connect(self.del_profile)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        left_layout.addLayout(btn_layout)
        
        main_layout.addLayout(left_layout, 1)
        
        # Right side - Profile details
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        
        # Type selection
        type_group = QGroupBox("Profile Type")
        type_group.setStyleSheet("color: #CDD6F4;")
        type_layout = QHBoxLayout(type_group)
        self.rb_local = QRadioButton("Local (Ollama)")
        self.rb_online = QRadioButton("Online (Cloud API)")
        self.rb_local.toggled.connect(self.toggle_type)
        type_layout.addWidget(self.rb_local)
        type_layout.addWidget(self.rb_online)
        self.right_layout.addWidget(type_group)
        
        # Common fields
        self.form_layout = QFormLayout()
        self.le_name = QLineEdit()
        self.form_layout.addRow("Profile Name:", self.le_name)
        
        # Stack for Local vs Online fields
        self.stack = QStackedWidget()
        
        # Local Page
        self.page_local = QWidget()
        local_form = QFormLayout(self.page_local)
        self.cb_local_models = QComboBox()
        
        local_model_layout = QHBoxLayout()
        local_model_layout.addWidget(self.cb_local_models)
        self.btn_install = QPushButton("Install")
        self.btn_install.setStyleSheet("background-color: #89B4FA; color: #11111B; font-weight: bold; padding: 5px 15px; border-radius: 4px;")
        self.btn_install.clicked.connect(self.install_local_model)
        local_model_layout.addWidget(self.btn_install)
        local_form.addRow("Installed Model:", local_model_layout)
        
        # Online Page
        self.page_online = QWidget()
        online_form = QFormLayout(self.page_online)
        self.cb_provider = QComboBox()
        self.cb_provider.addItems(["Google Gemini", "OpenAI", "Anthropic"])
        self.le_key = QLineEdit()
        self.le_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.le_model = QLineEdit()
        online_form.addRow("AI Provider:", self.cb_provider)
        online_form.addRow("API Key:", self.le_key)
        online_form.addRow("Model Name:", self.le_model)
        
        self.stack.addWidget(self.page_local)
        self.stack.addWidget(self.page_online)
        
        self.right_layout.addLayout(self.form_layout)
        self.right_layout.addWidget(self.stack)
        
        self.btn_save = QPushButton("Save Profile")
        self.btn_save.clicked.connect(self.save_profile_details)
        self.right_layout.addWidget(self.btn_save)
        self.right_layout.addStretch()
        
        main_layout.addWidget(self.right_panel, 2)
        
        self.fetch_local_models()
        self.refresh_list()
        self.check_and_install_ai()
        
    def check_and_install_ai(self):
        # We need to check if we already have the default model. If not, spawn the worker.
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(["ollama", "list"], startupinfo=startupinfo).decode("utf-8")
            if "network-assistant-ultimate" in output:
                return # Already installed
        except Exception:
            pass # Either Ollama not installed or model missing
            
        self.progress_dlg = QProgressDialog("Checking AI Dependencies...", "Cancel", 0, 100, self)
        self.progress_dlg.setWindowTitle("AI Configuration")
        self.progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dlg.setAutoClose(True)
        self.progress_dlg.show()
        
        self.ai_worker = AIInstallerWorker()
        self.ai_worker.progress.connect(self.update_ai_progress)
        self.ai_worker.finished_install.connect(self.finish_ai_install)
        self.ai_worker.start()

    def update_ai_progress(self, val, msg):
        self.progress_dlg.setValue(val)
        self.progress_dlg.setLabelText(msg)

    def finish_ai_install(self, success, msg):
        if not success:
            QMessageBox.critical(self, "AI Install Error", msg)
        else:
            self.fetch_local_models()
            self.refresh_list()

        
    def fetch_local_models(self):
        import subprocess
        self.cb_local_models.clear()
        try:
            # Hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(["ollama", "list"], startupinfo=startupinfo).decode("utf-8")
            lines = output.strip().split("\n")[1:] # skip header
            models = [line.split()[0] for line in lines if line.strip()]
            self.cb_local_models.addItems(models)
        except Exception:
            pass

    def toggle_type(self):
        if self.rb_local.isChecked():
            self.stack.setCurrentWidget(self.page_local)
        else:
            self.stack.setCurrentWidget(self.page_online)

    def refresh_list(self, select_name="Default"):
        self.profile_list.clear()
        selected_item = None
        for p in self.profiles:
            item = QListWidgetItem(p["name"])
            item.setData(Qt.ItemDataRole.UserRole, p["name"])
            self.profile_list.addItem(item)
            if p["name"] == select_name:
                selected_item = item
        
        if selected_item:
            self.profile_list.setCurrentItem(selected_item)
            self.load_profile_details(selected_item)
        elif self.profile_list.count() > 0:
            self.profile_list.setCurrentRow(0)
            self.load_profile_details(self.profile_list.item(0))
            
    def load_profile_details(self, item):
        name = item.data(Qt.ItemDataRole.UserRole) or item.text()
        
        is_default = (name == "Default")
        self.right_panel.setDisabled(is_default)
        self.btn_del.setDisabled(is_default)
        
        for p in self.profiles:
            if p["name"] == name:
                self.le_name.setText(p["name"])
                if p.get("provider") == "Ollama":
                    self.rb_local.setChecked(True)
                    idx = self.cb_local_models.findText(p.get("model", ""))
                    if idx >= 0: 
                        self.cb_local_models.setCurrentIndex(idx)
                    elif p.get("model"):
                        self.cb_local_models.addItem(p.get("model"))
                        self.cb_local_models.setCurrentText(p.get("model"))
                else:
                    self.rb_online.setChecked(True)
                    idx = self.cb_provider.findText(p.get("provider", ""))
                    if idx >= 0: self.cb_provider.setCurrentIndex(idx)
                    self.le_key.setText(p.get("api_key", ""))
                    self.le_model.setText(p.get("model", ""))
                break

    def add_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name:")
        if ok and name:
            self.profiles.append({"name": name, "provider": "Ollama", "api_key": "", "model": ""})
            self.refresh_list(select_name=name)
            
    def del_profile(self):
        item = self.profile_list.currentItem()
        if item:
            name = item.data(Qt.ItemDataRole.UserRole)
            self.profiles = [p for p in self.profiles if p["name"] != name]
            self.refresh_list()
            self.save_all()

    def save_profile_details(self):
        item = self.profile_list.currentItem()
        if not item: return
        old_name = item.data(Qt.ItemDataRole.UserRole)
        
        for p in self.profiles:
            if p["name"] == old_name:
                p["name"] = self.le_name.text().strip()
                if self.rb_local.isChecked():
                    p["provider"] = "Ollama"
                    p["model"] = self.cb_local_models.currentText()
                    p["api_key"] = ""
                else:
                    p["provider"] = self.cb_provider.currentText()
                    p["api_key"] = self.le_key.text().strip()
                    p["model"] = self.le_model.text().strip()
                break
                
        self.refresh_list(select_name=old_name)
        self.save_all()
        QMessageBox.information(self, "Saved", "Profile saved successfully.")

    def save_all(self):
        self.config["profiles"] = self.profiles
        save_ai_config(self.config, self.user_id)

    def install_local_model(self):
        model_name, ok = QInputDialog.getText(self, "Install Model", "Enter model name (e.g., net-arch, llama3):")
        if ok and model_name:
            model_name = model_name.strip()
            # Check if already installed
            installed = []
            for i in range(self.cb_local_models.count()):
                installed.append(self.cb_local_models.itemText(i))
            if model_name in installed or f"{model_name}:latest" in installed:
                QMessageBox.warning(self, "Already Installed", f"Model '{model_name}' is already installed!")
                return
                
            import subprocess
            import threading
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Downloading...")
            msg.setText(f"Downloading model '{model_name}' via Ollama.\nThis might take a few minutes depending on your internet connection.")
            msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            msg.show()
            
            def run_pull():
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.run(["ollama", "pull", model_name], check=True, startupinfo=startupinfo)
                    if self.parent() and hasattr(self.parent(), 'status'):
                        self.parent().status.showMessage(f"Model '{model_name}' installed successfully.", 5000)
                except Exception:
                    pass
                finally:
                    msg.accept()
                    
            t = threading.Thread(target=run_pull)
            t.start()

class MainWindow(QMainWindow):
    def __init__(self, mode='practice', lab='No Lab (Blank)', starting_topology=None, exam_id=None, db_url=None, user_id=None, requirement_text=None, close_callback=None, user_role='STUDENT'):
        super().__init__()
        self.mode = mode
        self.lab = lab
        self.starting_topology = starting_topology
        self.exam_id = exam_id
        self.db_url = db_url
        self.user_id = user_id
        self.requirement_text = requirement_text
        self.close_callback = close_callback
        self.user_role = user_role
        self.setWindowTitle("TTL-Topology Tormentor Lite")
        self.resize(1280, 800)
        
        self.canvas = NetworkCanvas(self)
        self.setCentralWidget(self.canvas)
        
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.canvas.status_message.connect(self.status.showMessage)
        
        self._create_menus()
        self._create_toolbar()
        
        if self.requirement_text:
            from PyQt6.QtWidgets import QTextBrowser, QPushButton
            self.req_dock = QDockWidget("Cerințe", self)
            self.req_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
            req_browser = QTextBrowser()
            req_browser.setStyleSheet("background-color: #181825; color: #CDD6F4; font-size: 14px; padding: 10px; border: none;")
            req_browser.setText(self.requirement_text)
            self.req_dock.setWidget(req_browser)
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.req_dock)
            
            # Button to reopen requirements
            self.req_btn = QPushButton("Cerințe")
            self.req_btn.setStyleSheet("background-color: #313244; color: #CDD6F4; border-radius: 4px; padding: 4px 10px; font-weight: bold;")
            self.req_btn.clicked.connect(self.req_dock.show)
            self.req_btn.hide()
            self.status.addPermanentWidget(self.req_btn)
            
            self.req_dock.visibilityChanged.connect(lambda visible: self.req_btn.setVisible(not visible))

        if self.mode == 'exam':
            self._setup_ai_dock()
            self._setup_exam_mode()
        else:
            self._setup_ai_dock()
            if self.lab != 'No Lab (Blank)':
                self.status.showMessage(f"Practice Mode: Loaded {self.lab}")
                
        if self.starting_topology:
            try:
                if isinstance(self.starting_topology, str):
                    self.starting_topology = json.loads(self.starting_topology)
                self.canvas.import_topology(self.starting_topology)
                self.status.showMessage("Loaded Topology from Database.")
            except Exception as e:
                print("Failed to load topology:", e)
    def _setup_ai_dock(self):
        self.ai_dock = QDockWidget("AI Topology Assistant", self)
        self.ai_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.ai_assistant = NetworkAssistantWidget(self.canvas)
        self.ai_dock.setWidget(self.ai_assistant)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ai_dock)
        if self.mode != 'exam':
            self.ai_dock.hide() 
        else:
            self.ai_dock.show()

    def _setup_exam_mode(self):
        from PyQt6.QtCore import QTimer
            
        if getattr(self, 'user_role', 'STUDENT') == 'STUDENT':
            self.time_left = 60 * 60 # 60 minutes
            self.exam_timer = QTimer(self)
            self.exam_timer.timeout.connect(self.update_exam_timer)
            self.exam_timer.start(1000) # every second
            self.update_exam_timer() # initial update
        else:
            self.time_left = -1

    def update_exam_timer(self):
        if self.time_left == -1:
            self.status.showMessage("EXAM MODE (Professor - No Timer)")
            return
            
        mins, secs = divmod(self.time_left, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.status.showMessage(f"EXAM MODE - Time Left: {time_str}")
        self.status.setStyleSheet("color: red; font-weight: bold; background-color: #181825;")
        
        if self.time_left <= 0:
            self.exam_timer.stop()
            self.status.showMessage("EXAM TIME EXPIRED! Uploading to Database...")
            self.status.setStyleSheet("color: red; font-weight: bold; background-color: #181825;")
            self.auto_upload_exam()
            self.canvas.setEnabled(False)
            return
            
        self.time_left -= 1

    def auto_upload_exam(self):
        from PyQt6.QtWidgets import QMessageBox
        if hasattr(self, 'exam_timer'): self.exam_timer.stop()
        self.canvas.setEnabled(False)
        
        data = {
            "devices": [d.to_dict() for d in self.canvas.devices],
            "links": [l.to_dict() for l in self.canvas.links]
        }
        
        if self.user_role == 'STUDENT':
            if self.db_url and self.user_id and self.exam_id:
                import psycopg2
                try:
                    with psycopg2.connect(self.db_url) as conn:
                        with conn.cursor() as cur:
                            cur.execute("INSERT INTO submissions (student_id, exam_id, submitted_topology) VALUES (%s, %s, %s);",
                                        (self.user_id, self.exam_id, json.dumps(data)))
                    QMessageBox.information(self, "Success", "Exam topology successfully submitted to the database!")
                except Exception as e:
                    QMessageBox.critical(self, "Database Error", f"Failed to submit: {e}")
            else:
                QMessageBox.information(self, "Mock Submit", "Submitted (Mock): DB URL or Exam ID missing.")
        else:
            QMessageBox.information(self, "Professor Mode", "Test submission complete. As a Professor, your answers are NOT saved.")
            
        if self.close_callback:
            self.close_callback()
        else:
            self.close()

    def _create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        save_act = QAction("Save Topology", self)
        save_act.triggered.connect(self.save_topology)
        file_menu.addAction(save_act)
        
        load_act = QAction("Load Topology", self)
        load_act.triggered.connect(self.load_topology)
        file_menu.addAction(load_act)
        
        config_menu = menubar.addMenu("Configure")
        ai_settings_act = QAction("AI Settings", self)
        ai_settings_act.triggered.connect(self.open_ai_settings)
        config_menu.addAction(ai_settings_act)

    def _create_toolbar(self):
        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        for act in ["Add PC", "Add Laptop", "Add Server", "Add Router", "Add Switch", "Add Wireless Router"]:

            action = QAction(act, self)
            action.triggered.connect(lambda checked, a=act: self.canvas.set_mode('device', a.replace("Add ", "")))
            toolbar.addAction(action)

        toolbar.addSeparator()

        for cable in ["Straight-Through", "Cross-Over", "Console", "Serial"]:
            action = QAction(f"Cable: {cable}", self)
            action.triggered.connect(lambda checked, c=cable: self.canvas.set_mode('cable', c))
            toolbar.addAction(action)

        toolbar.addSeparator()

        ai_toggle_act = QAction("Ask AI", self)
        ai_toggle_act.triggered.connect(self.toggle_ai_dock)
        ai_toggle_act.setCheckable(True)
        self.ai_toggle_action = ai_toggle_act
        toolbar.addAction(ai_toggle_act)
        
        if getattr(self, 'mode', 'practice') != 'practice':
            if getattr(self, 'user_role', 'STUDENT') == 'STUDENT':
                submit_act = QAction("Submit Exam Early", self)
                submit_act.triggered.connect(self.auto_upload_exam)
                toolbar.addAction(submit_act)
            else:
                exit_act = QAction("Exit Exam", self)
                exit_act.triggered.connect(self.force_close)
                toolbar.addAction(exit_act)
                
    def force_close(self):
        if self.close_callback:
            self.close_callback()
        else:
            self.close()

    def toggle_ai_dock(self):
        if self.ai_dock.isVisible():
            self.ai_dock.hide()
        else:
            self.ai_dock.show()
            self.ai_dock.raise_()

    def open_ai_settings(self):
        dlg = AISettingsDialog(self, user_id=getattr(self, 'user_id', 'default'))
        dlg.exec()
        if hasattr(self, 'ai_assistant'):
            self.ai_assistant.refresh_profiles()

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