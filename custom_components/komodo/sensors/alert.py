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

    return [
        KomodoSensor(
            coordinator=coordinator,
            item_id=f"{entry_id}_global",
            extractor=counter,
            key="alert_count",
        ),
        KomodoSensor(
            coordinator=coordinator,
            item_id=f"{entry_id}_global",
            extractor=joiner,
            key="alert_list",
        ),
    ]
