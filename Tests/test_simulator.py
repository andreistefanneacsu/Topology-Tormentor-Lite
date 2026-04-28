import pytest
from simulator import NetworkSimulator
from Devices.router2911 import Router2911
from Devices.switch2960 import Switch2960
from Devices.pc import PC
from Devices.link import Link

@pytest.fixture
def test_network():
    """Creates a standard topology: Router <-> Switch <-> (PC1, PC2)"""
    r1 = Router2911("HQ-Router")
    r1.process_command("en")
    r1.process_command("conf t")
    r1.process_command("interface gigabitEthernet 0/0")
    r1.process_command("ip address 192.168.1.1 255.255.255.0")
    
    sw1 = Switch2960("Core-Switch")
    sw1.process_command("en")
    sw1.process_command("conf t")
    sw1.process_command("interface vlan 1")
    sw1.process_command("ip address 192.168.1.2 255.255.255.0")

    pc1 = PC("PC-A")
    pc1.process_command("ipconfig 192.168.1.10 255.255.255.0 192.168.1.1")

    pc2 = PC("PC-B")
    pc2.process_command("ipconfig 192.168.1.11 255.255.255.0 10.0.0.1")

    links = [
        Link(r1, "gigabitEthernet 0/0", sw1, "gigabitEthernet 0/1"),
        Link(pc1, "FastEthernet0", sw1, "fastEthernet 0/1"),
        Link(pc2, "FastEthernet0", sw1, "fastEthernet 0/2")
    ]

    devices = [r1, sw1, pc1, pc2]
    sim = NetworkSimulator(devices, links)
    
    return {"sim": sim, "r1": r1, "sw1": sw1, "pc1": pc1, "pc2": pc2, "links": links}


@pytest.fixture
def routed_network():
    """
    Topology: 
    PC1 (192.168.1.0/24) -> R1 -> (10.0.0.0/30) <- R2 <- PC2 (192.168.2.0/24)
    """
    
    pc1 = PC("PC-1")
    pc1.process_command("ipconfig 192.168.1.10 255.255.255.0 192.168.1.1")

    r1 = Router2911("R1")
    r1.process_command("en")
    r1.process_command("conf t")

    r1.process_command("interface gigabitEthernet 0/0")
    r1.process_command("ip address 192.168.1.1 255.255.255.0")

    r1.process_command("interface gigabitEthernet 0/1")
    r1.process_command("ip address 10.0.0.1 255.255.255.252")
    r1.process_command("exit")

    r1.process_command("ip route 192.168.2.0 255.255.255.0 10.0.0.2")


    r2 = Router2911("R2")
    r2.process_command("en")
    r2.process_command("conf t")

    r2.process_command("interface gigabitEthernet 0/0")
    r2.process_command("ip address 10.0.0.2 255.255.255.252")

    r2.process_command("interface gigabitEthernet 0/1")
    r2.process_command("ip address 192.168.2.1 255.255.255.0")
    r2.process_command("exit") 

    r2.process_command("ip route 192.168.1.0 255.255.255.0 10.0.0.1")

    pc2 = PC("PC-2")
    pc2.process_command("ipconfig 192.168.2.10 255.255.255.0 192.168.2.1")

    links = [
        Link(pc1, "FastEthernet0", r1, "gigabitEthernet 0/0"),
        Link(r1, "gigabitEthernet 0/1", r2, "gigabitEthernet 0/0"),
        Link(r2, "gigabitEthernet 0/1", pc2, "FastEthernet0")
    ]

    devices = [pc1, r1, r2, pc2]
    sim = NetworkSimulator(devices, links)
    
    return {"sim": sim, "r1": r1, "r2": r2, "pc1": pc1, "pc2": pc2}



def test_is_in_subnet(test_network):
    sim = test_network["sim"]

    assert sim._is_in_subnet("192.168.1.50", "192.168.1.1", "255.255.255.0") is True

    assert sim._is_in_subnet("10.0.0.5", "192.168.1.1", "255.255.255.0") is False

def test_get_out_interface(test_network):
    sim = test_network["sim"]
    r1 = test_network["r1"]
    
    out_intf = sim._get_out_interface(r1, "192.168.1.10")
    assert out_intf == "gigabitEthernet 0/0"

    assert sim._get_out_interface(r1, "8.8.8.8") is None

