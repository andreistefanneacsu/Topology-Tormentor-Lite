import pytest
from Devices.link import Link
from Devices.router2911 import Router2911
from Devices.switch2960 import Switch2960


@pytest.fixture
def devices():
    """Provides a fresh router and switch for each test."""
    r1 = Router2911("R1")
    s1 = Switch2960("S1")
    return r1, s1

@pytest.fixture
def standard_link(devices):
    """Provides a pre-configured link using the devices fixture."""
    r1, s1 = devices
    return Link(
        device1=r1, 
        port1="gigabitEthernet 0/0", 
        device2=s1, 
        port2="gigabitEthernet 0/1", 
        cable_type="Copper Straight-Through"
    )


def test_initialization(devices, standard_link):
    """Test if the link stores the correct device IDs and port strings."""
    r1, s1 = devices
    
    assert standard_link.id is not None
    assert standard_link.cable_type == "Copper Straight-Through"
    assert standard_link.interface1["device_id"] == r1.id
    assert standard_link.interface1["port"] == "gigabitEthernet 0/0"
    assert standard_link.interface2["device_id"] == s1.id
    assert standard_link.interface2["port"] == "gigabitEthernet 0/1"

def test_default_cable_type(devices):
    """Test if the default cable type is applied when omitted."""
    r1, s1 = devices
    link = Link(r1, "gigabitEthernet 0/1", s1, "gigabitEthernet 0/2")
    
    assert link.cable_type == "Copper Straight-Through"

def test_unique_uuid(devices, standard_link):
    """Test if multiple link instances generate unique UUIDs."""
    r1, s1 = devices
    link2 = Link(r1, "gigabitEthernet 0/2", s1, "gigabitEthernet 0/3")
    
    assert standard_link.id != link2.id

def test_to_dict(devices, standard_link):
    """Test if the to_dict method properly formats the data for JSON export."""
    r1, s1 = devices
    data = standard_link.to_dict()
    
    assert "id" in data
    assert data["id"] == standard_link.id
    assert data["cable_type"] == "Copper Straight-Through"
    
    assert data["interface1"]["device_id"] == r1.id
    assert data["interface1"]["port"] == "gigabitEthernet 0/0"
    assert data["interface2"]["device_id"] == s1.id
    assert data["interface2"]["port"] == "gigabitEthernet 0/1"

def test_from_dict(devices):
    """Test if from_dict correctly overwrites instance variables with JSON data."""
    r1, s1 = devices
    
    saved_state = {
        "id": "12345-abcde",
        "cable_type": "Copper Cross-Over",
        "interface1": {"device_id": "old_router_id", "port": "fastEthernet 0/0"},
        "interface2": {"device_id": "old_switch_id", "port": "fastEthernet 0/1"}
    }
    
    dummy_link = Link(r1, "", s1, "")
    dummy_link.from_dict(saved_state)
    
    assert dummy_link.id == "12345-abcde"
    assert dummy_link.cable_type == "Copper Cross-Over"
    assert dummy_link.interface1["device_id"] == "old_router_id"
    assert dummy_link.interface1["port"] == "fastEthernet 0/0"
    assert dummy_link.interface2["device_id"] == "old_switch_id"
    assert dummy_link.interface2["port"] == "fastEthernet 0/1"