import itertools
import random
from typing import Tuple, Dict, List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin


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
                "TargetingPlugin",
                "Targeting Graph -> Print",
                lambda *args: [],
                self.answer_show_targeting_graph
            )
        ]

        # TODO: Config parameter: RANDOM LIBRARY'S SEED
        self.seed = 28082024

    def answer_show_targeting_graph(self, _):
        graph = self.compute_targets()
        for (attacker, targets) in graph.items():
            print(attacker)
            print(f"|________ {targets[0]}")
            print(f"|________ {targets[1]}")
            print(f"|________ {targets[2]}")
            print()

        if graph:
            print(f"Total alive players: {len(graph.keys())}")
        return []

    def compute_targets(self):
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
            print("[TARGETING] Refusing to generate a targeting graph (too few non-police assassins).")
            return {}

        # FIRST STEP, get initial targets
        # we use a hash set to cache combinations disallowed in subsequent chains.
        # (i.e., a targets b in chain one means a cannot target b and b cannot target a in chain two)
        claimed_combos = set()

        def new_unique_chain(abort_after=1000):
            chain = [p for p in players]
            random.shuffle(chain)
            tries = 0
            while any((a, b) in claimed_combos or (b, a) in claimed_combos
                      for (a, b) in zip(chain, chain[1:] + [chain[0]])):
                if tries >= abort_after:
                    raise FailedToCreateChainException()
                random.shuffle(chain)
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

        # NO USE OF RANDOM AFTER THIS POINT WITHOUT RE-SEEDING.

        for e in events:
            deaths = [victim for (_, victim) in e.kills]

            # try to fix with triangle elimination
            # this function has side effects
            success = self.update_graph(targeting_graph, targeters_graph, deaths)
            if success:
                continue

            success = self.update_graph(targeting_graph, targeters_graph, deaths, allow_mutual_targets=True)
            if success:
                print("[TARGETING] WARNING: An unavoidable targeting graph collapse has lead to two assassins"
                      " targeting each other.")
                continue

            print("[TARGETING] CRITICAL: The targeting graph 3-targets 3-targeting invariant cannot be maintained."
                  " Targeting has been ABORTED. IT IS TIME TO BEGIN OPEN SEASON.")
            return {}

        return targeting_graph

    def update_graph(
            self,
            targeting_graph: Dict[str, List[str]],
            targeters_graph: Dict[str, List[str]],
            deaths: List[str],
            allow_mutual_targets: bool = False
    ) -> bool:
        """
        Updates the targeting graph given a list of deaths.

        The problem is constraint satisfaction so a Prolog-style "generate-and-test" is sufficient.
        """

        # collect a list of [non-unique] players who need new targets
        targeters = sum((targeters_graph[d] for d in deaths), start=[])
        targeters = [t for t in targeters if t not in deaths]

        # collect a list of [non-unique]
        targeting = sum((targeting_graph[d] for d in deaths), start=[])
        targeting = [t for t in targeting if t not in deaths]

        # we assume as a precondition the "3-targeters, 3-targeting" invariant.
        # this guarantees len(targeters) == len(targeting)
        assert(len(targeters) == len(targeting))

        # to generate-and-test all matchings, we can permute one list and zip it with the second
        new_targets: List[Tuple[str, str]]
        for targeters_permutation in itertools.permutations(targeters):
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

