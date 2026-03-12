from typing import Any, Callable, Generator, List, NamedTuple, Optional, Tuple, Type, TypeVar, Union

from AU2.database.model import Assassin, Event
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.html_components import HTMLComponent
from AU2.plugins.util.navbar import NavbarEntry

ColorFnGenerator = Generator[Callable[[Assassin, str], Optional[Tuple[float, str]]], Event, None]

T = TypeVar("T")

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

    def __init__(self, identifier: str, display_name: str, ask, answer):
        """
        Unlike Export, this bans the options function as there are only two stages to Config.

        :param identifier: internal identifier for the callback
        :param display_name: html-visible display name
        :param ask: function that generates a list of HTML components
        :param answer: function that takes a dictionary of arg -> str and actions the output

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
    This is signalled to the user by colouring the option red
    """
    def __init__(self, identifier: str, display_name: str, ask, answer,
                 danger_explanation: Callable[[], str] = lambda: DEFAULT_DCE_EXPLANATION):
        self.danger_explanation = danger_explanation
        super().__init__(identifier, display_name, ask, answer)




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

    @property
    def enabled(self) -> bool:
        return GENERIC_STATE_DATABASE.plugin_map.get(self.identifier, True)

    @enabled.setter
    def enabled(self, val: bool):
        if not isinstance(val, bool):
            raise TypeError(f"{self.__class__.__name__}.enabled must be a boolean, not '{type(val)}'")
        GENERIC_STATE_DATABASE.plugin_map[self.identifier] = val

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

    def on_page_generate(self, html_response: dict, navbar_entries: List[NavbarEntry]) -> List[HTMLComponent]:
        """
        Called by the answer function of `Generate Pages`

        Args:
            html_response (dict): response data from the components produced by the ask function of `Generate Pages`,
                in particular including those produced by `on_page_request_generate`.
            navbar_entries (list[NavbarEntries]): a list for plugins to append NavbarEntry namedtuples to so that they
                can be rendered into a HTML list for inclusion into header.html. Each NavbarEntry specifies a url,
                display text, and position. The position is a float value and the entries are rendered from top to
                bottom in *ascending* order of position. For reference, the positions of the pages generated by the
                various plugins are:

                -2: May week player list
                -1: Bounties (either plugin)
                0: City Watch
                1: Wanted
                2: Incos
                3: Open Season
                4: Stats
        """
        return []

    def colour_fn_generator(self) -> ColorFnGenerator:
        """
        Allows plugins to affect the colouring of assassin pseudonyms.
        For reference, the priority values for each situation are:
            6: wanted (with different colours for city watch and full players)
            5: dead city watch (only when CityWatchPlugin enabled)
            4: dead
            3: inco
            2: hardcoded pseudonym-based colours
            1.5: teams (only when MayWeekUtilitiesPlugin enabled)
            1: city watch (only when CityWatchPlugin enabled)

        Yields:
            Callable[[Assassin, int], Optional[Tuple[float, str]]]: A function taking an assassin model and pseudonym
                as input and returning either
                    - a tuple of a float-valued priority and colour hexcode, or
                    - `None` to ignore this plugin.

        Receives:
            Event: events are sent to the generator in chronological order
        """
        while True:
            yield lambda a, p: None

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

    def on_data_hook(self, hook: str, data):
        """
        Allows plugins to request data from each other.
        `data` can be anything the hooking function wants you to contribute to
        """

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

    def on_request_setup_game(self, game_type: str) -> List[HTMLComponent]:
        """
        Walk through config options. Generally this method should call the `ask` functions of important
        `ConfigExport`s of this plugin and return the results concatenated together.
        Make sure that all the components have unique identifiers.
        """
        return []

    def on_setup_game(self, htmlResponse) -> List[HTMLComponent]:
        """
        Effect config options. Generally this method should call the `answer` functions of the same `ConfigExport`s
        called by `on_request_setup_game` above, passing `htmlResponse` to each, then returning the results concatenated
        together.
        """
        return []

    def assassin_property(self, identifier: str, default: T, store_default: bool = True) -> property:
        """
        Creates a property corresponding to a value stored in the plugin_state of an assassin.

        Args:
            identifier (str): identifier under which to store the property
            default: the default value of the property
            store_default (bool): whether to store the default value in the database. Necessary for mutable default
                values.
        Returns:
            property: a property whose getter and setter functions read and write from Assassin.plugin_state.
                Needs to be assigned to a CLASS attribute of Assassin to work!
        """

        if store_default:
            def getter(assassin: Assassin) -> T:
                return assassin.plugin_state.setdefault(self.identifier, {}).setdefault(identifier, default)
        else:
            def getter(assassin: Assassin) -> T:
                return assassin.plugin_state.get(self.identifier, {}).get(identifier, default)

        def setter(assassin: Assassin, val: T):
            assassin.plugin_state.setdefault(self.identifier, {})[identifier] = val

        return property(getter, setter)
