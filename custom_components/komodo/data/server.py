from komodo_api.types import (
    ServerListItem,
	ServerState,
	ResourceListItem,
)

class KomodoServer:
	"""Wrapper for a server list item returned from the API."""
	state: ServerState | None
	id: str
	name: str

	def __init__(self, item: ResourceListItem[ServerListItem]):
		self.state = item.info.state
		self.id = item.id
		self.name = item.name

	@classmethod
	def unknown(cls) -> "KomodoServer":
		"""Create unknown server."""
		self = cls.__new__(cls)
		self.state = None
		return self

