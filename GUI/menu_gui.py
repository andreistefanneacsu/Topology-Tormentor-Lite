import sys
import os
import psycopg2
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QMessageBox, QLineEdit)
from PyQt6.QtCore import Qt
from GUI.gui import MODERN_STYLE
from GUI.workspace import WorkspaceWindow

def get_db_url():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    try:
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    return line.strip().split('=', 1)[1]
    except Exception:
        pass
    return ""

DB_URL = get_db_url()

class MainMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TTL - Secure Login")
        self.resize(500, 450)
        self.setStyleSheet(MODERN_STYLE + """
            MainMenu { background-color: #11111B; }
            QLineEdit { border: 2px solid #313244; }
            QLineEdit:focus { border: 2px solid #89B4FA; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Premium Card
        card = QWidget()
        card.setFixedSize(380, 350)
        card.setStyleSheet("background-color: #181825; border-radius: 15px; border: 1px solid #313244;")
        
        # Add slight shadow
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Welcome to TTL")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #CDD6F4; border: none; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email address")
        self.email_input.setStyleSheet("padding: 12px; font-size: 15px; background-color: #313244; color: #CDD6F4; border-radius: 6px;")
        layout.addWidget(self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("padding: 12px; font-size: 15px; background-color: #313244; color: #CDD6F4; border-radius: 6px;")
        layout.addWidget(self.password_input)

        self.btn_login = QPushButton("Sign In")
        self.btn_login.clicked.connect(self.attempt_login)
        self.btn_login.setStyleSheet("""
            QPushButton { background-color: #89B4FA; color: #11111B; font-weight: bold; font-size: 16px; padding: 12px; border-radius: 6px; }
            QPushButton:hover { background-color: #B4BEFE; }
        """)
        layout.addWidget(self.btn_login)

        main_layout.addWidget(card)
        self.workspace = None

    def attempt_login(self):
        email = self.email_input.text().strip()
        pwd = self.password_input.text().strip()
        if not email or not pwd:
            QMessageBox.warning(self, "Error", "Email and Password required.")
            return

        try:
            conn = psycopg2.connect(DB_URL)
            with conn.cursor() as cur:
                cur.execute("SELECT id, first_name, account_type FROM users WHERE email = %s AND password_hash = crypt(%s, password_hash);", (email, pwd))
                row = cur.fetchone()
                if row:
                    user_data = {'id': row[0], 'first_name': row[1], 'type': row[2]}
                    from GUI.session_manager import save_session
                    save_session(user_data)
                    self.workspace = WorkspaceWindow(DB_URL, user_data)
                    self.workspace.show()
                    self.close()
                else:
                    QMessageBox.warning(self, "Login Failed", "Invalid credentials.")
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))