def test_l2_forwarding_through_switch(test_network):
    sim = test_network["sim"]
    r1 = test_network["r1"]
    pc1 = test_network["pc1"]
    
    found_dev, target_ip = sim._l2_forward(r1, "gigabitEthernet 0/0", "192.168.1.10")
    
    assert found_dev is not None
    assert found_dev.id == pc1.id
    assert target_ip == "192.168.1.10"

def test_l2_forwarding_fails_on_dead_ip(test_network):
    sim = test_network["sim"]
    pc1 = test_network["pc1"]
    
    found_dev, target_ip = sim._l2_forward(pc1, "FastEthernet0", "192.168.1.99")
    assert found_dev is None


def test_route_packet_local_success(test_network):
    sim = test_network["sim"]
    pc1 = test_network["pc1"]
    r1 = test_network["r1"]
    
    success, msg, target_dev, source_ip = sim._route_packet(pc1, "192.168.1.1")
    
    assert success is True
    assert target_dev.id == r1.id
    assert source_ip == "192.168.1.10"

def test_route_packet_fails_no_gateway(test_network):
    sim = test_network["sim"]
    pc2 = test_network["pc2"] 
    
    success, msg, target_dev, source_ip = sim._route_packet(pc2, "8.8.8.8")
    
    assert success is False
    assert "unreachable" in msg.lower()


def test_ping_success(test_network, capsys):
    sim = test_network["sim"]
    pc1 = test_network["pc1"]
    
    sim.ping(pc1, "192.168.1.1")
    captured = capsys.readouterr()
    
    assert "Pinging 192.168.1.1" in captured.out
    assert "Reply from 192.168.1.1: bytes=32 time=1ms" in captured.out
    assert "Received = 4, Lost = 0" in captured.out

def test_ping_timeout(test_network, capsys):
    sim = test_network["sim"]
    pc1 = test_network["pc1"]
    
    sim.ping(pc1, "192.168.1.99")
    captured = capsys.readouterr()
    
    assert "Request timed out" in captured.out
    assert "Received = 0, Lost = 4" in captured.out

def test_ping_self(test_network, capsys):
    sim = test_network["sim"]
    pc1 = test_network["pc1"]
    
    sim.ping(pc1, "192.168.1.10")
    captured = capsys.readouterr()
    
    assert "Reply from 192.168.1.10: bytes=32 time<1ms" in captured.out


def test_ping_across_routers_success(routed_network, capsys):
    """Tests if a packet can successfully traverse R1 -> R2 and come back."""
    sim = routed_network["sim"]
    pc1 = routed_network["pc1"]
    
    sim.ping(pc1, "192.168.2.10")
    captured = capsys.readouterr()
    
    assert "Reply from 192.168.2.10: bytes=32 time=1ms TTL=128" in captured.out
    assert "Received = 4, Lost = 0" in captured.out

def test_ping_fails_if_forward_route_missing(routed_network, capsys):
    """Tests that the packet drops if R1 doesn't know how to reach PC2."""
    sim = routed_network["sim"]
    r1 = routed_network["r1"]
    pc1 = routed_network["pc1"]
    
    r1.process_command("conf t")
    r1.process_command("no ip route 192.168.2.0 255.255.255.0 10.0.0.2")
    
    sim.ping(pc1, "192.168.2.10")
    captured = capsys.readouterr()
    
    assert "Destination net unreachable" in captured.out
    assert "Received = 0, Lost = 4" in captured.out

def test_ping_fails_if_return_route_missing(routed_network, capsys):
    """Tests that the packet reaches PC2, but fails because R2 doesn't know how to reply to PC1."""
    sim = routed_network["sim"]
    r2 = routed_network["r2"]
    pc1 = routed_network["pc1"]
    
    r2.process_command("conf t")
    r2.process_command("no ip route 192.168.1.0 255.255.255.0 10.0.0.1")
    
    sim.ping(pc1, "192.168.2.10")
    captured = capsys.readouterr()
    
    assert "Request timed out. (Return path failed)" in captured.out
    assert "Received = 0, Lost = 4" in captured.out