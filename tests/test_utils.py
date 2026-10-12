import pytest
from custom_components.komodo.utils import fix_host, parse_docker_percent, parse_docker_size, split_docker_pair

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
