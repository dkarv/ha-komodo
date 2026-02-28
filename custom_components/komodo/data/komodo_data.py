
# Arrange servers into a mapping where the key is the name property
from typing import Mapping, Optional, List

from .server import KomodoServer
from .stack import KomodoStack
from .service import KomodoService
from komodo_api.types import (
    ListServersResponse,
    ListStacksResponse,
    ListAlertsResponse,
    ServerListItem,
    StackListItem,
    ResourceTargetServer,
    ResourceTargetStack,
    ListStackServicesResponse,
)

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
        server = self.servers[server_id]
        if server is None:
            server = KomodoServer.unknown()
            self.servers[server_id] = server
        return server

    def add_stacks(self, stacks: ListStacksResponse):
        """Add stacks from response.
        services: Mapping of (stack_id, service_name) to service details.
        """
        for _stack in stacks:
            self.stacks[_stack.id] = KomodoStack(_stack)
    
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
        self.alert_list = [alert.data.type for alert in alerts.alerts]
        for alert in alerts.alerts:
            if isinstance(alert.target, ResourceTargetServer):
                self.get_server(alert.target.id).add_alert(alert)
            elif isinstance(alert.target, ResourceTargetStack):
                self.get_stack(alert.target.id).add_alert(alert)

    def add_services(self, stack_id: str, 
                     services: List[KomodoService],
                     ):
        """Add services for a stack from response."""
        stack = self.get_stack(stack_id)

        for service in services:
            stack.add_service(service)
