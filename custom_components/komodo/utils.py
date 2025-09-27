import ipaddress
import asyncio
from komodo_api.lib import KomodoClient
from komodo_api.types import Update, UpdateStatus, GetUpdate

import logging

_LOGGER = logging.getLogger(__name__)

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

async def wait_for_completion(client: KomodoClient, update: Update, title: str):
    while not update.status == UpdateStatus.COMPLETE:
        await asyncio.sleep(1)
        update = await client.read.getUpdate(GetUpdate(id = update.id.oid))
    
    if update.success:
        _LOGGER.info("%s successful", title)
    else:
        logs = "\n".join(f"[{log.stage}] {log.stderr} {log.stdout}" for log in update.logs)
        _LOGGER.error("%s failed. Logs:\n%s", title, logs)
    return update
