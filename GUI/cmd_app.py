import io
from contextlib import redirect_stdout
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit
from simulator import NetworkSimulator

from PyQt6.QtCore import Qt

class TerminalEdit(QTextEdit):
    def __init__(self, executor):
        super().__init__()
        self.executor = executor
        self.prompt_pos = 0

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        pos = cursor.position()
        
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)
            cmd = self.toPlainText()[self.prompt_pos:].strip()
            self.insertPlainText("\n")
            self.executor(cmd)
            return
        elif event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Left):
            if pos <= self.prompt_pos:
                return
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            return
            
        if pos < self.prompt_pos:
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)
            
        super().keyPressEvent(event)

    def append_output(self, text):
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.insertPlainText(text)
        self.ensureCursorVisible()

    def set_prompt(self, prompt):
        self.append_output(prompt)
        self.prompt_pos = len(self.toPlainText())

class CmdWidget(QWidget):
    def __init__(self, host_device, all_devices, all_links):
        super().__init__()
        self.host = host_device
        self.simulator = NetworkSimulator(all_devices, all_links)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.terminal = TerminalEdit(self.execute_command)
        self.terminal.setStyleSheet("background-color: black; color: #CCCCCC; font-family: Consolas; font-size: 14px; border: none;")
        self.terminal.append_output("Microsoft Windows XP [Version 5.1.2600]\n(C) Copyright 1985-2001 Microsoft Corp.\n\n")
        self.terminal.set_prompt(self.host.get_prompt())

        layout.addWidget(self.terminal)
        self.terminal.setFocus()

    def execute_command(self, cmd):
        if not cmd:
            self.terminal.set_prompt(self.host.get_prompt())
            return
            
        if cmd.lower().startswith("ping "):
            target_ip = cmd.split()[1]
            f = io.StringIO()
            with redirect_stdout(f):
                self.simulator.ping(self.host, target_ip)
            self.terminal.append_output(f.getvalue())
        elif cmd.lower() == "ipconfig /renew":
            self.terminal.append_output("Requesting IP via DHCP...\n")
            res = self.simulator.request_dhcp(self.host)
            if res:
                intf_name = res.get("interface")
                intf = self.host.interfaces.get(intf_name)
                
                if intf:
                    intf.ip = res["ip"]
                    intf.subnet = res["subnet"]
                self.host.config["default-gateway"] = res["gateway"]
                self.host.config["dns-server"] = res["dns"]
                
                self.terminal.append_output("\nConnection-specific DNS Suffix  . : \n")
                self.terminal.append_output(f"IP Address. . . . . . . . . . . . : {res['ip']}\n")
                self.terminal.append_output(f"Subnet Mask . . . . . . . . . . . : {res['subnet']}\n")
                self.terminal.append_output(f"Default Gateway . . . . . . . . . : {res['gateway']}\n")
            else:
                self.terminal.append_output("DHCP Request failed. No DHCP server found.\n")
        else:
            response = self.host.process_command(cmd)
            self.terminal.append_output(response)
            
        self.terminal.set_prompt(self.host.get_prompt())