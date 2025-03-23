import datetime
from html import escape
from typing import Optional

from AU2 import TIMEZONE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.plugins.util.date_utils import get_now_dt


HTML_REPORT_PREFIX = "<!--HTML-->"


def get_game_start() -> datetime.datetime:
    """
    Returns the start of the game.
    """
    return datetime.datetime.fromtimestamp(
        GENERIC_STATE_DATABASE.arb_state.setdefault(
            "game_start", get_now_dt().timestamp()
        )
    ).astimezone(TIMEZONE)


def set_game_start(date: datetime.datetime):
    """
    Sets the start of the game
    """
    GENERIC_STATE_DATABASE.arb_state["game_start"] = date.timestamp()


def get_game_end() -> Optional[datetime.datetime]:
    """
    Returns the end of the game, or `None` if the end of the game hasn't been set.
    """
    ts = GENERIC_STATE_DATABASE.arb_state.get("game_end", None)
    return datetime.datetime.fromtimestamp(ts).astimezone(TIMEZONE) if ts else None


def set_game_end(date: Optional[datetime.datetime]):
    """
    Sets the end of the game
    """
    GENERIC_STATE_DATABASE.arb_state["game_end"] = date.timestamp() if date else None


def soft_escape(string: str) -> str:
    """
    Escapes html and adds <br /> to newlines only if not prefixed by HTML_REPORT_PREFIX
    """

    # umpires may regret allowing this
    # supposing you are a clever player who has found this and the umpire does not know...
    # please spare the umpire any headaches
    # and remember that code injection without explicit consent is illegal (CMA sxn 2/3)
    if not string.startswith(HTML_REPORT_PREFIX):
        return escape(string).replace("\n", "<br />\n")
    return string


def escape_format_braces(string: str) -> str:
    """
    Escapes { and } in a string so that they will be processed correctly by .format
    This needs to be called on user-input strings passed as part of the message of any inquirer prompt,
    or as part of the default of inquirer Text prompts (but not the choices or defaults of List of Checkbox prompts)

    Args:
        string: the string to escape occurrences of `{` and `}` in.

    Returns:
        `string` with all occurrences of `{` and `}` doubled.

    Examples:
        >>> escape_format_braces(":} :{")
        ":}} :{{"
    """
    return string.replace("{", "{{").replace("}", "}}")
