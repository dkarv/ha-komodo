import pytest
from unittest.mock import MagicMock

from custom_components.komodo.utils import create_stack_device_info, fix_host, parse_docker_percent, parse_docker_size, split_docker_pair

@pytest.mark.parametrize("input_host,expected", [
    ("http://192.168.1.1", "http://192.168.1.1"),
    ("https://example.com", "https://example.com"),
    ("192.168.1.1", "http://192.168.1.1"),
    ("example.com", "https://example.com"),
    ("192.168.1.1/", "http://192.168.1.1"),
    ("example.com/", "https://example.com"),
    ("http://example.com/", "http://example.com"),
    ("https://192.168.1.1/", "https://192.168.1.1"),
])
def test_fix_host(input_host, expected):
    assert fix_host(input_host) == expected


@pytest.mark.parametrize("text,expected", [
    ("12.5MiB", 12.5 * 1024**2),
    ("1.2kB", 1200),
    ("0B", 0),
    ("3GB", 3 * 1000**3),
    ("1.5GiB", 1.5 * 1024**3),
    ("--", None),
    ("", None),
    (None, None),
    ("12XB", None),
])
def test_parse_docker_size(text, expected):
    assert parse_docker_size(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("1.2kB / 3.4MB", ("1.2kB", "3.4MB")),
    ("12MiB / 1.9GiB", ("12MiB", "1.9GiB")),
    ("--", (None, None)),
    (None, (None, None)),
])
def test_split_docker_pair(text, expected):
    assert split_docker_pair(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("1.23%", 1.23),
    ("250.5%", 250.5),
    ("0.00%", 0.0),
    ("--", None),
    ("", None),
    (None, None),
])
def test_parse_docker_percent(text, expected):
    assert parse_docker_percent(text) == expected


def test_unassigned_stack_device_has_no_parent():
    stack = MagicMock(id="s1", server_id=None)
    stack.name = "s1"
    info = create_stack_device_info(stack, {"": "dev"})
    assert "via_device" not in info
    assert "via_device_id" not in info


def test_create_stack_device_info_configuration_url():
    stack = MagicMock(id="s1", server_id="srv1")
    stack.name = "jarvis"
    stack.deployed_hash = "641203c12345678"
    stack.branch = "main"

    # With base_url and deployed_hash
    info = create_stack_device_info(stack, {"srv1": "dev_srv1"}, base_url="https://komodo.example.com")
    assert info["configuration_url"] == "https://komodo.example.com/stacks/s1"
    assert info["sw_version"] == "641203c1"

    # Without deployed_hash and branch="main", sw_version should be None (no "Firmware: main")
    stack.deployed_hash = None
    info_branch_main = create_stack_device_info(stack, {"srv1": "dev_srv1"})
    assert info_branch_main["sw_version"] is None

    # With a custom non-default branch, sw_version should be the branch
    stack.branch = "feature/awesome"
    info_branch_custom = create_stack_device_info(stack, {"srv1": "dev_srv1"})
    assert info_branch_custom["sw_version"] == "feature/awesome"

    # Without base_url
    info_no_url = create_stack_device_info(stack, {"srv1": "dev_srv1"})
    assert info_no_url.get("configuration_url") is None


def test_create_komodo_main_device_info():
    from unittest.mock import MagicMock

    from custom_components.komodo.const import DOMAIN
    from custom_components.komodo.utils import create_komodo_main_device_info

    coordinator = MagicMock()
    coordinator.komodo_version = "2.3.3"
    coordinator.host_url = "https://komodo.example.com"

    info = create_komodo_main_device_info("entry_123", coordinator)
    assert info["identifiers"] == {(DOMAIN, "entry_123")}
    assert info["name"] == "Komodo"
    assert info["manufacturer"] == "Komodo"
    assert info["model"] == "Fleet Controller"
    assert info["sw_version"] == "2.3.3"
    assert info["configuration_url"] == "https://komodo.example.com"

