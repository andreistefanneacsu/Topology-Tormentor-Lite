import io
from contextlib import redirect_stdout
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit
from simulator import NetworkSimulator

class CmdWidget(QWidget):
    def __init__(self, host_device, all_devices, all_links):
        super().__init__()
        self.host = host_device
        self.simulator = NetworkSimulator(all_devices, all_links)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("background-color: black; color: #CCCCCC; font-family: Consolas; font-size: 14px; border: none;")
        self.output_area.append("Microsoft Windows XP [Version 5.1.2600]\n(C) Copyright 1985-2001 Microsoft Corp.\n")
        self.output_area.append(self.host.get_prompt())

        self.output_area.mousePressEvent = self.force_focus

        self.input_line = QLineEdit()
        self.input_line.setStyleSheet("background-color: black; color: white; font-family: Consolas; font-size: 14px; border: none;")
        self.input_line.returnPressed.connect(self.execute_command)

        layout.addWidget(self.output_area)
        layout.addWidget(self.input_line)

        self.input_line.setFocus()

    def force_focus(self, event):
        self.input_line.setFocus()
        QTextEdit.mousePressEvent(self.output_area, event)

    def execute_command(self):
        cmd = self.input_line.text().strip()
        self.input_line.clear()
        
        self.output_area.insertPlainText(f"{cmd}\n")
        
        if cmd.lower().startswith("ping "):
            target_ip = cmd.split()[1]
            f = io.StringIO()
            with redirect_stdout(f):
                self.simulator.ping(self.host, target_ip)
            output = f.getvalue()
            self.output_area.insertPlainText(output)
        else:
            response = self.host.process_command(cmd)
            self.output_area.insertPlainText(response)
            
        self.output_area.insertPlainText(self.host.get_prompt())
        self.output_area.ensureCursorVisible()