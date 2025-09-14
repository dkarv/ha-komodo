import ipaddress

def fix_host(host: str) -> str:
    """Normalize the host by adding a protocol."""

    host = host.rstrip('/')

    # If already has a protocol scheme, return as-is
    if host.startswith(('http://', 'https://')):
        return host
    
    try:
        ipaddress.ip_address(host)
        return f"http://{host}"
    except ValueError:
        return f"https://{host}"
