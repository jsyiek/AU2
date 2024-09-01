import datetime

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
