from dataclasses import dataclass
from typing import Dict, Tuple

from dataclasses_json import dataclass_json

from AU2.plugins import CONFIG_WRITE_LOCATION
from AU2.plugins.AbstractPlugin import AbstractPlugin


@dataclass_json
@dataclass
class Config:
    # map from plugin name to plugin string and whether it's enabled
    plugins: Dict[str, Tuple[str, bool]]


class __PluginMap:
    """
    Stores the plugins that are available
    Most conveniently accessed as an iteration.
    """

    def __init__(self, plugins):
        self.plugins: Dict[str, AbstractPlugin] = plugins

    def __iter__(self):
        """
        You can access plugins using syntax such as `for plugin in pluginMap`
        """
        yield from self.plugins.values()

    def __getitem__(self, item: str):
        """
        If there is a particular plugin you want and you know the ID, you can do
        `pluginMap["police"]`
        """
        return self.plugins[item.lower()]


__config = Config.load_json(CONFIG_WRITE_LOCATION)
__plugin_dict = {}
for (identifier, (path, enabled)) in __config.plugins:
    __plugin_dict[identifier.lower()] = __import__(path).EXPORT_PLUGIN
    if enabled:
        __plugin_dict[identifier.lower()].enable()
    else:
        __plugin_dict[identifier.lower()].disable()

PLUGINS = __PluginMap(__plugin_dict)
