"""
utils/registry.py

Plugin registry metaclass for automatic registration of plugins.

This module defines a metaclass `PluginRegistry` that automatically
registers any class that uses it as a metaclass into a central registry.
"""

class PluginRegistry(type):
    """
    Metaclass for automatic plugin registration.
    Upon class creation, registers the class in the `registry` dictionary.
    """
    registry = {}

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        if name != "BasePlugin":
            cls.registry[name] = new_cls
        return new_cls


class BasePlugin(metaclass=PluginRegistry):
    pass