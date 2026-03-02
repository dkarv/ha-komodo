from komodo_api.types import ServerState
from ..coordinator import KomodoCoordinator
from .common import KomodoSensor, KomodoOptionSensor
from homeassistant.helpers.device_registry import DeviceInfo
from ..const import DOMAIN


def create_server_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoSensor]:
    """Return a list of sensors, one device per server."""
    sensors: list[KomodoSensor] = []
    for server in coordinator.data.servers.values():
        device_info = DeviceInfo(
            identifiers={(DOMAIN, server.id)},
            name=server.name,
            manufacturer="Komodo",
            sw_version=server.periphery_version,
        )

        item_id = f"{entry_id}_{server.id}"

        def extractor(data, sid=server.id):
            srv = data.get_server(sid)
            return srv.state.name

        def joiner(data, sid=server.id):
            srv = data.get_server(sid)
            if srv.alerts:
                return ", ".join(srv.alerts)
            return ""

        sensors.append(
            KomodoOptionSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=extractor,
                key="server_state",
                device_info=device_info,
                options=[state.name for state in ServerState],
            )
        )
        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=joiner,
                key="alert_list",
                device_info=device_info,
            )
        )

        def stack_counter(data, sid=server.id):
            return data.servers[sid].stack_count

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=stack_counter,
                key="stack_count",
                device_info=device_info,
            )
        )

        def service_counter(data, sid=server.id):
            return data.servers[sid].service_count

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=service_counter,
                key="service_count",
                device_info=device_info,
            )
        )

    return sensors
