# Arrange servers into a mapping where the key is the name property
from typing import List, Mapping, Optional

from komodo_api.types import (
    ListAlertsResponse,
    ListServersResponse,
    ListStacksResponse,
    ResourceTargetServer,
    ResourceTargetStack,
)

from .server import KomodoServer
from .service import KomodoService
from .stack import KomodoStack


class KomodoData:
    """Wrapper to represent all data fetched from the API."""

    servers: Mapping[str, KomodoServer] = {}
    stacks: Mapping[str, KomodoStack] = {}
    alert_count: Optional[int] = None
    alert_list: Optional[List[str]] = None

    def add_servers(self, servers: ListServersResponse):
        """Add servers from response."""
        for server in servers:
            self.servers[server.id] = KomodoServer(server)

    def get_server(self, server_id: str) -> KomodoServer:
        """Get server by ID."""
        server = self.servers.get(server_id)
        if server is None:
            server = KomodoServer.unknown(server_id)
            self.servers[server_id] = server
        return server

    def add_stacks(self, stacks: ListStacksResponse):
        """Add stacks from response.
        services: Mapping of (stack_id, service_name) to service details.
        """
        for _stack in stacks:
            stack = KomodoStack(_stack)
            self.stacks[_stack.id] = stack

            # Update server stack count
            server = self.get_server(_stack.info.server_id)
            server.add_stack()
            server.add_services(len(_stack.info.services))

            for service in _stack.info.services:
                stack.add_service(KomodoService(service))

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
                self.get_server(alert.target.id).add_alert(alert)
            elif isinstance(alert.target, ResourceTargetStack):
                self.get_stack(alert.target.id).add_alert(alert)
