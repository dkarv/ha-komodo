"""Pytest configuration and mocks for ha-komodo."""

import sys
import types
from unittest.mock import MagicMock
from importlib.machinery import ModuleSpec

try:
    import homeassistant
except ImportError:
    class BaseMockEntity:
        def __init__(self, *args, **kwargs):
            self.coordinator = args[0] if args else None
            self.hass = getattr(self.coordinator, "hass", None)

        def __class_getitem__(cls, item):
            return cls

        def __getattr__(self, name):
            attr_name = f"_attr_{name}"
            if attr_name in self.__dict__:
                return self.__dict__[attr_name]
            raise AttributeError(f"{type(self).__name__} object has no attribute {name}")

    class AutoMockModule(types.ModuleType):
        def __getattr__(self, name):
            if name.endswith("Entity") or name in ("Entity", "CoordinatorEntity", "DataUpdateCoordinator"):
                cls = type(name, (BaseMockEntity,), {})
                setattr(self, name, cls)
                return cls
            val = MagicMock()
            setattr(self, name, val)
            return val

    class HAMockFinder:
        def find_spec(self, fullname, path, target=None):
            if fullname.startswith("homeassistant"):
                return ModuleSpec(fullname, self, is_package=True)
            return None

        def create_module(self, spec):
            mod = AutoMockModule(spec.name)
            mod.__path__ = []
            return mod

        def exec_module(self, module):
            pass

    sys.meta_path.insert(0, HAMockFinder())

    import homeassistant.const
    homeassistant.const.MAJOR_VERSION = 2026
    homeassistant.const.MINOR_VERSION = 11
    homeassistant.core.callback = lambda fn: fn
