from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit

from PyQt6.QtCore import Qt
from GUI.cmd_app import TerminalEdit

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

        self.terminal = TerminalEdit(self.execute_command)
        self.terminal.setStyleSheet("background-color: #000000; color: #00FF00; font-family: Consolas; font-size: 14px; border: none;")
        self.terminal.append_output(f"PuTTY (Inactive) - Connected to {self.target.name} via COM1\n\n")
        self.terminal.set_prompt(self.target.get_prompt())

        layout.addWidget(self.terminal)
        self.terminal.setFocus()

    def execute_command(self, cmd):
        if not cmd:
            self.terminal.set_prompt(self.target.get_prompt())
            return
            
        response = self.target.process_command(cmd)
        if response:
            self.terminal.append_output(response)
            
        self.terminal.set_prompt(self.target.get_prompt())