from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from AU2.database.model import Event, Assassin
from AU2.html_components.HTMLComponent import HTMLComponent, HTMLResponse

AskFunction = Callable[[...], Sequence[HTMLComponent]]
AnswerFunction = Callable[[HTMLResponse], Sequence[HTMLComponent]]

class Export:
    """
    Represents an HTML callback
    """

    def __init__(self, identifier: str, display_name: str,
                 ask: AskFunction, answer: Union[AnswerFunction, Sequence[AnswerFunction]],
                 options_functions: Sequence[Callable[[...], Union[List[Union[str, Tuple[str, Any]]]]
                 ]] = tuple()):
        """
        Args:
            identifier: internal identifier for the callback
            display_name: html-visible display name
            ask: function that generate a list of HTML components. The function takes the outputs of the options_functions
                as positional arguments, in the order that these functions are specified in options_functions, and
                outputs a sequence of HTMLComponents to be rendered.
            answer: either a single or sequence of AnswerFunctions: functions that take the response dict from rendering a
                sequence of HTMLComponents and output a sequence of HTMLComponents to render. In the single function
                case, the output from rendering the HTMLComponents produced by the `ask` function is used as input.
                In the multiple function case, the first of the answer functions gets this as input, and the subsequent
                ones get the output of rendering the components produced by the previous one in the sequence.
                Only the last of these should have side-effects as it is possible to abort / go back at any prior stage,
                and this last answer function should hence only return non-interactive components.
                (Note: the reason for allowing a single function *or* a sequence is that the old plugin API only
                allowed for a single answer function, and keeping this possibility avoids having to change every single
                export definition)

            options_functions: tuple of functions each returning a list of options; these options can either be strings
                or tuples of (display string, option value). The functions are executed in the order that they appear in
                the tuple, with the selected value for all previous lists being passed as positional arguments of
                subsequent functions, as well as the first `ask` function.

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
    def __init__(self, identifier: str, display_name: str, ask, answer):
        """
        Unlike Export, this bans the options_functions.
        """
        super().__init__(
            identifier,
            display_name,
            ask,
            answer
        )

class DangerousConfigExport(ConfigExport):
    """
    Represents a config export which shouldn't be changed while a game is in progress
    This is signalled to the user by colouring the option red.
    `explanation' gives a string to be displayed to the user when they try to access the config export by way of
    explanation for why they should be careful changing the value.
    For the rest of the arguments, see ConfigExport.
    """
    def __init__(self, *args, explanation: str = DEFAULT_DCE_EXPLANATION, **kwargs):
        self.explanation = explanation
        super().__init__(*args, **kwargs)


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


AttributePairTableRow = Tuple[str, str]

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

    def on_gather_assassin_pseudonym_pairs(self, _: Optional[Event]) -> List[HTMLComponent]:
        return []

    def on_event_request_create(self, assassin_pseudonyms: Dict[str, int]) -> List[HTMLComponent]:
        return []

    def on_event_create(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_event_request_update(self, _: Event, assassin_pseudonyms: Dict[str, int]) -> List[HTMLComponent]:
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

    def on_request_assassin_summary(self) -> List[HTMLComponent]:
        return []

    def on_request_event_summary(self) -> List[HTMLComponent]:
        return []

    def render_assassin_summary(self, _: Assassin) -> List[AttributePairTableRow]:
        """
        Display any information about an ASSASSIN that is managed by this plugin
        """
        return []

    def render_event_summary(self, _: Event) -> List[AttributePairTableRow]:
        """
        Display any information about an EVENT that is managed by this plugin
        """
        return []
