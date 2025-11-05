from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.plugins.AbstractPlugin import AbstractPlugin


class __PluginMap:
    """
    Stores the plugins that are available
    Most conveniently accessed as an iteration.
    """

    def __init__(self, plugins):

        # I refuse to allow users to disable the CorePlugin... because then the entire app would break
        GENERIC_STATE_DATABASE.plugin_map["CorePlugin"] = True

        for p in plugins.values():
            GENERIC_STATE_DATABASE.plugin_map.setdefault(p.identifier, False)

        self.plugins: dict[str, AbstractPlugin] = plugins

    def __iter__(self):
        """
        You can access plugins using syntax such as `for plugin in pluginMap`
        """
        yield from [p for p in self.plugins.values() if p.enabled]

    def __getitem__(self, item: str):
        """
        If there is a particular plugin you want and you know the ID, you can do
        `pluginMap["police"]`
        """
        return self.plugins[item]
