import sys
import os
from PyQt6.QtWidgets import QApplication
from GUI.menu_gui import MainMenu, MODERN_STYLE, DB_URL
from GUI.workspace import WorkspaceWindow
from GUI.session_manager import load_session

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLE)
    
    session_data = load_session()
    if session_data:
        window = WorkspaceWindow(DB_URL, session_data)
    else:
        window = MainMenu()
        
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()