from ..coordinator import KomodoCoordinator
from .common import KomodoSensor
from homeassistant.helpers.device_registry import DeviceInfo
from ..const import DOMAIN


def create_alert_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """

    def counter(data):
        return data.alert_count if data.alert_count is not None else 0

    def joiner(data):
        if data.alert_list:
            return ", ".join(data.alert_list)
        return ""

    base_url = coordinator.host_url
    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_global")},
        name="Komodo Alerts",
        manufacturer="Komodo",
        sw_version=coordinator.komodo_version,
        configuration_url=f"{base_url.rstrip('/')}/alerts" if base_url else None,
    )

    return [
        KomodoSensor(
            coordinator=coordinator,
            item_id=f"{entry_id}_global",
            extractor=counter,
            key="alert_count",
            device_info=device_info,
        ),
        KomodoSensor(
            coordinator=coordinator,
            item_id=f"{entry_id}_global",
            extractor=joiner,
            key="alert_list",
            device_info=device_info,
        ),
    ]
