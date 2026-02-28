import ipaddress
import asyncio
from komodo_api.lib import KomodoClient
from komodo_api.types import Update, UpdateStatus, GetUpdate
from homeassistant.helpers.device_registry import DeviceInfo

import logging

_LOGGER = logging.getLogger(__name__)


def create_stack_device_info(
    stack_id: str, stack_name: str, server_id: str, domain: str
) -> DeviceInfo:
    """Create device info for a stack."""
    return DeviceInfo(
        identifiers={(domain, stack_id)},
        name=stack_name,
        manufacturer="Komodo",
        via_device=(domain, server_id),
    )


def fix_host(host: str) -> str:
    """Normalize the host by adding a protocol."""

    host = host.rstrip("/")

    # If already has a protocol scheme, return as-is
    if host.startswith(("http://", "https://")):
        return host

    try:
        ipaddress.ip_address(host)
        return f"http://{host}"
    except ValueError:
        return f"https://{host}"


async def wait_for_completion(client: KomodoClient, update: Update, title: str):
    while not update.status == UpdateStatus.COMPLETE:
        await asyncio.sleep(1)
        update = await client.read.getUpdate(GetUpdate(id=update.id.oid))

    if update.success:
        _LOGGER.info("%s successful", title)
    else:
        logs = "\n".join(
            f"[{log.stage}] {log.stderr} {log.stdout}" for log in update.logs
        )
        _LOGGER.error("%s failed. Logs:\n%s", title, logs)
    return update
