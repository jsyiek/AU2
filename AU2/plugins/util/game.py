import datetime

from AU2 import TIMEZONE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.plugins.util.date_utils import get_now_dt


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
