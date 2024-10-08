import datetime
from html import escape

from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE


def get_game_start() -> datetime.datetime:
    """
    Returns the start of the game.
    """
    return datetime.datetime.fromtimestamp(GENERIC_STATE_DATABASE.arb_state.setdefault("game_start", datetime.datetime.now().timestamp()))


def set_game_start(date: datetime.datetime):
    """
    Sets the start of the game
    """
    GENERIC_STATE_DATABASE.arb_state["game_start"] = date


def soft_escape(string: str) -> str:
    """
    Escapes only if not prefixed by <!--HTML-->
    """

    # umpires may regret allowing this
    # supposing you are a clever player who has found this and the umpire does not know...
    # please spare the umpire any headaches
    # and remember that code injection without explicit consent is illegal (CMA sxn 2/3)
    if not string.startswith("<!--HTML-->"):
        return escape(string)
    return string