import pytest
from custom_components.komodo.utils import fix_host

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
