import psycopg2
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QGridLayout, QScrollArea, QTabWidget, QTextBrowser, QHBoxLayout, QMessageBox, QMainWindow, QFrame, QSplitter)
from PyQt6.QtCore import Qt
from GUI.gui import MainWindow, MODERN_STYLE

class CourseSidebar(QWidget):
    def __init__(self, workspace, db_url, user_data):
        super().__init__()
        self.workspace = workspace
        self.db_url = db_url
        self.user_data = user_data
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        lbl = QLabel("My Courses & Labs")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #89B4FA; margin-bottom: 10px; background-color: transparent; border: none;")
        layout.addWidget(lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        container = QWidget()
        self.vbox = QVBoxLayout(container)
        self.vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        self.load_sidebar_data()

    def load_sidebar_data(self):
        # Add Free Practice button at the very top
        btn_free = QPushButton("New Free Practice Workspace")
        btn_free.setStyleSheet("""
            QPushButton { background-color: #89B4FA; color: #11111B; font-weight: bold; padding: 12px; border-radius: 6px; text-align: center; }
            QPushButton:hover { background-color: #B4BEFE; }
        """)
        btn_free.clicked.connect(lambda: self.workspace.open_simulator_tab("Free Practice", "practice", None))
        self.vbox.addWidget(btn_free)
        
        sep0 = QFrame()
        sep0.setFrameShape(QFrame.Shape.HLine)
        sep0.setStyleSheet("color: #313244; margin: 5px 0px;")
        self.vbox.addWidget(sep0)

        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Fetch enrolled courses
                    if self.user_data['type'] == 'STUDENT':
                        cur.execute("SELECT m.id, m.title FROM modules m JOIN module_enrollments me ON m.id = me.module_id WHERE me.student_id = %s;", (self.user_data['id'],))
                    else:
                        cur.execute("SELECT id, title FROM modules;")
                    courses = cur.fetchall()
                    
                    for cid, ctitle in courses:
                        # Course Header Button
                        btn_course = QPushButton(f"{ctitle}")
                        btn_course.setStyleSheet("""
                            QPushButton { background-color: #313244; color: #CDD6F4; font-weight: bold; font-size: 14px; padding: 12px; border-radius: 6px; text-align: left; }
                            QPushButton:hover { background-color: #45475A; border-left: 4px solid #89B4FA; }
                        """)
                        btn_course.clicked.connect(lambda checked, course_id=cid, course_name=ctitle: self.workspace.open_course_info(course_id, course_name))
                        self.vbox.addWidget(btn_course)
                        
                        # Fetch Labs
                        cur.execute("SELECT id, title, starting_topology, instructions FROM laboratories WHERE module_id = %s;", (cid,))
                        labs = cur.fetchall()
                        for lid, ltitle, topology, instructions in labs:
                            btn_lab = QPushButton(f"Lab: {ltitle}")
                            btn_lab.setStyleSheet("""
                                QPushButton { background-color: transparent; color: #A6E3A1; padding: 8px 12px 8px 25px; text-align: left; border: none; font-size: 13px; }
                                QPushButton:hover { color: #89B4FA; background-color: rgba(166, 227, 161, 0.1); border-radius: 4px; }
                            """)
                            btn_lab.clicked.connect(lambda checked, t=topology, n=ltitle, req=instructions: self.workspace.open_simulator_tab(n, 'practice', t, req))
                            self.vbox.addWidget(btn_lab)
                            
                        # Fetch Exams
                        cur.execute("SELECT id, title, starting_topology, requirement_text, exam_type FROM exams WHERE module_id = %s;", (cid,))
                        exams = cur.fetchall()
                        for eid, etitle, topology, req, etype in exams:
                            btn_exam = QPushButton(f"Exam: {etitle} ({etype})")
                            btn_exam.setStyleSheet("""
                                QPushButton { background-color: transparent; color: #F38BA8; font-weight: bold; padding: 8px 12px 8px 25px; text-align: left; border: none; font-size: 13px; }
                                QPushButton:hover { color: #F5E0DC; background-color: rgba(243, 139, 168, 0.1); border-radius: 4px; }
                            """)
                            
                            if etype == 'THEORY':
                                btn_exam.clicked.connect(lambda checked, mod_id=cid: self.workspace.open_browser_for_exam(mod_id))
                            else:
                                btn_exam.clicked.connect(lambda checked, t=topology, n=etitle, exam_id=eid, requirement=req: self.workspace.open_exam_simulator(n, t, exam_id, requirement))
                            self.vbox.addWidget(btn_exam)
                            
                        # Add a separator
                        sep = QFrame()
                        sep.setFrameShape(QFrame.Shape.HLine)
                        sep.setStyleSheet("color: #313244; margin: 10px 0px;")
                        self.vbox.addWidget(sep)
        except Exception as e:
            print("Error loading sidebar data:", e)

class CourseInfoTab(QWidget):
    def __init__(self, db_url, course_id, course_name):
        super().__init__()
        self.db_url = db_url
        self.course_id = course_id
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl = QLabel(f"Course Info: {course_name}")
        lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #89B4FA; margin-bottom: 20px;")
        layout.addWidget(lbl)
        
        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet("background-color: #1E1E2E; color: #CDD6F4; font-size: 15px; border: 1px solid #313244; border-radius: 8px; padding: 15px;")
        layout.addWidget(self.text_browser)
        
        self.load_theory()
        
    def load_theory(self):
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT title, content FROM courses WHERE module_id = %s ORDER BY display_order;", (self.course_id,))
                    theory_html = ""
                    for r in cur.fetchall():
                        theory_html += f"<h2 style='color: #F5E0DC;'>{r[0]}</h2><p style='line-height: 1.6;'>{r[1]}</p><hr style='border:1px solid #45475A;'/>"
                    
                    if not theory_html:
                        theory_html = "<p>No theory content available for this course yet.</p>"
                    self.text_browser.setHtml(theory_html)
        except Exception as e:
            print("Error loading theory:", e)

class WorkspaceWindow(QMainWindow):
    def __init__(self, db_url, user_data):
        super().__init__()
        self.db_url = db_url
        self.user_data = user_data
        self.setWindowTitle("TTL Workspace")
        self.resize(1400, 850)
        self.setStyleSheet(MODERN_STYLE)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left Panel (Tabs and Toggle)
        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        left_layout.addWidget(self.tabs)
        
        # Vertical centered toggle button
        arrow_container = QWidget()
        arrow_container.setFixedWidth(20)
        arr_layout = QVBoxLayout(arrow_container)
        arr_layout.setContentsMargins(0, 0, 0, 0)
        arr_layout.addStretch()
        
        self.btn_toggle = QPushButton("▶")
        self.btn_toggle.setFixedSize(20, 60)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #CDD6F4;
                font-weight: bold;
                border: none;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
            }
            QPushButton:hover {
                background-color: #89B4FA;
                color: #11111B;
            }
        """)
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        arr_layout.addWidget(self.btn_toggle)
        arr_layout.addStretch()
        
        left_layout.addWidget(arrow_container)
        
        splitter.addWidget(left_panel)
        
        # Right Panel (Sidebar)
        self.sidebar = CourseSidebar(self, self.db_url, self.user_data)
        self.sidebar.setMinimumWidth(300)
        self.sidebar.setMaximumWidth(400)
        self.sidebar.setStyleSheet("background-color: #11111B; border-left: 1px solid #313244;")
        splitter.addWidget(self.sidebar)
        
        splitter.setSizes([1000, 300])

        # Home Tab
        home_tab = QWidget()
        h_layout = QVBoxLayout(home_tab)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        import os
        from PyQt6.QtGui import QPixmap
        logo_path = os.path.join(os.path.dirname(__file__), "icons", "logo.svg")
        logo_label = QLabel()
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(400, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        h_layout.addStretch()
        h_layout.addWidget(logo_label)
        h_layout.addStretch()
        
        self.tabs.addTab(home_tab, "Home")
        from PyQt6.QtWidgets import QTabBar
        self.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        
        # Account Corner Widget
        from PyQt6.QtWidgets import QToolButton, QMenu
        from PyQt6.QtGui import QAction, QDesktopServices
        from PyQt6.QtCore import QUrl
        
        account_btn = QToolButton(self)
        name = self.user_data.get('first_name', 'Account')
        account_btn.setText(f"👤 {name}")
        account_btn.setStyleSheet("""
            QToolButton {
                background-color: #313244; color: #CDD6F4; font-size: 14px; font-weight: bold; border-radius: 4px; padding: 5px 10px; margin-right: 10px; margin-top: 2px;
            }
            QToolButton:hover { background-color: #89B4FA; color: #11111B; }
            QToolButton::menu-indicator { image: none; }
        """)
        account_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        account_menu = QMenu(account_btn)
        account_menu.setStyleSheet("QMenu { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; } QMenu::item:selected { background-color: #89B4FA; color: #11111B; }")
        
        web_base = "https://ttl.calculatoaresitehnologiainformatiei.ro"
        role_path = "student" if self.user_data.get('type') == "STUDENT" else "professor"
        
        act_profile = QAction("Profile", self)
        act_profile.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(f"{web_base}/profile/")))
        account_menu.addAction(act_profile)
        
        act_dash = QAction("Dashboard", self)
        act_dash.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(f"{web_base}/lms/{role_path}/")))
        account_menu.addAction(act_dash)
        
        act_settings = QAction("Settings", self)
        act_settings.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(f"{web_base}/lms/{role_path}/settings/general/")))
        account_menu.addAction(act_settings)
        
        account_menu.addSeparator()
        
        act_logout = QAction("Logout", self)
        act_logout.triggered.connect(self.logout)
        account_menu.addAction(act_logout)
        
        account_btn.setMenu(account_menu)
        self.tabs.setCornerWidget(account_btn, Qt.Corner.TopRightCorner)
        
    def logout(self):
        from GUI.session_manager import clear_session
        from GUI.menu_gui import MainMenu
        msg = QMessageBox(self)
        msg.setWindowTitle("Logout")
        msg.setText("Are you sure you want to log out?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet("QMessageBox { background-color: #181825; } QLabel { color: #CDD6F4; font-size: 14px; } QPushButton { background-color: #313244; color: #CDD6F4; padding: 6px 12px; border-radius: 4px; } QPushButton:hover { background-color: #89B4FA; color: #11111B; }")
        reply = msg.exec()
        if reply == QMessageBox.StandardButton.Yes:
            clear_session()
            self.main_menu = MainMenu()
            self.main_menu.show()
            self.close()

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
            self.btn_toggle.setText("◀")
        else:
            self.sidebar.show()
            self.btn_toggle.setText("▶")

    def close_tab_with_widget(self, widget):
        idx = self.tabs.indexOf(widget)
        if idx != -1:
            self.close_tab(idx)

    def close_tab(self, index):
        if index != 0:
            widget = self.tabs.widget(index)
            self.tabs.removeTab(index)
            widget.deleteLater()

    def open_course_info(self, course_id, course_name):
        info_tab = CourseInfoTab(self.db_url, course_id, course_name)
        idx = self.tabs.addTab(info_tab, f"📖 {course_name}")
        self.tabs.setCurrentIndex(idx)

    def open_simulator_tab(self, name, mode, topology, requirement_text=None):
        sim = MainWindow(mode=mode, lab=name, starting_topology=topology, requirement_text=requirement_text)
        idx = self.tabs.addTab(sim, f"Sim: {name}")
        self.tabs.setCurrentIndex(idx)

    def open_exam_simulator(self, name, topology, exam_id, requirement_text):
        if self.tabs.count() > 1:
            QMessageBox.warning(self, "Tabs Open", "Please close all other tabs (Practice/Course Info) before starting an exam.")
            return
            
        reply = QMessageBox.warning(self, "EXAM MODE WARNING", 
                                    "You are about to start EXAM MODE.\n\n"
                                    "- The AI Assistant is in Tormentor Mode.\n"
                                    "- You will have 60 minutes to complete the topology.\n"
                                    "- A timer will be displayed in the toolbar.\n"
                                    "- Course materials will be hidden.\n"
                                    "- When time expires, your work is AUTO-SUBMITTED to the database.\n\n"
                                    "Are you ready?", 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            sim = MainWindow(
                mode='exam', 
                lab=name, 
                starting_topology=topology, 
                exam_id=exam_id, 
                db_url=self.db_url, 
                user_id=self.user_data['id'],
                requirement_text=requirement_text,
                user_role=self.user_data['type']
            )
            idx = self.tabs.addTab(sim, f"EXAM: {name}")
            
            # Hide sidebar and tab bar to prevent switching
            self.sidebar.hide()
            self.tabs.tabBar().hide()
            
            sim.close_callback = lambda: self.close_exam_tab(sim)
            self.tabs.setCurrentIndex(idx)

    def close_exam_tab(self, widget):
        self.close_tab_with_widget(widget)
        # Restore UI
        self.sidebar.show()
        self.tabs.tabBar().show()

    def open_browser_for_exam(self, module_id):
        import webbrowser
        url = f"https://ttl.calculatoaresitehnologiainformatiei.ro/lms/module/{module_id}/"
        webbrowser.open(url)
        QMessageBox.information(self, "Theory Exam", f"Opened the module page in your default web browser.\nIf it didn't open automatically, please visit: {url}")

    def closeEvent(self, event):
        QApplication.quit()