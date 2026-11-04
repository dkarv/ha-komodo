from ..coordinator import KomodoCoordinator
from ..utils import create_komodo_main_device_info
from .common import KomodoSensor


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

    device_info = create_komodo_main_device_info(entry_id, coordinator)

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
