from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsPathItem, QMenu, QMessageBox, \
    QGraphicsDropShadowEffect, QInputDialog
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath, QFont, QLinearGradient
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF

from Devices.pc import PC
from Devices.laptop import Laptop
from Devices.router2911 import Router2911
from Devices.switch2960 import Switch2960
from Devices.interface import Interface
from Devices.link import Link

class CableNode(QGraphicsPathItem):
    def __init__(self, node1, node2, cable_type):
        super().__init__()
        self.node1 = node1
        self.node2 = node2
        self.cable_type = cable_type
        self.setZValue(-1) 
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.update_path()

    def update_path(self):
        path = QPainterPath()
        start = self.node1.scenePos()
        end = self.node2.scenePos()
        path.moveTo(start)

        pen = QPen()
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        if self.cable_type == "Straight-Through":
            pen.setColor(QColor("#A6E3A1"))
            path.lineTo(end)
        elif self.cable_type == "Cross-Over":
            pen.setColor(QColor("#F38BA8"))
            pen.setStyle(Qt.PenStyle.DashLine)
            path.lineTo(end)
        elif self.cable_type == "Console":
            pen.setColor(QColor("#89B4FA"))
            control_x = (start.x() + end.x()) / 2
            control_y = min(start.y(), end.y()) - 120 
            path.quadTo(QPointF(control_x, control_y), end)

        self.setPen(pen)
        self.setPath(path)

    def paint(self, painter, option, widget):
        pen = QPen(self.pen())
        if self.isSelected():
            pen.setColor(QColor("#F9E2AF")) 
            pen.setWidth(6)
        painter.setPen(pen)
        painter.drawPath(self.path())

class DeviceNode(QGraphicsItem):
    def __init__(self, backend_device, canvas):
        super().__init__()
        self.device = backend_device
        self.canvas = canvas
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        if self.device.type in ["Router", "Switch"] and "Console" not in self.device.interfaces:
            self.device.interfaces["Console"] = Interface("Console", is_console=True)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(5)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

    def boundingRect(self):
        return QRectF(-40, -40, 80, 80)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isSelected():
            painter.setPen(QPen(QColor("#F9E2AF"), 4)) 
        else:
            painter.setPen(QPen(QColor("#11111B"), 2))

        grad = QLinearGradient(-30, -30, 30, 30)
        if self.device.type == "Router":
            grad.setColorAt(0, QColor("#313244"))
            grad.setColorAt(1, QColor("#181825"))
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(-35, -35, 70, 70)
            painter.setPen(QPen(QColor("#89B4FA"), 3))
            painter.drawLine(-10, -10, 10, 10)
            painter.drawLine(-10, 10, 10, -10)

        elif self.device.type == "Switch":
            grad.setColorAt(0, QColor("#45475A"))
            grad.setColorAt(1, QColor("#313244"))
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(-40, -25, 80, 50, 10, 10)
            painter.setPen(QPen(QColor("#A6E3A1"), 3))
            painter.drawLine(-20, -10, 20, -10)
            painter.drawLine(20, -10, 10, -15)
            painter.drawLine(-20, 10, 20, 10)
            painter.drawLine(-20, 10, -10, 15)

        elif self.device.type == "PC":
            painter.setBrush(QBrush(QColor("#CDD6F4")))
            painter.drawRoundedRect(-25, -30, 50, 35, 5, 5) 
            painter.setBrush(QBrush(QColor("#11111B")))
            painter.drawRect(-20, -25, 40, 25) 
            painter.setBrush(QBrush(QColor("#9399B2")))
            painter.drawRect(-30, 15, 60, 10)  
            painter.setPen(QPen(QColor("#9399B2"), 4))
            painter.drawLine(0, 5, 0, 15)      

        elif self.device.type == "Laptop":
            painter.setBrush(QBrush(QColor("#11111B")))
            painter.drawRoundedRect(-30, -25, 60, 40, 4, 4) 
            painter.setBrush(QBrush(QColor("#CDD6F4")))
            painter.drawPolygon(QPointF(-35, 15), QPointF(35, 15), QPointF(45, 25), QPointF(-45, 25))

        painter.setPen(QPen(QColor("#CDD6F4")))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(-50, 35, 100, 20), Qt.AlignmentFlag.AlignCenter, self.device.name)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            for item in self.canvas.scene.items():
                if isinstance(item, CableNode) and (item.node1 == self or item.node2 == self):
                    item.update_path()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        if self.canvas.current_mode == 'select':
            if self.device.type in ["PC", "Laptop"]:
                from desktop import DesktopEnvironment
                self.os_window = DesktopEnvironment(self.device, self.canvas)
                self.os_window.show()
            else:
                from cli_app import CLIWidget
                from PyQt6.QtWidgets import QDialog, QVBoxLayout
                dlg = QDialog()
                dlg.setWindowTitle(f"CLI - {self.device.name}")
                dlg.resize(650, 450)
                lay = QVBoxLayout(dlg)
                lay.setContentsMargins(0,0,0,0)
                cli = CLIWidget(self.device)
                lay.addWidget(cli)
                dlg.exec()
        super().mouseDoubleClickEvent(event)

