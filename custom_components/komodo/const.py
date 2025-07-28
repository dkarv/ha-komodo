"""Constants for the Komodo integration."""
from homeassistant.const import CONF_HOST, CONF_API_KEY, CONF_CLIENT_SECRET

DOMAIN = "komodo"
CONF_HOST = CONF_HOST
CONF_API_KEY = CONF_API_KEY
CONF_API_SECRET = CONF_CLIENT_SECRET


def normalize_host_url(host: str) -> str:
    """Normalize host URL by adding protocol scheme if missing.
    
    Args:
        host: The host URL that may or may not include a protocol scheme
        
    Returns:
        A properly formatted URL with protocol scheme
    """
    if not host:
        return host
        
    # Remove any trailing slashes
    host = host.rstrip('/')
    
    # If already has a protocol scheme, return as-is
    if host.startswith(('http://', 'https://')):
        return host
    
    # Default to HTTPS for security, but allow HTTP for localhost/private IPs
    # RFC 1918 private IP ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
    # Plus localhost and 127.0.0.0/8
    is_private = (
        host.startswith('localhost') or 
        host.startswith('127.') or 
        host.startswith('192.168.') or 
        host.startswith('10.') or
        # 172.16.0.0/12 (172.16.0.0 to 172.31.255.255)
        (host.startswith('172.') and _is_172_private(host))
    )
    
    if is_private:
        return f"http://{host}"
    else:
        return f"https://{host}"


def _is_172_private(host: str) -> bool:
    """Check if a host starting with 172. is in the private range 172.16.0.0/12."""
    try:
        # Extract the second octet to check if it's in range 16-31
        parts = host.split('.')
        if len(parts) >= 2:
            second_octet = int(parts[1].split(':')[0])  # Handle port numbers
            return 16 <= second_octet <= 31
    except (ValueError, IndexError):
        pass
    return False
