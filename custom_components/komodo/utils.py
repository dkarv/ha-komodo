import asyncio
import ipaddress
import re
from typing import TYPE_CHECKING

from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.helpers.device_registry import DeviceInfo
from komodo_api.lib import KomodoClient
from komodo_api.types import GetUpdate, Update, UpdateStatus

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import KomodoCoordinator
    from .data.action import KomodoAction
    from .data.build import KomodoBuild
    from .data.procedure import KomodoProcedure
    from .data.stack import KomodoStack

import logging

_LOGGER = logging.getLogger(__name__)

# DeviceInfo accepts via_device_id (replacing the deprecated via_device) since HA 2026.8.
_SUPPORTS_VIA_DEVICE_ID = (MAJOR_VERSION, MINOR_VERSION) >= (2026, 8)


def create_komodo_main_device_info(
    entry_id: str,
    coordinator: "KomodoCoordinator",
) -> DeviceInfo:
    """Create device info for the central Komodo Core device."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="Komodo",
        manufacturer="Komodo",
        model="Fleet Controller",
        sw_version=coordinator.komodo_version,
        configuration_url=coordinator.host_url,
    )


def create_stack_device_info(
    stack: "KomodoStack",
    server_device_ids: dict[str, str],
    base_url: str | None = None,
) -> DeviceInfo:
    """Create device info for a stack, linked to the device of its server."""
    config_url = f"{base_url.rstrip('/')}/stacks/{stack.id}" if base_url else None
    sw_ver = None
    if stack.deployed_hash:
        sw_ver = stack.deployed_hash[:8]
    elif stack.branch and stack.branch.lower() not in (
        "main",
        "master",
        "head",
        "trunk",
        "default",
    ):
        sw_ver = stack.branch
    device_info = DeviceInfo(
        identifiers={(DOMAIN, stack.id)},
        name=stack.name,
        manufacturer="Komodo",
        sw_version=sw_ver,
        configuration_url=config_url,
    )
    if not stack.server_id:
        # Unassigned stack: there is no server device to link to.
        return device_info
    if not _SUPPORTS_VIA_DEVICE_ID:
        device_info["via_device"] = (DOMAIN, stack.server_id)
    elif (server_device_id := server_device_ids.get(stack.server_id)) is not None:
        device_info["via_device_id"] = server_device_id
    return device_info


def create_build_device_info(
    build: "KomodoBuild",
    base_url: str | None = None,
) -> DeviceInfo:
    """Create device info for a build pipeline."""
    config_url = f"{base_url.rstrip('/')}/builds/{build.id}" if base_url else None
    sw_ver = None
    if build.version and build.version.lower() not in (
        "main",
        "master",
        "head",
        "trunk",
        "default",
    ):
        sw_ver = build.version
    elif build.built_hash:
        sw_ver = build.built_hash[:8]
    return DeviceInfo(
        identifiers={(DOMAIN, f"build_{build.id}")},
        name=f"Build {build.name}",
        manufacturer="Komodo",
        model="CI/CD Build Pipeline",
        sw_version=sw_ver,
        configuration_url=config_url,
    )


def create_procedure_device_info(
    procedure: "KomodoProcedure",
    base_url: str | None = None,
) -> DeviceInfo:
    """Create device info for a procedure."""
    config_url = f"{base_url.rstrip('/')}/procedures/{procedure.id}" if base_url else None
    return DeviceInfo(
        identifiers={(DOMAIN, f"procedure_{procedure.id}")},
        name=f"Procedure {procedure.name}",
        manufacturer="Komodo",
        model="Procedure Runbook",
        configuration_url=config_url,
    )


def create_action_device_info(
    action: "KomodoAction",
    base_url: str | None = None,
) -> DeviceInfo:
    """Create device info for an action."""
    config_url = f"{base_url.rstrip('/')}/actions/{action.id}" if base_url else None
    return DeviceInfo(
        identifiers={(DOMAIN, f"action_{action.id}")},
        name=f"Action {action.name}",
        manufacturer="Komodo",
        model="Action Command",
        configuration_url=config_url,
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
    while update.status != UpdateStatus.COMPLETE:
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
