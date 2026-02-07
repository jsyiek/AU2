from typing import Any

from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.plugins.AbstractPlugin import AbstractPlugin


class __PluginMap:
    """
    Stores the plugins that are available
    Most conveniently accessed as an iteration.
    """
    def __init__(self, plugins):
        self.update(plugins)

    def __iter__(self):
        """
        You can access plugins using syntax such as `for plugin in pluginMap`
        """
        yield from [p for p in self.plugins.values() if p.enabled]

    def __getitem__(self, item: str):
        """
        If there is a particular plugin you want and you know the ID, you can do
        `pluginMap["CorePlugin"]`
        """
        return self.plugins[item]

    def update(self, plugins: dict[str, AbstractPlugin]):
        # I refuse to allow users to disable the CorePlugin... because then the entire app would break
        GENERIC_STATE_DATABASE.plugin_map["CorePlugin"] = True

        for p in plugins.values():
            GENERIC_STATE_DATABASE.plugin_map.setdefault(p.identifier, False)

        self.plugins = plugins

    def data_hook(self, hook: str, data: Any):
        """
        Get data from plugins using the specified hook. Allows non-core plugins to request data from each other.
        Each plugin modifies `data` as appropriate.
        """
        for p in self:
            p.on_data_hook(hook, data)
