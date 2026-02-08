
# Arrange servers into a mapping where the key is the name property
from typing import Mapping, Optional

from .server import KomodoServer
from .stack import KomodoStack, KomodoUpdateInfo
from komodo_api.types import (
    ListServersResponse,
    ListStacksResponse,
    ListAlertsResponse,
    ListServers,
    ListStacks,
    ListAlerts,
    ServerListItem,
    StackListItem,
    ResourceTargetServer,
    ResourceTargetStack,
    InspectStackContainerResponse,
)


def arrange_servers_by_name(
    servers: ListServersResponse | None,
) -> Mapping[str, ServerListItem]:
    if servers is None:
        return {}
    return {server.name: server for server in servers if hasattr(server, "name")}


# Arrange stacks into a mapping where the key is the name property
def arrange_stacks_by_name(
    stacks: ListStacksResponse | None,
) -> Mapping[str, StackListItem]:
    if stacks is None:
        return {}
    return {stack.name: stack for stack in stacks if hasattr(stack, "name")}


class KomodoData:
    """Wrapper to represent all data fetched from the API."""
    servers: Mapping[str, KomodoServer] = {}
    stacks: Mapping[str, KomodoStack] = {}
    alert_count: Optional[int] = None

    def add_servers(self, servers: ListServersResponse):
        """Add servers from response."""
        for server in servers:
            self.servers[server.id] = KomodoServer(server)
    
    def get_server(self, server_id: str) -> KomodoServer:
        """Get server by ID."""
        server = self.servers[server_id]
        if server is None:
            server = KomodoServer.unknown()
            self.servers[server_id] = server
        return server

    def add_stacks(self, stacks: ListStacksResponse, services: Mapping[str, Mapping[str, KomodoUpdateInfo]]):
        """Add stacks from response.
        services: Mapping of (stack_id, service_name) to service details.
        """
        for _stack in stacks:
            stack = KomodoStack(_stack, services[_stack.id])
            self.stacks[_stack.id] = stack
    
    def get_stack(self, stack_id: str) -> KomodoStack:
        """Get stack by ID."""
        stack = self.stacks[stack_id]
        if stack is None:
            stack = KomodoStack.unknown()
            self.stacks[stack_id] = stack
        return stack

    def add_alerts(self, alerts: ListAlertsResponse):
        """Add alerts from response."""
        self.alert_count = len(alerts.alerts) + (0 if alerts.next_page is None else 99)
        # TODO currently only server and stack alerts are processed
        for alert in alerts.alerts:
            if isinstance(alert.target, ResourceTargetServer):
                self.get_server(alert.target.id).add_alert(alert)
            elif isinstance(alert.target, ResourceTargetStack):
                self.get_stack(alert.target.id).add_alert(alert)
            