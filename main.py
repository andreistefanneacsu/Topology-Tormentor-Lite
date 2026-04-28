import sys
import os
from PyQt6.QtWidgets import QApplication

root_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.join(root_dir, "GUI") not in sys.path:
    sys.path.insert(0, os.path.join(root_dir, "GUI"))
if os.path.join(root_dir, "Devices") not in sys.path:
    sys.path.insert(0, os.path.join(root_dir, "Devices"))

from GUI.gui import MainWindow, MODERN_STYLE

def main():
    app = QApplication(sys.argv)
    
    app.setStyleSheet(MODERN_STYLE)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()