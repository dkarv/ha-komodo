import ipaddress
import re
import asyncio
from komodo_api.lib import KomodoClient
from komodo_api.types import Update, UpdateStatus, GetUpdate
from typing import TYPE_CHECKING
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN

if TYPE_CHECKING:
    from .data.stack import KomodoStack

import logging

_LOGGER = logging.getLogger(__name__)

# DeviceInfo accepts via_device_id (replacing the deprecated via_device) since HA 2026.8.
_SUPPORTS_VIA_DEVICE_ID = (MAJOR_VERSION, MINOR_VERSION) >= (2026, 8)


def create_stack_device_info(
    stack: "KomodoStack", server_device_ids: dict[str, str],
) -> DeviceInfo:
    """Create device info for a stack, linked to the device of its server."""
    device_info = DeviceInfo(
        identifiers={(DOMAIN, stack.id)},
        name=stack.name,
        manufacturer="Komodo",
    )
    if not _SUPPORTS_VIA_DEVICE_ID:
        device_info["via_device"] = (DOMAIN, stack.server_id)
    elif (server_device_id := server_device_ids.get(stack.server_id)) is not None:
        device_info["via_device_id"] = server_device_id
    return device_info


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


_DOCKER_SIZE_UNITS = {
    "b": 1,
    "kb": 1000,
    "mb": 1000**2,
    "gb": 1000**3,
    "tb": 1000**4,
    "kib": 1024,
    "mib": 1024**2,
    "gib": 1024**3,
    "tib": 1024**4,
}
_DOCKER_SIZE_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([a-zA-Z]+)\s*$")


def parse_docker_size(text: str | None) -> float | None:
    """Parse a docker stats size like '12.5MiB' or '1.2kB' into bytes."""
    if not text:
        return None
    match = _DOCKER_SIZE_RE.match(text)
    if match is None:
        return None
    factor = _DOCKER_SIZE_UNITS.get(match.group(2).lower())
    if factor is None:
        return None
    return float(match.group(1)) * factor


def parse_docker_percent(text: str | None) -> float | None:
    """Parse a docker stats percentage like '1.23%' into a float."""
    if not text:
        return None
    try:
        return float(text.strip().rstrip("%"))
    except ValueError:
        return None


def split_docker_pair(text: str | None) -> tuple[str | None, str | None]:
    """Split a docker stats pair like '1.2kB / 3.4MB' into its two halves."""
    if not text:
        return None, None
    parts = text.split("/")
    if len(parts) != 2:
        return None, None
    return parts[0].strip(), parts[1].strip()
