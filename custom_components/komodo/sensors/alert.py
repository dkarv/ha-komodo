from ..coordinator import KomodoCoordinator
from .common import KomodoSensor

def create_alert_sensors(
    coordinator: KomodoCoordinator, 
    id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    if coordinator.data.alerts is None:
        return []
    return [
        KomodoSensor(
            coordinator=coordinator,
            id = id,
            extractor= lambda item: len(item.alerts.alerts) + 0 if item.alerts.next_page is None else 1,
            category = "alert",
            key = "alertcount",
            name = None,
        ),
        KomodoSensor(
            coordinator=coordinator,
            id = id,
            extractor= lambda item: ", ".join([alert.data.type for alert in item.alerts.alerts]),
            category = "alert",
            key = "alerts",
            name = None,
        ),
    ]
