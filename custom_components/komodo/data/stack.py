from typing import Mapping
from komodo_api.types import (
    StackListItem,
	StackState,
	InspectStackContainerResponse,
	ResourceListItem,
)


class KomodoUpdateInfo:
	"""Update information for a service."""
	# TODO

	def __init__(self, info: InspectStackContainerResponse):
		pass

class KomodoStack:
	"""Wrapper for a stack list item returned from the API."""
	state: StackState | None
	id: str
	name: str
	server_id: str
	update_info: Mapping[str, KomodoUpdateInfo] = {}

	def __init__(self, item: ResourceListItem[StackListItem], services: Mapping[str, KomodoUpdateInfo]):
		self.state = item.info.state
		self.id = item.id
		self.name = item.name
		self.server_id = item.info.server_id
		self.update_info = services

	@classmethod
	def unknown(cls) -> "KomodoStack":
		"""Create unknown stack."""
		self = cls.__new__(cls)
		self.state = None
		self.id = "unknown"
		self.name = "unknown"
		self.server_id = "unknown"
		return self
