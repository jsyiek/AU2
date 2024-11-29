from typing import List, Tuple, Union, Any, Callable

from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent


class Export:
    """
    Represents an HTML callback
    """

    def __init__(self, identifier: str, display_name: str, ask, answer,
                 options_functions: Tuple[Callable[
                     [...],
                     Union[
                         List[Union[str, Tuple[str, Any]]],
                         HTMLComponent
                     ]
                 ]] = tuple()):
        """
        Args:
            identifier: internal identifier for the callback
            display_name: html-visible display name
            ask: function that generates a list of HTML components
            answer: function that takes a dictionary of arg -> str and actions the output
            options_functions: tuple of functions each returning either a HTMLComponent or a list of options;
                The functions are executed in the order that they appear in this tuple. If a HTMLComponent is returned,
                this will be rendered, and the result passed as a keyword argument based on the identifier to subsequent
                functions in the tuple as well as the `ask` function.
                If a list is returned then we fall back to rendering a selection from the options in that list, and the
                result is passed as a positional argument to subsequent functions in the tuple as well as the `ask`
                function.

        """
        self.identifier = identifier
        self.display_name = display_name
        self.ask = ask
        self.answer = answer
        self.options_functions = options_functions


DEFAULT_DCE_EXPLANATION = "This config option is dangerous to modify after a game has started."

class ConfigExport(Export):
    """
    Represents a callback for a configuration parameter.
    """

    def __init__(self, identifier: str, display_name: str, ask, answer,
                 explanation: str = DEFAULT_DCE_EXPLANATION):
        """
        Unlike Export, this bans the options function as there are only two stages to Config.

        :param identifier: internal identifier for the callback
        :param display_name: html-visible display name
        :param ask: function that generates a list of HTML components
        :param answer: function that takes a dictionary of arg -> str and actions the output

        """
        self.explanation = explanation
        super().__init__(
            identifier,
            display_name,
            ask,
            answer
        )

class DangerousConfigExport(ConfigExport):
    """
    Represents a config export which shouldn't be changed while a game is in progress
    This is signalled to the user by colouring the option red
    """

class HookedExport:
    """
    Represents an export capable of being hooked into other plugins for their cooperation.
    """

    FIRST = True
    LAST = False

    def __init__(self, plugin_name: str, identifier: str, display_name: str, producer, call_order: bool=FIRST):
        """
        :param plugin_name: name of the plugin (self-explanatory)
        :param identifier: internal identifier for the callback
        :param display_name: html-visible display name
        :param producer: function called that returns an arbitrary data object to be passed to all custom hook requests

        All calls to a custom hook must be handled through `on_request_custom_hook` and `on_custom_hook`.
        `on_custom_hook` will be called with the produced object.

        The hooking plugin will have its `on_custom_hook` function called according to the call_order
        (either first or last).

        The producer function is called with the `htmlResponse` and is always called first.
        """
        self.plugin_name = plugin_name
        self.display_name = display_name
        self.identifier = identifier
        self.producer = producer
        self.call_first = call_order


class AbstractPlugin:
    def __init__(self, identifier: str):
        # unique identifier for the plugin
        self.identifier = identifier
        self.enabled = True
        self.exports: List[Export] = []

        # for config parameters
        self.config_exports: List[ConfigExport] = []

        # for functions that require cross-plugin cooperation
        self.hooked_exports: List[HookedExport] = []

    def _dump_state(self):
        """
        I don't recommend your plugin dumps any state, although some plugins in rare cases
        might want to. State doesn't play well with deleted events!
        :return:
        """
        return

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def process_all_events(self, _: List[Event]) -> List[HTMLComponent]:
        return []

    def on_event_request_create(self) -> List[HTMLComponent]:
        return []

    def on_event_create(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_event_request_update(self, _: Event) -> List[HTMLComponent]:
        return []

    def on_event_update(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_event_request_delete(self, _: Event) -> List[HTMLComponent]:
        return []

    def on_event_delete(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_assassin_request_create(self) -> List[HTMLComponent]:
        return []

    def on_assassin_create(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_assassin_request_update(self, _: Assassin) -> List[HTMLComponent]:
        return []

    def on_assassin_update(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_page_request_generate(self) -> List[HTMLComponent]:
        return []

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_request_hook_respond(self, hook: str) -> List[HTMLComponent]:
        """
        Allows you to respond to hooks from other plugins.

        The `hook` parameter is a string identifier from a function that you can check for and respond to.
        """
        return []

    def on_hook_respond(self, hook: str, htmlResponse, data) -> List[HTMLComponent]:
        """
        Allows you to respond to hooks from other plugins.
        `data` can be anything the hooking function wants you to contribute to
        """
        return []