import os
from dataclasses import dataclass

from dataclasses_json import dataclass_json

from AU2.plugins import CONFIG_WRITE_LOCATION
from AU2.plugins.AbstractPlugin import AbstractPlugin


@dataclass_json
@dataclass
class Config:
    # map from plugin name to plugin string and whether it's enabled
    plugins: dict[str, bool]

    @classmethod
    def load_json(cls, location: str):
        if os.path.exists(location):
            with open(location, "r") as F:
                config = F.read()
            return cls.from_json(config)
        return Config({})


ENABLED_PLUGINS = Config.load_json(CONFIG_WRITE_LOCATION)


class __PluginMap:
    """
    Stores the plugins that are available
    Most conveniently accessed as an iteration.
    """

    def __init__(self, plugins):

        for (name, plugin) in plugins.items():
            enabled = ENABLED_PLUGINS.plugins.get(name, True)
            if not enabled:
                del plugins[name]
                continue
            # when we add new plugins, update config to default to enabled
            ENABLED_PLUGINS.plugins[name] = True

        self.plugins: dict[str, AbstractPlugin] = plugins

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
        return self.plugins[item]
