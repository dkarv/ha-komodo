from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfInformation

from ..const import (
    CONF_CONTAINER_CPU,
    CONF_CONTAINER_DISK,
    CONF_CONTAINER_MEMORY,
    CONF_CONTAINER_NETWORK,
)
from ..coordinator import KomodoCoordinator
from ..utils import create_stack_device_info
from .common import KomodoSensor

_BYTES = (UnitOfInformation.BYTES, SensorDeviceClass.DATA_SIZE)

# key -> (category, KomodoService property, (unit, device class), suggested unit)
CONTAINER_SENSORS = {
    "container_cpu_usage": (CONF_CONTAINER_CPU, "cpu_percent", (PERCENTAGE, None), None),
    "container_memory_used": (CONF_CONTAINER_MEMORY, "memory_used_bytes", _BYTES, UnitOfInformation.MEBIBYTES),
    "container_network_rx": (CONF_CONTAINER_NETWORK, "network_rx_bytes", _BYTES, UnitOfInformation.MEGABYTES),
    "container_network_tx": (CONF_CONTAINER_NETWORK, "network_tx_bytes", _BYTES, UnitOfInformation.MEGABYTES),
    "container_block_read": (CONF_CONTAINER_DISK, "block_read_bytes", _BYTES, UnitOfInformation.MEGABYTES),
    "container_block_write": (CONF_CONTAINER_DISK, "block_write_bytes", _BYTES, UnitOfInformation.MEGABYTES),
}


def container_sensor_category(unique_id: str) -> str | None:
    """Return the category of a container sensor, None for other entities."""
    for key, (category, *_) in CONTAINER_SENSORS.items():
        if unique_id.endswith(f"_{key}"):
            return category
    return None


def create_container_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
    enabled_categories: frozenset[str],
) -> list[KomodoSensor]:
    """Return diagnostic sensors for every stack service container.

    No state class is set on purpose, so Home Assistant doesn't keep
    long-term statistics for these (potentially many) sensors.
    """
    sensors: list[KomodoSensor] = []
    for stack in coordinator.data.stacks.values():
        device_info = create_stack_device_info(stack, coordinator.server_device_ids)

        for service in stack.services.values():
            item_id = f"{entry_id}_{stack.id}_{service.name}"

            for key, (category, attr, (unit, device_class), suggested_unit) in CONTAINER_SENSORS.items():

                def extractor(data, sid=stack.id, name=service.name, attr=attr):
                    stk = data.stacks.get(sid)
                    svc = stk.services.get(name) if stk else None
                    return getattr(svc, attr) if svc else None

                sensors.append(
                    KomodoSensor(
                        coordinator=coordinator,
                        item_id=item_id,
                        extractor=extractor,
                        key=key,
                        device_info=device_info,
                        native_unit_of_measurement=unit,
                        device_class=device_class,
                        suggested_unit_of_measurement=suggested_unit,
                        suggested_display_precision=1,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        enabled_default=category in enabled_categories,
                        translation_placeholders={"service": service.name},
                    )
                )

    return sensors
