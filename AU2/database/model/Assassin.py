import datetime as dt

from dataclasses_json import dataclass_json, config
from typing import List, Dict, Any, Optional, Iterator, Union

from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model.PersistentFile import PersistentFile
from dataclasses import dataclass, field

from AU2 import TIMEZONE
from AU2.plugins.util.date_utils import get_now_dt


@dataclass_json
@dataclass
class Assassin(PersistentFile):
    """ Class for keeping track of an assassin """
    pseudonyms: List[str]
    real_name: str
    pronouns: str
    email: str
    address: str
    water_status: str
    college: str
    notes: str
    is_police: bool
    # almost everything that is stateful is probably best placed in an event
    # but for a few plugins, it might make sense to place the information directly onto the assassin
    # make sure you know what you're doing (modifications here can't be undone with a later event state change)
    plugin_state: Dict[str, Any] = field(default_factory=dict)
    identifier: str = ""   # human-readable unique identifier
    _secret_id: str = ""  # unique identifier

    # store a timestamp along with each pseudonym,
    # so that anachronous pseudonyms aren't rendered when rendering [DX]
    # the mapping is stored as a Dict for compatibility with old save files
    # any non-timestamped pseudonym should be assumed to have existed "forever".
    pseudonym_datetimes: Dict[int, dt.datetime] = field(
        default_factory=dict,
        metadata=config(
            encoder=lambda d: {k: ts.timestamp() for k,ts in d.items()},
            decoder=lambda d: {int(k): dt.datetime.fromtimestamp(ts).astimezone().astimezone(TIMEZONE) for k,ts in d.items()}
        )
    )

    def __post_init__(self):
        if len(self.pseudonyms) == 0:
            raise ValueError(f"Tried to initialize {self}, but no pseudonyms were provided!")
        if not self._secret_id:
            self._secret_id = GENERIC_STATE_DATABASE.get_unique_str()

        if self.TEST_MODE:
            self.identifier = f"{self.real_name} identifier"
            return

        # Don't move this out of __post_init__
        if not self.identifier:
            dotdotdot = "..." if len(self.pseudonyms[0]) > 15 else ""
            self.identifier = f"{self.real_name} ({self.pseudonyms[0][:15]}{dotdotdot}) ID: {self._secret_id}"

    def get_pseudonym(self, i: int) -> str:
        """
        Fetches the pseudonym of this assassin corresponding to a given index,
        with the first non-deleted pseudonym given as a fallback value if the index does not point to an extant
        pseudonym (pseudonyms set to "" are considered to have been deleted).

        Args:
            i: the index of the pseudonym to get.

        Returns:
             the i-th pseudonym of this assassin, if it exists, otherwise the first pseudonym of this assassin that has
                not been deleted.
        """
        # We "delete" pseudonyms by setting them to "",
        # in order to preserve the correspondence between index and pseudonym.
        # In the case that a deleted pseudonym is requested,
        # fall back to the first pseudonym that hasn't been deleted.
        # (This *should* always be the initial pseudonym,
        # since `delete_pseudonym` throws an error if you try to delete the initial pseudonym).
        if i >= len(self.pseudonyms) or not self.pseudonyms[i]:
            return next((p for p in self.pseudonyms if p))

        return self.pseudonyms[i]

    def get_pseudonym_validity(self, i: int) -> Union[dt.datetime, None]:
        """
        Fetches the start of validity for a given pseudonym, referenced by index.
        The start of validity is notionally the point in time in the game when the assassin was granted the pseudonym,
        which may differ from when the pseudonym was physically entered into AutoUmpire.
        The start of validity may be `None`, which represents that the pseudonym is always valid.

        Args:
            i: the index of the pseudonym to get the validity of.

        Returns:
            `None` if the relevant pseudonym is always valid, otherwise a `datetime.datetime` object representing when
            this assassin was granted the pseudonym.
        """
        return self.pseudonym_datetimes[i] if i in self.pseudonym_datetimes else None

    def add_pseudonym(self, val: str, valid_from: Union[dt.datetime, None] = get_now_dt()) -> int:
        """
        Adds a new pseudonym to this assassin.

        Args:
            val: text of new pseudonym
            valid_from: start of validity of new pseudonym.
                Defaults to the current datetime.
                May be explicitly set to `None` to indicate that the pseudonym is always valid.

        Return: index of the newly-added pseudonym.
        """
        new_i = len(self.pseudonyms)
        if isinstance(valid_from, dt.datetime):
            self.pseudonym_datetimes[new_i] = valid_from
        elif valid_from is not None:
            raise TypeError("add_pseudonym expects a datetime.datetime object or None in the second argument")
        self.pseudonyms.append(val)
        return new_i

    def edit_pseudonym(self, i: int, new_val: str, new_valid_from: Union[dt.datetime, None]):
        """
        Edits a pseudonym, referenced by index, from this assassin.
        Both the new text and new start of validity must be specified.
        (This is to avoid confusion between using `None` as a placeholder default value, and `None` representing an
        always-valid pseudonym).

        Args:
            i: the index of the pseudonym to edit.
            new_val: the new text of the pseudonym.
            new_valid_from: the new start of validity of the pseudonym; may be explicitly set to `None` to indicate the
                pseudonym should always be valid.
        """
        if new_val.strip() == "":
            raise ValueError("Cannot set a blank pseudonym.")

        if new_valid_from is not None:
            if i == 0:
                raise ValueError("Cannot set a validity for the initial pseudonym.")
            else:
                self.pseudonym_datetimes[i] = new_valid_from
        # a validity of `None`, which represents the pseudonym being valid forever
        elif i in self.pseudonym_datetimes:
            del self.pseudonym_datetimes[i]

        self.pseudonyms[i] = new_val

    def delete_pseudonym(self, i: int):
        """
        Deletes a pseudonym, referenced by index, from this assassin.
        Internally, the pseudonym is set to "" so that the indices of other pseudonyms are unchanged.
        The initial pseudonym (i=0) cannot be deleted.

        Args:
            i: the index of the pseudonym to delete.
        """
        if i == 0:
            raise ValueError("Cannot delete initial pseudonym.")

        self.pseudonyms[i] = ""
        if i in self.pseudonym_datetimes:
            del self.pseudonym_datetimes[i]

    def pseudonyms_until(self, ts: dt.datetime = get_now_dt()) -> Iterator[str]:
        """
        A generator yielding all the assassin's pseudonyms valid at a given datetime.
        Pseudonyms with no datetime set are considered always valid.

        Args:
            ts: the datetime at which we want the returned pseudonyms to be valid.
                Defaults to the current datetime.

        Yields:
            the next pseudonym of the assassin that is valid before datetime `ts`.
        """
        for (i, p) in enumerate(self.pseudonyms):
            if p and self.pseudonym_datetimes.get(i, ts) <= ts:
                yield p

    def all_pseudonyms(self) -> str:
        return " AKA ".join(self.pseudonyms)
