"""
test_plugins.py

Tests for plugin registry system.
"""

import unittest

from utils.registry import PluginRegistry


class TestPluginRegistry(unittest.TestCase):
    """Test plugin registration and retrieval."""

    def test_missing_plugin_raises_keyerror(self):
        """Test that accessing non-existent plugin raises KeyError."""
        with self.assertRaises(KeyError):
            PluginRegistry.get_plugin("does_not_exist")

    def test_plugin_registration(self):
        """Test that plugins register correctly."""
        
        class TestPlugin(metaclass=PluginRegistry):
            name = "test_plugin"
            
            def run(self):
                return "test"

        retrieved = PluginRegistry.get_plugin("test_plugin")
        self.assertEqual(retrieved, TestPlugin)
        
        # Should be able to instantiate
        instance = retrieved()
        self.assertEqual(instance.run(), "test")

    def test_duplicate_plugin_name_rejected(self):
        """Test that duplicate plugin names raise RuntimeError."""
        
        class FirstPlugin(metaclass=PluginRegistry):
            name = "duplicate_name"
        
        with self.assertRaises(RuntimeError):
            class SecondPlugin(metaclass=PluginRegistry):
                name = "duplicate_name"

    def test_plugin_without_name_not_registered(self):
        """Test that plugins without name attribute are not registered."""
        
        class UnnamedPlugin(metaclass=PluginRegistry):
            pass
        
        # Should not raise error, just not registered
        all_plugins = PluginRegistry.all_plugins()
        self.assertNotIn(None, all_plugins)

    def test_all_plugins_returns_dict(self):
        """Test that all_plugins returns dictionary of registered plugins."""
        
        class PluginA(metaclass=PluginRegistry):
            name = "plugin_a"
        
        class PluginB(metaclass=PluginRegistry):
            name = "plugin_b"
        
        all_plugins = PluginRegistry.all_plugins()
        self.assertIsInstance(all_plugins, dict)
        self.assertIn("plugin_a", all_plugins)
        self.assertIn("plugin_b", all_plugins)


if __name__ == "__main__":
    unittest.main()
