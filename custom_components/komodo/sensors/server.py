from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.helpers.device_registry import DeviceInfo
from komodo_api.types import ServerState

from ..const import DOMAIN
from ..coordinator import KomodoCoordinator
from .common import KomodoOptionSensor, KomodoSensor


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
            state = srv.state
            if state is None:
                return None
            return state.name

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

        def cpu_usage(data, sid=server.id):
            return data.get_server(sid).cpu_percent

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=cpu_usage,
                key="cpu_usage",
                device_info=device_info,
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
            )
        )

        def memory_usage(data, sid=server.id):
            return data.get_server(sid).memory_percent

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=memory_usage,
                key="memory_usage",
                device_info=device_info,
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
            )
        )

        def disk_usage(data, sid=server.id):
            return data.get_server(sid).disk_percent

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=disk_usage,
                key="disk_usage",
                device_info=device_info,
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
            )
        )

        def memory_total(data, sid=server.id):
            return data.get_server(sid).memory_total_gb

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=memory_total,
                key="memory_total",
                device_info=device_info,
                native_unit_of_measurement=UnitOfInformation.GIGABYTES,
                device_class=SensorDeviceClass.DATA_SIZE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
            )
        )

        def memory_available(data, sid=server.id):
            return data.get_server(sid).memory_available_gb

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=memory_available,
                key="memory_free",
                device_info=device_info,
                native_unit_of_measurement=UnitOfInformation.GIGABYTES,
                device_class=SensorDeviceClass.DATA_SIZE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
            )
        )

        def disk_total(data, sid=server.id):
            return data.get_server(sid).disk_total_gb

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=disk_total,
                key="disk_total",
                device_info=device_info,
                native_unit_of_measurement=UnitOfInformation.GIGABYTES,
                device_class=SensorDeviceClass.DATA_SIZE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
            )
        )

        def disk_free(data, sid=server.id):
            return data.get_server(sid).disk_free_gb

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=disk_free,
                key="disk_free",
                device_info=device_info,
                native_unit_of_measurement=UnitOfInformation.GIGABYTES,
                device_class=SensorDeviceClass.DATA_SIZE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
            )
        )

        def load_1m(data, sid=server.id):
            return data.get_server(sid).load_average_1m

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=load_1m,
                key="load_1m",
                device_info=device_info,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=2,
            )
        )

    return sensors
