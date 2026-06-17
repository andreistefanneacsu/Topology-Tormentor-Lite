import pytest
import json
from unittest.mock import patch, mock_open
from Devices.devices import Device

@pytest.fixture
def router():
    return Device(name="Router1", dev_type="router")

def test_device_initialization(router):
    assert router.name == "Router1"
    assert router.hostname == "Router1"
    assert router.cli_mode == 0
    assert router.config["cdp_run"] is True 

def test_to_dict_format(router):
    router.config["default-gateway"] = "192.168.1.1"
    router.config["banner_motd"] = "Authorized Access Only"
    data = router.to_dict()
    assert data["name"] == "Router1"
    assert data["config"]["default-gateway"] == "192.168.1.1"
    assert data["config"]["banner_motd"] == "Authorized Access Only"

def test_domain_lookup_delay(router):
    router.cli_mode = 1
    response = router.process_command("comanda-gresita")

    assert "Translating" in response
    assert "Unknown command" in response

    router.cli_mode = 2
    router.process_command("no ip domain-lookup")
    assert router.config["ip_domain_lookup"] is False
    router.cli_mode = 1
    response = router.process_command("comanda-gresita-din-nou")
    assert "Translating" not in response
    assert "Invalid input" in response

def test_advanced_config_commands(router):
    router.cli_mode = 2
    
    router.process_command("username cisco privilege 15 secret pass123")
    assert "cisco" in router.config["users"]
    assert router.config["users"]["cisco"]["privilege"] == 15
    assert router.config["users"]["cisco"]["is_secret"] is True
    
    router.process_command("login block-for 120 attempts 3 within 60")
    assert router.config["login_block"]["block_for"] == 120
    assert router.config["login_block"]["attempts"] == 3
    
    router.process_command("line vty 0 15")
    assert router.cli_mode == 3
    router.process_command("password telnetpass")
    router.process_command("transport input ssh")
    
    vty_config = router.config["lines"]["vty 0 15"]
    assert vty_config["password"] == "telnetpass"
    assert vty_config["transport_input"] == ["ssh"]

def test_no_commands(router):
    router.cli_mode = 2
    router.process_command("cdp run")
    assert router.config["cdp_run"] is True
    router.process_command("no cdp run")
    assert router.config["cdp_run"] is False
    
    router.process_command("service password-encryption")
    assert router.config["service_password_encryption"] is True
    router.process_command("no service password-encryption")
    assert router.config["service_password_encryption"] is False

@patch("builtins.open", new_callable=mock_open)
def test_copy_run_start_saves_file(mock_file, router):
    router.cli_mode = 1
    response = router.process_command("copy run start")
    assert "Building configuration" in response
    mock_file.assert_called_once_with(f"{router.id}.json", 'w')