class NetworkCanvas(QGraphicsView):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, 2000, 2000)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.setBackgroundBrush(QBrush(QColor("#2B2D3A")))
        
        self.current_mode = 'select'  
        self.selected_item_type = None 
        
        self.devices = []
        self.links = []
        self.cable_start_node = None
        self.cable_start_port = None

    def keyPressEvent(self, event):
        """Allows deletion of devices and cables using Delete or Backspace."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected_items()
        else:
            super().keyPressEvent(event)

    def delete_selected_items(self):
        items = self.scene.selectedItems()
        for item in items:
            if isinstance(item, DeviceNode):
                self.remove_device_node(item)
            elif isinstance(item, CableNode):
                self.remove_cable_node(item)

    def remove_cable_node(self, cable_node):
        if cable_node not in self.scene.items(): return

        if cable_node.cable_type == "Console":
            laptop = cable_node.node1.device if cable_node.node1.device.type == "Laptop" else cable_node.node2.device
            if hasattr(laptop, 'disconnect_serial'):
                laptop.disconnect_serial()

        link_to_remove = None
        for link in self.links:
            match_1 = (link.interface1["device_id"] == cable_node.node1.device.id and link.interface2["device_id"] == cable_node.node2.device.id)
            match_2 = (link.interface1["device_id"] == cable_node.node2.device.id and link.interface2["device_id"] == cable_node.node1.device.id)
            if (match_1 or match_2) and link.cable_type == cable_node.cable_type:
                link_to_remove = link
                break
        
        if link_to_remove:
            self.links.remove(link_to_remove)

        self.scene.removeItem(cable_node)
        self.status_message.emit("Cable deleted.")

    def remove_device_node(self, device_node):
        if device_node not in self.scene.items(): return

        attached_cables = []
        for item in self.scene.items():
            if isinstance(item, CableNode):
                if item.node1 == device_node or item.node2 == device_node:
                    attached_cables.append(item)
        
        for cable in attached_cables:
            self.remove_cable_node(cable)

        if device_node.device in self.devices:
            self.devices.remove(device_node.device)

        self.scene.removeItem(device_node)
        self.status_message.emit(f"Device {device_node.device.name} deleted.")

    def clear_canvas(self):
        self.scene.clear()
        self.devices.clear()
        self.links.clear()
        self.cable_start_node = None

    def get_node_by_device(self, device):
        for item in self.scene.items():
            if isinstance(item, DeviceNode) and item.device == device:
                return item
        return None

    def set_mode(self, mode, item_type=None):
        self.current_mode = mode
        self.selected_item_type = item_type
        self.cable_start_node = None
        self.status_message.emit(f"Mode: {mode.upper()} | {item_type or ''}")

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        
        if self.current_mode == 'device':
            self.add_device(scene_pos)
            
        elif self.current_mode == 'cable':
            item = self.scene.itemAt(scene_pos, self.transform())
            if isinstance(item, DeviceNode):
                global_pos = event.globalPosition().toPoint()
                self.handle_cable_connection(item, global_pos)
        else:
            super().mousePressEvent(event)

    def add_device(self, pos):
        dev_map = {"PC": PC, "Laptop": Laptop, "Router": Router2911, "Switch": Switch2960}
        dev_class = dev_map.get(self.selected_item_type)
        if dev_class:
            num = len([d for d in self.devices if d.type == self.selected_item_type]) + 1
            backend_dev = dev_class(f"{self.selected_item_type}{num}")
            self.devices.append(backend_dev)
            
            node = DeviceNode(backend_dev, self)
            node.setPos(pos)
            self.scene.addItem(node)
            self.set_mode('select')

    def handle_cable_connection(self, node, screen_pos):
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; } QMenu::item:selected { background-color: #89B4FA; color: #11111B; }")
        valid_ports = []
        
        for name, intf in node.device.interfaces.items():
            if self._is_port_available(node.device, name):
                if self.selected_item_type == "Console" and intf.is_console:
                    valid_ports.append(name)
                elif self.selected_item_type in ["Straight-Through", "Cross-Over"] and not intf.is_console:
                    valid_ports.append(name)

        if not valid_ports:
            QMessageBox.warning(self, "Port Error", "No compatible free ports for this cable.")
            return

        for port in valid_ports:
            menu.addAction(port)

        action = menu.exec(screen_pos)
        if not action: return
        selected_port = action.text()

        if not self.cable_start_node:
            self.cable_start_node = node
            self.cable_start_port = selected_port
            self.status_message.emit(f"Connected to {node.device.name} on {selected_port}. Select second device.")
        else:
            if self.cable_start_node == node:
                self.cable_start_node = None
                return

            new_link = Link(self.cable_start_node.device, self.cable_start_port, node.device, selected_port, self.selected_item_type)
            self.links.append(new_link)
            
            if self.selected_item_type == "Console":
                laptop = self.cable_start_node.device if self.cable_start_node.device.type == "Laptop" else node.device
                target = node.device if self.cable_start_node.device.type == "Laptop" else self.cable_start_node.device
                if hasattr(laptop, 'connect_serial'):
                    laptop.connect_serial(target)

            cable_line = CableNode(self.cable_start_node, node, self.selected_item_type)
            self.scene.addItem(cable_line)
            
            self.status_message.emit("Connection successful.")
            self.set_mode('select')

    def _is_port_available(self, device, port_name):
        for link in self.links:
            if (link.interface1["device_id"] == device.id and link.interface1["port"] == port_name) or \
               (link.interface2["device_id"] == device.id and link.interface2["port"] == port_name):
                return False
        return True

    def contextMenuEvent(self, event):
        node = self.itemAt(event.pos())
        menu = QMenu()

        if isinstance(node, DeviceNode):
            copy_action = menu.addAction("Copy")
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")

            action = menu.exec(event.globalPos())

            if action == copy_action:
                self.copied_node = node

            elif action == rename_action:
                text, ok = QInputDialog.getText(self, "Rename", "New name:")
                if ok:
                    node.device.name = text
                    node.update()

            elif action == delete_action:
                self.remove_device_node(node)

        else:
            paste_action = menu.addAction("Paste")
            action = menu.exec(event.globalPos())

            if action == paste_action and self.copied_node:
                old_device = self.copied_node.device
                old_device_type = type(old_device)

                new_device = old_device_type(old_device.name + "_copy")
                self.devices.append(new_device)

                new_node = DeviceNode(new_device, self)
                new_node.setPos(self.mapToScene(event.pos()))

                self.scene.addItem(new_node)
                self.set_mode('select')