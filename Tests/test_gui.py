import pytest
from PyQt6.QtCore import Qt
import tempfile
import json

from GUI.gui import MainWindow

@pytest.fixture
def app(qtbot):
    window = MainWindow()
    window.show()
    qtbot.addWidget(window)
    return window

def test_add_device(app, qtbot):
    canvas = app.canvas
    canvas.set_mode('device', 'PC')
    qtbot.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.rect().center())
    assert len(canvas.devices) == 1
    assert canvas.devices[0].type == "PC"

def test_remove_device_key(app, qtbot):
    canvas = app.canvas
    canvas.set_mode('device', 'PC')
    qtbot.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.rect().center())
    node = next(item for item in canvas.scene.items() if hasattr(item, "device"))
    node.setSelected(True)
    qtbot.keyClick(canvas, Qt.Key.Key_Delete)
    assert len(canvas.devices) == 0


def test_connect_two_devices(app, qtbot, monkeypatch):
    canvas = app.canvas
    canvas.set_mode('device', 'PC')
    qtbot.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.rect().center())
    canvas.set_mode('device', 'PC')
    qtbot.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.rect().center() + canvas.rect().bottomRight()/4)
    monkeypatch.setattr(canvas, "handle_cable_connection", lambda node, pos: None)
    d1, d2 = canvas.devices
    from Devices.link import Link
    link = Link(d1, "fa 0/0", d2, "fa 0/0", "Straight-Through")
    canvas.links.append(link)
    assert len(canvas.links) == 1

def test_delete_cable(app, qtbot):
    canvas = app.canvas
    canvas.set_mode('device', 'PC')
    qtbot.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.rect().center())
    canvas.set_mode('device', 'PC')
    qtbot.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.rect().center() + canvas.rect().bottomRight()/4)
    d1, d2 = canvas.devices
    from Devices.link import Link
    link = Link(d1, "fa 0/0", d2, "fa 0/0", "Straight-Through")
    canvas.links.append(link)
    node1 = canvas.get_node_by_device(d1)
    node2 = canvas.get_node_by_device(d2)
    from GUI.canvas import CableNode
    cable = CableNode(node1, node2, "Straight-Through")
    canvas.scene.addItem(cable)
    cable.setSelected(True)
    qtbot.keyClick(canvas, Qt.Key.Key_Delete)
    assert len(canvas.links) == 0



def test_save_load(app):
    canvas = app.canvas
    canvas.set_mode('device', 'PC')
    canvas.add_device(canvas.scene.sceneRect().center())
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    data = {
        "devices": [d.to_dict() for d in canvas.devices],
        "links": []
    }
    with open(tmp.name, "w") as f:
        json.dump(data, f)
    canvas.clear_canvas()
    assert len(canvas.devices) == 0
    with open(tmp.name) as f:
        loaded = json.load(f)
    assert len(loaded["devices"]) == 1