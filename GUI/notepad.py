from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QMenuBar
from PyQt6.QtGui import QAction

class NotepadWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(500, 400)
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        menubar = QMenuBar()
        file_menu = menubar.addMenu("File")
        clear_act = QAction("New", self)
        clear_act.triggered.connect(lambda: self.text_area.clear())
        file_menu.addAction(clear_act)
        
        layout.addWidget(menubar)

        self.text_area = QTextEdit()
        self.text_area.setStyleSheet("font-family: 'Lucida Console', Consolas; font-size: 14px; background-color: white; border: 2px inset gray;")
        layout.addWidget(self.text_area)