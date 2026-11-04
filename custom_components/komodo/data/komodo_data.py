# Arrange servers into a mapping where the key is the name property
from typing import List, Mapping, Optional

from komodo_api.types import (
    ListAlertsResponse,
    ListAllStackServicesResponse,
    ListBuildsResponse,
    ListServersResponse,
    ListStacksResponse,
    ResourceTargetServer,
    ResourceTargetStack,
)

from .build import KomodoBuild
from .server import KomodoServer
from .service import KomodoService
from .stack import KomodoStack


class KomodoData:
    """Wrapper to represent all data fetched from the API."""

    servers: dict[str, KomodoServer]
    stacks: dict[str, KomodoStack]
    builds: dict[str, KomodoBuild]
    alert_count: Optional[int]
    alert_list: Optional[List[str]]

    def __init__(self):
        self.servers = {}
        self.stacks = {}
        self.builds = {}
        self.alert_count = None
        self.alert_list = None

    def add_servers(self, servers: ListServersResponse):
        """Add servers from response."""
        for server in servers:
            self.servers[server.id] = KomodoServer(server)

    def get_server(self, server_id: str | None, server_name: str | None = None) -> KomodoServer | None:
        """Get server by ID, creating unknown server placeholder only if ID is non-empty."""
        if not server_id:
            return None
        server = self.servers.get(server_id)
        if server is None:
            server = KomodoServer.unknown(server_id, server_name=server_name)
            self.servers[server_id] = server
        elif server_name and server.is_unknown and server.name.startswith("Unknown Server"):
            server.name = server_name
        return server

    def add_stacks(self, stacks: ListStacksResponse):
        """Add stacks from response.
        services: Mapping of (stack_id, service_name) to service details.
        """
        for _stack in stacks:
            stack = KomodoStack(_stack)
            self.stacks[_stack.id] = stack

            # Update server stack count if assigned to a server
            server = self.get_server(stack.server_id, server_name=stack.server_name)
            if server:
                server.add_stack()
                server.add_services(len(_stack.info.services))

            for service in _stack.info.services:
                stack.add_service(KomodoService(service))

    def add_builds(self, builds: ListBuildsResponse):
        """Add builds from response."""
        for build in builds:
            self.builds[build.id] = KomodoBuild(build)

    def add_stack_services(self, services: ListAllStackServicesResponse):
        """Attach container state/image/labels/digests to the services from add_stacks.

        Must run after add_stacks. Services without a container (stack down,
        server unreachable, swarm mode) keep state None.
        """
        for item in services:
            stack = self.stacks.get(item.stack_id)
            if stack is None:
                continue
            service = stack.services.get(item.service)
            if service is not None:
                if hasattr(service, "apply_stack_service"):
                    service.apply_stack_service(item)
                elif item.container is not None:
                    service.apply_container(item.container)

    def get_stack(self, stack_id: str) -> KomodoStack:
        """Get stack by ID."""
        stack = self.stacks.get(stack_id)
        if stack is None:
            stack = KomodoStack.unknown(stack_id)
            self.stacks[stack_id] = stack
        return stack

    def add_alerts(self, alerts: ListAlertsResponse):
        """Add alerts from response."""
        self.alert_count = len(alerts.alerts) + (0 if alerts.next_page is None else 99)
        self.alert_list = [alert.data.type for alert in alerts.alerts]
        for alert in alerts.alerts:
            if isinstance(alert.target, ResourceTargetServer):
                srv = self.get_server(alert.target.id)
                if srv:
                    srv.add_alert(alert)
            elif isinstance(alert.target, ResourceTargetStack):
                self.get_stack(alert.target.id).add_alert(alert)
