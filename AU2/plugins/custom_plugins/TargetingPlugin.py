import itertools
import random
from typing import Tuple, Dict, List, Set

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.IntegerEntry import IntegerEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, DangerousConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.custom_plugins.SRCFPlugin import Email

EMAIL_TARGETS_TEMPLATE = """\
Your targets are:

{TARGET1}

{TARGET2}

{TARGET3}
"""

EMAIL_SINGLE_TARGET_TEMPLATE = """\
Name: {NAME}
College: {COLLEGE}
Address: {ADDRESS}
Water Weapons Status: {WATER_STATUS}
Notes: {NOTES}"""


class FailedToCreateChainException(Exception):
    pass


@registered_plugin
class TargetingPlugin(AbstractPlugin):
    """
    Are YOU considering editing the TargetingPlugin in the middle of the game?
    Don't.
    Just don't.
    Do it between games.
    """

    def __init__(self):
        super().__init__("TargetingPlugin")
        self.exports = [
            Export(
                "targeting_print_targeting_graph",
                "Targeting Graph -> Print",
                lambda *args: [],
                self.answer_show_targeting_graph
            )
        ]

        self.config_exports = [
            DangerousConfigExport(
                "targeting_set_player_seeds",
                "Targeting Graph -> Set player seeds",
                self.ask_set_seeds,
                self.answer_set_seeds
            ),
            DangerousConfigExport(
                "targeting_set_random_seed",
                "Targeting Graph -> Set random seed",
                self.ask_set_random_seed,
                self.answer_set_random_seed
            )
        ]

        self.html_ids = {
            "Seeds": self.identifier + "_seeds",
            "Random Seed": self.identifier + "_random_seed"
        }

    def on_hook_respond(self, hook: str, htmlResponse, data) -> List[HTMLComponent]:
        if hook == "SRCFPlugin_email":
            # if graph computation time becomes an issue, we could yield the `last_graph` and then compute
            # current_graph without needing to recompute
            response = []
            last_emailed_event = int(
                GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).setdefault("last_emailed_event", -1))
            last_graph = self.compute_targets(response, max_event=last_emailed_event)
            current_graph = self.compute_targets(response)

            if not current_graph:
                return []

            email_list: List[Email] = data
            for email in email_list:
                assassin = email.recipient
                target_strs = []
                if assassin.identifier not in current_graph:
                    continue
                for target_identifier in current_graph[assassin.identifier]:
                    target_assassin = ASSASSINS_DATABASE.assassins[target_identifier]
                    target_strs.append(
                        EMAIL_SINGLE_TARGET_TEMPLATE.format(
                            NAME=target_assassin.real_name,
                            COLLEGE=target_assassin.college,
                            ADDRESS=target_assassin.address,
                            WATER_STATUS=target_assassin.water_status,
                            NOTES=target_assassin.notes
                        )
                    )

                email_content = EMAIL_TARGETS_TEMPLATE.format(
                    TARGET1=target_strs[0],
                    TARGET2=target_strs[1],
                    TARGET3=target_strs[2]
                )

                # only send email if targets for this user have changed
                targets_changed = any(
                    a not in current_graph[assassin.identifier] for a in last_graph[assassin.identifier])
                targets_changed |= len(current_graph[assassin.identifier]) != len(last_graph[assassin.identifier])
                targets_changed |= last_emailed_event == -1  # we haven't emailed anything yet

                email.add_content(
                    plugin_name="TargetingPlugin",
                    content=email_content,
                    require_send=targets_changed
                )

            if EVENTS_DATABASE.events:
                max_event: Event = max((e for e in EVENTS_DATABASE.events.values()), key=lambda e: e._Event__secret_id)
                GENERIC_STATE_DATABASE.arb_state[self.identifier]["last_emailed_event"] = max_event._Event__secret_id
            return response
        return []

    def ask_set_seeds(self):
        return [
            SelectorList(
                identifier=self.html_ids["Seeds"],
                title="Choose which assassins should be seeded",
                options=sorted(list(ASSASSINS_DATABASE.assassins)),
                defaults=GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get("seeds", [])
            )
        ]

    def answer_set_seeds(self, htmlResponse):
        seeds = htmlResponse[self.html_ids["Seeds"]]
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})["seeds"] = seeds
        return [Label("[TARGETING] Success!")]

    def ask_set_random_seed(self):
        return [
            IntegerEntry(
                identifier=self.html_ids["Random Seed"],
                title="Enter new random seed",
                default=self.seed
            )
        ]

    def answer_set_random_seed(self, htmlResponse):
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})["random_seed"] = htmlResponse[
            self.html_ids["Random Seed"]]
        return [Label(f"[TARGETING] Set random seed to: {self.seed}")]

    def answer_show_targeting_graph(self, _):
        response = []
        graph = self.compute_targets(response)
        for (attacker, targets) in graph.items():
            response.append(Label(attacker))
            response.append(Label(f"|________ {targets[0]}"))
            response.append(Label(f"|________ {targets[1]}"))
            response.append(Label(f"|________ {targets[2]}"))
            response.append(Label(""))

        if graph:
            response.append(Label(f"Total alive players: {len(graph.keys())}"))
        return response

    @property
    def seed(self):
        return GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).setdefault("random_seed", 28082024)

    def compute_targets(self, response, max_event=100000000000000000):
        """
        Deterministically computes the targeting graph given current events.

        IMPORTANT: If you ever think about editing this function, don't.
                   If you still want to, make sure any change you make is
                   DETERMINISTIC with respect to the initial seed.

        UNDER NO CIRCUMSTANCES SHOULD YOU CHANGE THIS FUNCTION IN THE MIDDLE
        OF THE GAME WITHOUT RISK OF SEVERE CONSEQUENCES.
        """

        # reset the seed for determinism
        random.seed(self.seed)

        # collect all targetable assassins
        players = [a for (a, model) in ASSASSINS_DATABASE.assassins.items() if not model.is_police]

        # Targeting graphs with 7 or less players are non-trivial to generate random graphs for, and don't
        # last long anyway.
        if len(players) <= 7:
            response.append(Label("[TARGETING] Refusing to generate a targeting graph (too few non-police assassins)."))
            return {}

        # FIRST STEP, get initial targets
        # we use a hash set to cache combinations disallowed in subsequent chains.
        # (i.e., a targets b in chain one means a cannot target b and b cannot target a in chain two)
        claimed_combos = set()

        # We must respect any seeding constraints.
        player_seeds = [p for p in GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get("seeds", [])]

        def seed_shuffle(chain):
            if not player_seeds:
                random.shuffle(chain)
                return chain

            chain_no_seeds = [p for p in chain if p not in player_seeds]

            if not chain_no_seeds:
                random.shuffle(player_seeds)
                return player_seeds

            random.shuffle(chain_no_seeds)
            random.shuffle(player_seeds)

            output = []
            increase_factor = len(chain_no_seeds) / len(player_seeds)
            player_seeds_pointer = 0
            chain_no_seeds_pointer = 0
            balance = 0
            while chain_no_seeds_pointer < len(chain_no_seeds) and player_seeds_pointer < len(player_seeds):
                if balance > 0:
                    output.append(chain_no_seeds[chain_no_seeds_pointer])
                    chain_no_seeds_pointer += 1
                    balance -= 1
                elif balance <= 0:
                    output.append(player_seeds[player_seeds_pointer])
                    balance += increase_factor
                    player_seeds_pointer += 1
            return output + chain_no_seeds[chain_no_seeds_pointer:] + player_seeds[player_seeds_pointer:]

        def new_unique_chain(abort_after=1000):
            chain = [p for p in players]
            chain = seed_shuffle(chain)
            tries = 0
            last_chain = chain
            while any((a, b) in claimed_combos or (b, a) in claimed_combos
                      for (a, b) in zip(chain, chain[1:] + [chain[0]])):
                if tries >= abort_after:
                    raise FailedToCreateChainException()
                chain = seed_shuffle(chain)
                tries += 1

            for (a, b) in zip(chain, chain[1:] + [chain[0]]):
                claimed_combos.add((a, b))
                claimed_combos.add((b, a))

            return chain

        while True:
            try:
                chain_one = new_unique_chain()
                chain_two = new_unique_chain()
                chain_three = new_unique_chain()
                break
            except FailedToCreateChainException:
                # edge case where chain one and two create an impossibility result for chain three to exist
                # occurs commonly at lower numbers
                claimed_combos = set()

        # who the player P is targeting
        targeting_graph = {P: [] for P in players}

        # who targets player P
        targeters_graph = {P: [] for P in players}

        for c in [chain_one, chain_two, chain_three]:
            for (targeter, targetee) in zip(c, c[1:] + [c[0]]):
                targeting_graph[targeter].append(targetee)
                targeters_graph[targetee].append(targeter)

        # counter to what might seem intuitive, events must be sorted by secret ID and not when they occurred in game
        # secret ID is monotonically increasing in order of events being added and can't be changed by the user
        # (but event datetime isn't)
        # using secret ID means users can't screw with the determinacy
        events = [e_model for e_model in EVENTS_DATABASE.events.values()]
        events.sort(key=lambda e: e._Event__secret_id)

        # NO USE OF RANDOM AFTER THIS POINT WITHOUT RE-SEEDING (random.seed).
        player_seeds_set = set(player_seeds)

        for e in events:
            if int(e._Event__secret_id) > max_event:
                break

            deaths = [victim for (_, victim) in e.kills]

            # filter out police
            deaths = [d for d in deaths if not ASSASSINS_DATABASE.get(d).is_police]
            if not deaths:
                continue

            # try to fix with triangle elimination
            # this function has side effects
            success = self.update_graph(response, targeting_graph, targeters_graph, deaths, player_seeds_set)
            if success:
                continue

            success = self.update_graph(
                response,
                targeting_graph,
                targeters_graph,
                deaths,
                player_seeds_set,
                allow_mutual_seed_targets=True
            )

            if success:
                response.append(
                    Label("[TARGETING] WARNING: Seeding has been violated due to an unavoidable graph collapse."))
                continue

            success = self.update_graph(
                response,
                targeting_graph,
                targeters_graph,
                deaths,
                player_seeds_set,
                allow_mutual_seed_targets=True,
                allow_mutual_targets=True
            )

            if success:
                response.append(
                    Label("[TARGETING] WARNING: Two assassins target each other due to an unavoidable graph collapse."))
                continue

            response.append(
                Label("[TARGETING] CRITICAL: The targeting graph 3-targets 3-targeting invariant cannot be maintained."
                      " Targeting has been ABORTED. IT IS TIME TO BEGIN OPEN SEASON."))
            return {}

        return targeting_graph

    def update_graph(
            self,
            response: List[Label],
            targeting_graph: Dict[str, List[str]],
            targeters_graph: Dict[str, List[str]],
            deaths: List[str],
            player_seeds: Set[str],
            allow_mutual_seed_targets: bool = False,
            allow_mutual_targets: bool = False,
            limit_checks=1000000
    ) -> bool:
        """
        Updates the targeting graph given a list of deaths.

        The problem is constraint satisfaction so a Prolog-style "generate-and-test" is sufficient.
        """

        deaths_adj = list(set([d for d in deaths if d in targeting_graph]))
        visited = []
        for d in deaths:
            if d not in deaths_adj or d in visited:
                response.append(
                    Label(f"WARNING: {d} has been killed more than once. Skipping this player when updating graph..."))
            visited.append(d)

        deaths = deaths_adj

        # collect a list of [non-unique] players who need new targets
        targeters = sum((targeters_graph[d] for d in deaths), start=[])
        targeters = [t for t in targeters if t not in deaths]

        # collect a list of [non-unique]
        targeting = sum((targeting_graph[d] for d in deaths), start=[])
        targeting = [t for t in targeting if t not in deaths]

        # we assume as a precondition the "3-targeters, 3-targeting" invariant.
        # this guarantees len(targeters) == len(targeting)
        assert (len(targeters) == len(targeting))

        # to generate-and-test all matchings, we can permute one list and zip it with the second
        new_targets: List[Tuple[str, str]]
        checks = 0
        for targeters_permutation in itertools.permutations(targeters):
            # events with a huge number of deaths can be spiral badly in extremely rare edge cases
            # thanks to the factorial function, so I've put in a check to abort instead of stalling
            if checks > limit_checks:
                response.append(Label(
                    "[TARGETING] WARNING: Aborted search check due to excessive depth. This can happen if you added "
                    "many deaths in one event, and only exists as a safety check to avoid the app stalling."))
                return False
            checks += 1

            # list of [(targeter, targeted), (a, b), ...]
            new_targets = list(zip(targeters_permutation, targeting))

            # Constraint 0: no one can get a target they already have
            if any(b in targeting_graph[a] for (a, b) in new_targets):
                continue

            # Constraint 1: no one targets themselves
            if any(a == b for (a, b) in new_targets):
                continue

            # Constraint 2: no one targets anyone who ALREADY targets them
            # Ignore conditions: allow_mutual_targets=True
            if not allow_mutual_targets and any(b in targeters_graph[a] for (a, b) in new_targets):
                continue

            # Constraint 3: no mutual targets are being created
            # Ignore conditions: allow_mutual_targets=True
            if not allow_mutual_targets:
                observed_target_pairs = set()
                any_clashes = False
                for (a, b) in new_targets:
                    if (b, a) in observed_target_pairs:
                        any_clashes = True
                        break
                    observed_target_pairs.add((a, b))
                if any_clashes:
                    continue

            # Constraint 4: no triangles are formed
            # (a triangle is any targeting of players (eg) Vendetta, OHare, and O-Ren Ishii such that
            # Vendetta targets OHare targets O-Ren Ishii targets Vendetta
            # V -> OH -> OR -> V)
            # Ignore conditions: allow_mutual_targets=True
            if not allow_mutual_targets:
                # precondition: assume triangle elimination has been performed up to this point.
                # While triangle elimination originated with the previous AU, Peter has a good description of it:
                # "only check the targets of the newly assigned targets' targets,
                # and check for matches with their respective targetters"
                # Which is a mouthful but makes sense if you draw yourself a diagram like this:
                #          ____> p3
                # A --> B |----> p2
                #         |____> p1
                # To eliminate triangles, we require that p1, p2, and p3 don't target A
                any_clashes = False
                for (a, b) in new_targets:
                    if any(a in targeting_graph[p] for p in targeting_graph[b]):
                        any_clashes = True
                        break
                if any_clashes:
                    continue

            # Constraint 5: limit mutual seed targeting
            # ideally, we try to avoid two seeds targeting each other
            if not allow_mutual_seed_targets:
                any_clashes = False
                for (a, b) in new_targets:
                    if a in player_seeds and b in player_seeds:
                        any_clashes = True
                        break
                if any_clashes:
                    continue

            # If we reach here without being forced to `continue`, update the graph and return True
            for t in targeters:
                targeting_graph[t] = [targ for targ in targeting_graph[t] if targ not in deaths]

            for d in deaths:
                for targ in targeting_graph[d]:
                    if targ in deaths:
                        continue
                    targeters_graph[targ].remove(d)
                del targeters_graph[d]
                del targeting_graph[d]

            for (new_targeter, new_target) in new_targets:
                targeting_graph[new_targeter].append(new_target)
                targeters_graph[new_target].append(new_targeter)

            return True
        return False
