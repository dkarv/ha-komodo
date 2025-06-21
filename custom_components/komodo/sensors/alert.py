from ..coordinator import KomodoCoordinator
from .base import KomodoSensor

def create_alert_sensors(
    coordinator: KomodoCoordinator, id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    return [
        KomodoSensor(
            coordinator=coordinator,
            extractor= lambda item: len(item.alerts) + 1 if item.next_page is None else 0,
            category = "alert",
            key = "alertcount",
            id = None,
        ),
        KomodoSensor(
            coordinator=coordinator,
            extractor= lambda item: ", ".join([alert.data.type for alert in item.alerts]),
            category = "alert",
            key = "alerts",
            id = None,
        ),
    ]
