"""
utils/registry.py

Plugin registration utilities.

This module provides a PluginRegistry metaclass that
automatically registers classes by a specified name.
"""

from typing import Dict, Type


class PluginRegistry(type):
    """
    Metaclass that auto-registers plugins by name.

    Classes using this metaclass should define a class-level
    attribute `name` which will be used as the registration key.
    """

    _registry: Dict[str, Type] = {}

    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)

        plugin_name = namespace.get("name")

        if plugin_name:
            if plugin_name in mcls._registry:
                raise RuntimeError(
                    f"Duplicate plugin name: {plugin_name}"
                )
            mcls._registry[plugin_name] = cls

        return cls

    @classmethod
    def get_plugin(mcls, name: str):
        if name not in mcls._registry:
            raise KeyError(f"No plugin registered for '{name}'")
        return mcls._registry[name]

    @classmethod
    def all_plugins(mcls):
        return dict(mcls._registry)

    @classmethod
    def clear_registry(mcls):
        """Clear all registered plugins (useful for testing)."""
        mcls._registry.clear()
