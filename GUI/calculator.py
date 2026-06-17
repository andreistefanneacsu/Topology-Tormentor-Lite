from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit
from PyQt6.QtCore import Qt

class CalculatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(250, 300)
        self.setStyleSheet("background-color: #ECE9D8; color: black; font-family: Tahoma;")
        
        layout = QVBoxLayout(self)
        
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setStyleSheet("font-size: 20px; background-color: white; border: 2px inset gray; padding: 5px;")
        layout.addWidget(self.display)

        grid = QGridLayout()
        buttons = ['7', '8', '9', '/', '4', '5', '6', '*', '1', '2', '3', '-', 'C', '0', '=', '+']

        row, col = 0, 0
        for text in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(50, 40)
            btn.setStyleSheet("QPushButton { font-size: 14px; font-weight: bold; background-color: #F0F0F0; border: 1px solid gray; } QPushButton:pressed { background-color: #D4D0C8; }")
            btn.clicked.connect(lambda checked, t=text: self.on_button_click(t))
            grid.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0; row += 1

        layout.addLayout(grid)

    def on_button_click(self, text):
        if text == 'C': self.display.clear()
        elif text == '=':
            try: self.display.setText(str(eval(self.display.text())))
            except: self.display.setText("Error")
        else:
            self.display.setText(self.display.text() + text)