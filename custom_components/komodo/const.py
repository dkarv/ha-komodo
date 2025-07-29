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
    
    # Use HTTP for all IP addresses, HTTPS for domain names
    if _is_ip_address(host):
        return f"http://{host}"
    else:
        return f"https://{host}"


def _is_ip_address(host: str) -> bool:
    """Check if the host is an IP address (IPv4 or IPv6)."""
    import ipaddress
    
    try:
        # For IPv6, we need to handle bracket notation and ports differently
        if '[' in host and ']' in host:
            # IPv6 with brackets: [::1]:8080
            ip_part = host.split(']')[0][1:]  # Extract between brackets
        elif ':' in host and host.count(':') > 1:
            # Likely IPv6 without brackets
            ip_part = host
        else:
            # IPv4 or IPv6 with port: 192.168.1.1:8080
            ip_part = host.split(':')[0]
        
        # Try to parse as IP address
        ipaddress.ip_address(ip_part)
        return True
    except ValueError:
        # Also check for localhost
        return host.startswith('localhost')
    except Exception:
        return False
