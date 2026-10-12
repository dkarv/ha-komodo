from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfInformation

from ..coordinator import KomodoCoordinator
from ..utils import create_stack_device_info
from .common import KomodoSensor

_BYTES = (UnitOfInformation.BYTES, SensorDeviceClass.DATA_SIZE)

# key -> (KomodoService property, (unit, device class), suggested unit)
CONTAINER_SENSORS = {
    "container_cpu_usage": ("cpu_percent", (PERCENTAGE, None), None),
    "container_memory_used": ("memory_used_bytes", _BYTES, UnitOfInformation.MEBIBYTES),
    "container_network_rx": ("network_rx_bytes", _BYTES, UnitOfInformation.MEGABYTES),
    "container_network_tx": ("network_tx_bytes", _BYTES, UnitOfInformation.MEGABYTES),
    "container_block_read": ("block_read_bytes", _BYTES, UnitOfInformation.MEGABYTES),
    "container_block_write": ("block_write_bytes", _BYTES, UnitOfInformation.MEGABYTES),
}


def is_container_sensor(unique_id: str) -> bool:
    """True when the unique id belongs to a container sensor."""
    return any(unique_id.endswith(f"_{key}") for key in CONTAINER_SENSORS)


def create_container_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
    enabled_default: bool,
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

            for key, (attr, (unit, device_class), suggested_unit) in CONTAINER_SENSORS.items():

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
                        enabled_default=enabled_default,
                        translation_placeholders={"service": service.name},
                    )
                )

    return sensors
