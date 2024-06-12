import datetime
from typing import List

import inquirer

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.html_components import HTMLComponent
from AU2.html_components.ArbitraryList import ArbitraryList
from AU2.html_components.AssassinDependentCrimeEntry import AssassinDependentCrimeEntry
from AU2.html_components.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.AssassinDependentReportEntry import AssassinDependentReportEntry
from AU2.html_components.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.AssassinPseudonymPair import AssassinPseudonymPair
from AU2.html_components.Checkbox import Checkbox
from AU2.html_components.DatetimeEntry import DatetimeEntry
from AU2.html_components.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.Dependency import Dependency
from AU2.html_components.HiddenTextbox import HiddenTextbox
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.AssassinDependentKillEntry import AssassinDependentKillEntry
from AU2.html_components.Label import Label
from AU2.html_components.NamedSmallTextbox import NamedSmallTextbox
from AU2.plugins.AbstractPlugin import Export
from AU2.plugins.CorePlugin import PLUGINS


DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def datetime_validator(_, current):
    try:
        s = datetime.datetime.strptime(current, DATETIME_FORMAT)
    except ValueError:
        return False
    return True


def integer_validator(_, current):
    try:
        s = int(current)
    except ValueError:
        return False
    return True


def render(html_component, dependency_context={}):
    """
    dependency context is a MUTABLE DEFAULT ARGUMENT
    if you are modifying it THEN MODIFY A COPY
    TODO: don't use a mutable default arg!
    (see in Scala, I already solved this problem with a beautiful scoping stack-map)
    (but it's idiomatically FP and not idiomatically Python)
    """
    if isinstance(html_component, Dependency):
        # we can guarantee the necessary context is at front of Dependency
        needed = html_component.htmlComponents[0]
        # if this fails check the sorting function (merge_dependency)
        assert(needed.identifier == html_component.dependentOn)
        out = render(needed, dependency_context)
        new_dependency = dependency_context.copy()
        new_dependency.update(out)
        for h in html_component.htmlComponents[1:]:
            out.update(render(h, new_dependency))
        return out
    elif isinstance(html_component, AssassinPseudonymPair):
        assassins = [a[0] for a in html_component.assassins]
        q = [inquirer.Checkbox(
            name="q",
            message="Choose which assassins are in this event",
            choices=assassins,
            default=list(html_component.default.keys()))]
        chosen_assassins = inquirer.prompt(q)["q"]
        mappings = {}
        for player in chosen_assassins:
            choices = [a[1] for a in html_component.assassins if a[0] == player][0]
            q = [inquirer.List(
                name="q",
                message=f"{player}: Choose pseudonym",
                choices=choices,
                default=html_component.default.get(player, "")
            )]
            pseudonym = inquirer.prompt(q)["q"]
            mappings[player] = choices.index(pseudonym)
            print(f"Using {player}: {pseudonym}")
        return {html_component.identifier: mappings}

    # dependent component
    elif isinstance(html_component, AssassinDependentReportEntry):
        dependent = html_component.pseudonym_list_identifier
        assert(dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        q = [inquirer.Checkbox(
            name="q",
            message="Reports (select players with reports)",
            choices=list(assassins_mapping.keys()),
            default=list(a[0] for a in html_component.default) # default: List[Tuple[str, int, str]]
        )]
        reporters = inquirer.prompt(q)["q"]
        results = []
        default_mapping = {
            a[:2]: a[2] for a in html_component.default
        }
        for r in reporters:
            key = (r, assassins_mapping[r])
            q = [inquirer.Editor(
                name="report",
                message=f"Report: {r}",
                default=default_mapping.get(key)
            )]
            report = inquirer.prompt(q)["report"]
            results.append((r, assassins_mapping[r], report))
        return {html_component.identifier: results}

    # dependent component
    elif isinstance(html_component, AssassinDependentKillEntry):
        dependent = html_component.assassins_list_identifier
        assert(dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        assassins = list(assassins_mapping.keys())
        if len(assassins) <= 1:
            return {html_component.identifier: tuple()}
        potential_kills = {}
        defaults = []
        for a1 in assassins:
            for a2 in assassins:
                if a1 != a2:
                    potential_kills[f"{a1} kills {a2}"] = (a1, a2)
                    if (a1, a2) in html_component.default:
                        defaults.append(f"{a1} kills {a2}")
        q = [inquirer.Checkbox(
            name="q",
            message="Select kills",
            choices=list(potential_kills.keys()),
            default=defaults
        )]
        # TODO: Confirm what happens if option in default isn't in choices
        a = inquirer.prompt(q)["q"]
        a = tuple(potential_kills[k] for k in a)
        return {html_component.identifier: a}

    # dependent component
    elif isinstance(html_component, AssassinDependentCrimeEntry):
        dependent = html_component.pseudonym_list_identifier
        assert(dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        q = [inquirer.Checkbox(
            name="q",
            message=html_component.title,
            choices=list(assassins_mapping.keys()),
            default=list(html_component.default.keys()) # default: Dict[str, int]
        )]
        assassins = inquirer.prompt(q)["q"]
        results = {}
        for a in assassins:
            q = [
                inquirer.Text(
                    name="duration",
                    message=f"WANTED DURATION (from now) for: {a} "
                            f"(setting -1 will wipe the Wanted override from this event. "
                            f"setting 0 will set them as not Wanted.)",
                    default=html_component.default.get(a, (None, None, None))[0],
                    validate=integer_validator
                ), inquirer.Text(
                    name="crime",
                    message=f"CRIME for: {a}",
                    default=html_component.default.get(a, (None, None, None))[1],
                    ignore=lambda x: int(x["duration"]) <= 0
                ), inquirer.Text(
                    name="redemption",
                    message=f"REDEMPTION for: {a}",
                    default=html_component.default.get(a, (None, None, None))[2],
                    ignore=lambda x: int(x["duration"]) <= 0
                )]
            value = inquirer.prompt(q)
            if int(value["duration"]) >= 0:
                results[a] = (int(value["duration"]), value.get("crime", ""), value.get("redemption", ""))
        return {html_component.identifier: results}

    # dependent component
    elif isinstance(html_component, AssassinDependentSelector):
        dependent = html_component.pseudonym_list_identifier
        assert(dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        assassins = [a for a in assassins_mapping]
        q = [inquirer.Checkbox(
            name=html_component.identifier,
            message=html_component.title,
            choices=assassins,
            default=html_component.default
        )]
        return inquirer.prompt(q)

    # dependent component
    elif isinstance(html_component, AssassinDependentIntegerEntry):
        dependent = html_component.pseudonym_list_identifier
        assert(dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        assassins = [a for a in assassins_mapping]
        q = [inquirer.Checkbox(
            name="assassins",
            message=html_component.title,
            choices=assassins,
            default=list(html_component.default.keys())
        )]
        selected_assassins = inquirer.prompt(q)["assassins"]
        q = []
        for a in selected_assassins:
            q.append(inquirer.Text(
                name=a,
                message=f"Value for {a}",
                default=html_component.default.get(a, None),
                validate=integer_validator
            ))
        points = inquirer.prompt(q)
        return {html_component.identifier: {k: int(v) for (k, v) in points.items()}}

    elif isinstance(html_component, DatetimeEntry):
        q = [inquirer.Text(
            name="dt",
            message="Enter date/time of event (YYYY-MM-DD HH:MM)",
            default=html_component.default.strftime(DATETIME_FORMAT),
            validate=datetime_validator
        )]
        datetime_str = inquirer.prompt(q)["dt"]
        return {html_component.identifier: datetime.datetime.strptime(datetime_str, DATETIME_FORMAT)}

    elif isinstance(html_component, Label):
        print(html_component.title)
        return {}

    elif isinstance(html_component, Checkbox):
        q = [inquirer.List(name="q", message=html_component.title, choices=["No", "Yes"], default="Yes" if html_component.checked else "No")]
        a = inquirer.prompt(q)
        return {html_component.identifier: a["q"] == "Yes"}

    elif isinstance(html_component, HiddenTextbox):
        return {html_component.identifier: html_component.default}

    elif isinstance(html_component, NamedSmallTextbox):
        q = [inquirer.Text(name=html_component.identifier, message=html_component.title)]
        return inquirer.prompt(q)

    elif isinstance(html_component, InputWithDropDown):
        q = [inquirer.List(
                name=html_component.identifier,
                message=html_component.title,
                choices=html_component.options,
                default=html_component.selected)]
        return inquirer.prompt(q)

    elif isinstance(html_component, DefaultNamedSmallTextbox):
        q = [inquirer.Text(name=html_component.identifier, message=html_component.title, default=html_component.default)]
        return inquirer.prompt(q)

    elif isinstance(html_component, ArbitraryList):
        q = [inquirer.Checkbox(
            name=html_component.identifier,
            message=html_component.title,
            choices=html_component.values + ["*Other*"],
            default=html_component.values
        )]
        a = inquirer.prompt(q)
        if "*Other*" in a[html_component.identifier]:
            a[html_component.identifier].remove("*Other*")
            print("Adding new pseudonyms.")
            print("Instructions:")
            print("    Leave a blank string if you want to add no pseudonyms")
            print("    Separate new pseudonyms by commas")
            print("    E.g. Vendetta,Pyrite,Mina will generate the list ['Vendetta', 'Pyrite', 'Mina']")
            print("    Adding *Other* as a pseudonym would be, shall we say, dumb. Don't do that.")
            q = [inquirer.Text(
                name="newpseudonyms",
                message="Enter new pseudonyms",
            )]
            out = inquirer.prompt(q)["newpseudonyms"]
            if out:
                out = out.split(",")
                print("New pseudonyms:", out)
                a[html_component.identifier] = a[html_component.identifier] + out
        return a

    else:
        raise Exception("Unknown component type:", type(html_component))


def move_dependent_to_front(dependency: Dependency) -> None:
    # only the required element should have score False(=0) (and the rest True(=1))
    dependency.htmlComponents.sort(key=lambda h: h.identifier != dependency.dependentOn)
    assert(dependency.htmlComponents[0].identifier == dependency.dependentOn)

def merge_dependency(component_list: List[HTMLComponent]) -> List[HTMLComponent]:
    final = []
    deps: List[Dependency] = []
    for c in component_list:
        if isinstance(c, Dependency):
            deps.append(c)
        else:
            final.append(c)
    deps.sort(key=lambda d: d.dependentOn)
    if deps:
        d1 = deps[0]
        for d2 in deps[1:]:
            if d1.dependentOn == d2.dependentOn:
                d1.htmlComponents += d2.htmlComponents
            else:
                final.insert(0, d1)
                move_dependent_to_front(d1)
                d1 = d2
        final.insert(0, d1)
        move_dependent_to_front(d1)
    return final

if __name__ == "__main__":
    exports = []
    for p in PLUGINS:
        exports += p.exports
    while True:
        q = [inquirer.List(name="mode", message="Select mode.", choices=[e.display_name for e in exports] + ["Exit"])]
        a = inquirer.prompt(q)["mode"]
        if a == "Exit":
            print("Have a good day!")
            exit()

        exp: Export = None
        for e in exports:
            if e.display_name == a:
                exp = e
                break

        params = []
        qs = []
        i = 0
        for f in exp.options_functions:
            qs.append(inquirer.List(name=i, choices=f()))
            i += 1
        if qs:
            a = inquirer.prompt(qs)
            for k in range(i):
                params.append(a[k])

        inp = {}
        components = exp.ask(*params)
        components = merge_dependency(components)
        for component in components:
            result = render(component)
            inp.update(result)
        components = exp.answer(inp)
        for component in components:
            render(component)

        print("Saving databases...")
        ASSASSINS_DATABASE.save()
        EVENTS_DATABASE.save()
        GENERIC_STATE_DATABASE.save() # utility database