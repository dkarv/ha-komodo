"""Constants for the Komodo integration."""

from homeassistant.const import CONF_HOST, CONF_API_KEY, CONF_CLIENT_SECRET

DOMAIN = "komodo"
CONF_HOST = CONF_HOST
CONF_API_KEY = CONF_API_KEY
CONF_API_SECRET = CONF_CLIENT_SECRET
# Legacy option, replaced by the per-category options below
CONF_CONTAINER_ENTITIES = "container_entities"
CONF_CONTAINER_CPU = "container_cpu"
CONF_CONTAINER_MEMORY = "container_memory"
CONF_CONTAINER_NETWORK = "container_network"
CONF_CONTAINER_DISK = "container_disk"
CONTAINER_CATEGORIES = (
    CONF_CONTAINER_CPU,
    CONF_CONTAINER_MEMORY,
    CONF_CONTAINER_NETWORK,
    CONF_CONTAINER_DISK,
)


def enabled_container_categories(options) -> frozenset[str]:
    """Return the container sensor categories enabled in the entry options.

    Entries created before the per-category options only have the legacy
    CONF_CONTAINER_ENTITIES flag, which applies to all categories.
    """
    legacy = options.get(CONF_CONTAINER_ENTITIES, False)
    return frozenset(c for c in CONTAINER_CATEGORIES if options.get(c, legacy))
