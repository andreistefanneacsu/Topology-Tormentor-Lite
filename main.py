import sys
import os
from PyQt6.QtWidgets import QApplication
from GUI.gui import MainWindow, MODERN_STYLE

def main():
    app = QApplication(sys.argv)
    
    app.setStyleSheet(MODERN_STYLE)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()