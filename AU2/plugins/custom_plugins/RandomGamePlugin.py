import datetime
import random
from typing import List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components.IntegerEntry import IntegerEntry
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import COLLEGES, WATER_STATUSES
from AU2.plugins.util import random_data


@registered_plugin
class RandomGamePlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("RandomGame")
        self.exports = [
            Export(
                "RandomGame_randomize_game",
                "Random Game",
                self.ask_random_game,
                self.answer_random_game
            )
        ]
        self.html_ids = {
            "Number Players": self.identifier + "_number_players",
            "Activity": self.identifier + "_activity",
            "Lethality": self.identifier + "_lethality",
            "Weeks": self.identifier + "_weeks"
        }

    def ask_random_game(self):
        return [
            Label(
                "[RANDOM GAME] WARNING: THIS FUNCTION RESETS THE DATABASE IF YOU ANSWER ALL THREE QUESTIONS."
            ),
            IntegerEntry(
                identifier=self.html_ids["Number Players"],
                title="[RANDOM GAME] How many players should we create? (Max 500, and Police aren't supported)",
                default=280
            ),
            Label(
                title="[RANDOM GAME] How many events does a player partake over the course of a six-week game on "
                      "average, assuming they live until the end? (Max 20)"
            ),
            IntegerEntry(
                identifier=self.html_ids["Activity"],
                title="",
                default=5
            ),
            IntegerEntry(
                identifier=self.html_ids["Lethality"],
                title="[RANDOM GAME] What is the percent chance a player kills another when they participate? (1-100)",
                default=20
            ),
            IntegerEntry(
                identifier=self.html_ids["Weeks"],
                title="[RANDOM GAME] How many weeks to simulate? (Max 6. At 6, game winner is declared.)",
                default=6
            )
        ]

    def create_random_assassin(self, available_pseudonyms):
        college = random.choice(COLLEGES)
        pseudonym = random.choice(available_pseudonyms)
        available_pseudonyms.remove(pseudonym)
        first_name = random.choice(random_data.first_names)
        last_name = random.choice(random_data.last_names)
        return Assassin(
            pseudonyms=[pseudonym],
            real_name=f"{first_name} {last_name}",
            pronouns=random.choice(["He/Him", "She/Her", "They/Them"]),
            email=f"{first_name}{last_name}@space_cambridge.ac.uk",
            address=f"Room {random.randint(1, 1000)}, Block {random.randint(1, 1000)}",
            college=college,
            water_status=random.choice(WATER_STATUSES),
            notes="Sample text.",
            is_police=False
        )

    def answer_random_game(self, htmlResponse):
        ASSASSINS_DATABASE.assassins.clear()
        EVENTS_DATABASE.events.clear()
        available_pseudonyms = [p for p in random_data.pseudonyms]

        player_count = htmlResponse[self.html_ids["Number Players"]]
        for _ in range(max(min(player_count, 500), 1)):
            ASSASSINS_DATABASE.add(self.create_random_assassin(available_pseudonyms))

        game_start = datetime.datetime(year=2010, month=8, day=10, hour=0).astimezone(TIMEZONE)

        EVENTS_DATABASE.add(
            Event(
                assassins={},
                datetime=game_start,
                headline="GAME START",
                reports={},
                kills=[],
                pluginState={"PageGeneratorPlugin": {"hidden_event": True}}
            )
        )

        activity_chance = max(min(htmlResponse[self.html_ids["Activity"]], 20), 1) / (6*7)
        lethality_chance = max(min(htmlResponse[self.html_ids["Lethality"]], 100), 1) / 100

        live_assassins = [a for a in ASSASSINS_DATABASE.assassins]

        num_weeks = max(min(htmlResponse[self.html_ids["Weeks"]], 6), 1)

        # to declare winner
        kills = {}

        for day in range(num_weeks*7):
            date_of_event = game_start + datetime.timedelta(days=day, hours=6)
            for assassin_ind in range(len(live_assassins)):

                # this can occur as `live_assassins` is edited during iteration
                if assassin_ind >= len(live_assassins):
                    continue

                if random.random() > activity_chance:
                    continue

                hour = datetime.timedelta(minutes=random.randint(0, 1080))

                # if here, then assassin has been selected for a random event
                # check if they kill
                if random.random() < lethality_chance:
                    num_killers, num_victims = random.choice(list(random_data.death_headlines.keys()))

                    # skip if not enough players for chosen event
                    if num_killers + num_victims > len(live_assassins):
                        continue

                    others = random.sample([a for (j, a) in enumerate(live_assassins) if assassin_ind != j], k=num_killers+num_victims-1)
                    victim_assassins: List[Assassin] = [ASSASSINS_DATABASE.get(a) for a in others[:num_victims]]
                    killer_assassins: List[Assassin] = [ASSASSINS_DATABASE.get(a) for a in ([live_assassins[assassin_ind]] + others[num_victims:])]
                    headline: str = random.choice(random_data.death_headlines[(num_killers, num_victims)])

                    for (i, killer) in enumerate(killer_assassins):
                        headline = headline.replace("{K" + str(i) + "}", f"[P{killer._secret_id}]")

                    for (i, victim) in enumerate(victim_assassins):
                        headline = headline.replace(
                            "{V" + str(i) + "}",
                            f"[D{victim._secret_id}] ([N{victim._secret_id}])")

                    killer_id = killer_assassins[0].identifier
                    kills[killer_id] = kills.get(killer_id, 0) + num_victims

                    EVENTS_DATABASE.add(
                        Event(
                            assassins={a.identifier: 0 for a in victim_assassins + killer_assassins},
                            datetime=date_of_event + hour,
                            headline=headline,
                            reports=[],
                            kills=[
                                (killer_assassins[0].identifier, victim.identifier) for victim in victim_assassins
                            ],
                            pluginState={
                                "CompetencyPlugin": {
                                    "competency": {
                                        killer.identifier: 7 - day % 14 for killer in killer_assassins
                                    }
                                }
                            }
                        )
                    )
                    for victim in victim_assassins:
                        live_assassins.remove(victim.identifier)

                else:
                    num_participants = random.choice(list(random_data.participant_headlines.keys()))

                    if num_participants > len(live_assassins):
                        continue

                    others = random.sample([a for (j, a) in enumerate(live_assassins) if assassin_ind != j], k=num_participants-1)
                    headline: str = random.choice(random_data.participant_headlines[num_participants])

                    participants = [ASSASSINS_DATABASE.get(a) for a in [live_assassins[assassin_ind]] + others]

                    for (i, player) in enumerate(participants):
                        headline = headline.replace("{V" + str(i) + "}", f"[P{player._secret_id}]")

                    EVENTS_DATABASE.add(
                        Event(
                            assassins={a.identifier: 0 for a in participants},
                            datetime=date_of_event + hour,
                            headline=headline,
                            reports=[],
                            kills=[],
                            pluginState={
                                "CompetencyPlugin": {
                                    "competency": {
                                        participants[0].identifier: 7 - (day % 14)
                                    }
                                }
                            }
                        )
                    )


        game_end = game_start + datetime.timedelta(weeks=6)
        if not kills:
            EVENTS_DATABASE.add(
                Event(
                    assassins={},
                    datetime=game_end,
                    headline="No one made any kills, so no one wins!",
                    reports={},
                    kills=[],
                    pluginState={}
                )
            )
        else:
            winner = max(list(kills.keys()), key=lambda k: kills[k])
            winner_id = ASSASSINS_DATABASE.get(winner)._secret_id
            EVENTS_DATABASE.add(
                Event(
                    assassins={winner: 0},
                    datetime=game_end,
                    headline=f"And the winner is... [D{winner_id}] ([N{winner_id}]), with {kills[winner]} kills!",
                    reports={},
                    kills=[],
                    pluginState={}
                )
            )

        return [Label("[RANDOM GAME] Success!")]






