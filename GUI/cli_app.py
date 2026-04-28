from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit

class CLIWidget(QWidget):
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.target = device.console_target if hasattr(device, 'console_target') and device.console_target else device
        
        self.resize(650, 450)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        if not self.target or self.target == self.device:
            err = QTextEdit()
            err.setStyleSheet("background-color: black; color: red; font-family: Consolas; font-size: 14px; padding: 10px;")
            err.setText("FATAL ERROR: No active console connection detected.\n\nPlease attach a Console cable from the Laptop's RS232 port to a Router or Switch Console port.")
            layout.addWidget(err)
            return

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("background-color: #000000; color: #00FF00; font-family: Consolas; font-size: 14px; border: none;")
        self.output_area.append(f"PuTTY (Inactive) - Connected to {self.target.name} via COM1\n\n")
        self.output_area.append(self.target.get_prompt())

        self.output_area.mousePressEvent = self.force_focus

        self.input_line = QLineEdit()
        self.input_line.setStyleSheet("background-color: #000000; color: #00FF00; font-family: Consolas; font-size: 14px; border: none;")
        self.input_line.returnPressed.connect(self.execute_command)

        layout.addWidget(self.output_area)
        layout.addWidget(self.input_line)

        self.input_line.setFocus()

    def force_focus(self, event):
        self.input_line.setFocus()
        QTextEdit.mousePressEvent(self.output_area, event)

    def execute_command(self):
        cmd = self.input_line.text()
        self.input_line.clear()
        
        self.output_area.insertPlainText(f"{cmd}\n")
        
        response = self.target.process_command(cmd)
        if response:
            self.output_area.insertPlainText(response)
            
        self.output_area.insertPlainText(self.target.get_prompt())
        self.output_area.ensureCursorVisible()