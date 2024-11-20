# -*- coding: utf-8 -*-
import copy
import datetime
import tabulate
from typing import List, Any, Dict

import inquirer

from AU2 import TIMEZONE
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.html_components import HTMLComponent
from AU2.html_components.MetaComponents.ComponentOverride import ComponentOverride
from AU2.html_components.MetaComponents.Searchable import Searchable
from AU2.html_components.DependentComponents.AssassinDependentCrimeEntry import AssassinDependentCrimeEntry
from AU2.html_components.DependentComponents.AssassinDependentFloatEntry import AssassinDependentFloatEntry
from AU2.html_components.DependentComponents.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.DependentComponents.AssassinDependentReportEntry import AssassinDependentReportEntry
from AU2.html_components.DependentComponents.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.DependentComponents.AssassinDependentTextEntry import AssassinDependentTextEntry
from AU2.html_components.DependentComponents.AssassinPseudonymPair import AssassinPseudonymPair
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DatetimeEntry import DatetimeEntry
from AU2.html_components.SimpleComponents.OptionalDatetimeEntry import OptionalDatetimeEntry
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.SimpleComponents.EmailSelector import EmailSelector
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.DependentComponents.AssassinDependentKillEntry import AssassinDependentKillEntry
from AU2.html_components.SimpleComponents.IntegerEntry import IntegerEntry
from AU2.html_components.SimpleComponents.FloatEntry import FloatEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.Table import Table
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.NamedSmallTextbox import NamedSmallTextbox
from AU2.html_components.SimpleComponents.PathEntry import PathEntry
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.html_components.SpecialComponents.EditablePseudonymList import EditablePseudonymList, PseudonymData, \
    ListUpdates
from AU2.plugins.AbstractPlugin import Export
from AU2.plugins.CorePlugin import PLUGINS, CorePlugin
from AU2.plugins.util.date_utils import get_now_dt
from AU2.plugins.util.game import escape_format_braces

DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def datetime_validator(_, current):
    try:
        if current is None:
            raise KeyboardInterrupt
        s = datetime.datetime.strptime(current, DATETIME_FORMAT)
    except ValueError:
        return False
    return True


# same as above except allows blank values (for pseudonym datetimes this represents being valid forever)
def optional_datetime_validator(_, current):
    try:
        if current is None:
            raise KeyboardInterrupt
        if current == "":
            return True
        s = datetime.datetime.strptime(current, DATETIME_FORMAT)
    except ValueError:
        return False
    return True


# TODO: Create a generic type validator

def integer_validator(_, current):
    try:
        if current is None:
            raise KeyboardInterrupt
        s = int(current)
    except ValueError:
        return False
    return True


def float_validator(_, current):
    try:
        if current is None:
            raise KeyboardInterrupt
        s = float(current)
    except ValueError:
        return False
    return True


def inquirer_prompt_with_abort(*args, **kwargs) -> Any:
    """
    Catches implicit keyboard interrupts in user code (i.e., inquirer output = None)
    """
    output = inquirer.prompt(*args, **kwargs)
    if output is None:
        raise KeyboardInterrupt
    return output


def render(html_component, dependency_context={}):
    """
    dependency context is a MUTABLE DEFAULT ARGUMENT
    if you are modifying it THEN MODIFY A COPY
    TODO: don't use a mutable default arg!
    """
    if isinstance(html_component, Dependency):
        iteration = 0
        last_step = 1
        while iteration < len(html_component.htmlComponents):
            if iteration == -1:
                raise KeyboardInterrupt
            try:
                if iteration == 0:
                    # we can guarantee the necessary context is at front of Dependency
                    needed = html_component.htmlComponents[0]
                    # if this fails check the sorting function (merge_dependency)
                    assert (needed.identifier == html_component.dependentOn)
                    out = render(needed, dependency_context)
                    new_dependency = dependency_context.copy()
                    new_dependency.update(out)
                elif iteration > 0:
                    h = html_component.htmlComponents[iteration]
                    if h.noInteraction and last_step == -1:
                        iteration -= 1
                        continue
                    value = render(h, new_dependency)
                    if value.get("skip", False) and last_step == -1:
                        iteration -= 1
                        continue
                    out.update(value)
                iteration += 1
                last_step = 1
            except KeyboardInterrupt:
                iteration -= 1
                last_step = -1

        if "skip" in out:
            del out["skip"]
        return out

    elif isinstance(html_component, Searchable):
        answer = ""
        while True:
            q = [inquirer.Text(
                name="q",
                default=answer,
                message=f"{html_component.title} (separate with commas for each searchable)"
            )]
            answer = inquirer_prompt_with_abort(q)["q"]
            filters = [candidate.strip() for candidate in answer.split(",") if candidate.strip()]
            component_copy = copy.copy(html_component.component)
            options = html_component.accessor(component_copy)

            is_default = lambda o: hasattr(html_component.component, "default") \
                                   and o in html_component.component.default

            if filters:
                options = [o for o in options if any(f.lower() in o.lower() for f in filters) or is_default(o)]
            html_component.setter(component_copy, options)
            try:
                return render(component_copy, dependency_context)
            except KeyboardInterrupt:
                continue

    # dependent component
    elif isinstance(html_component, AssassinPseudonymPair):
        assassins = [a[0] for a in html_component.assassins]
        assassins.sort()
        if not assassins:
            return {html_component.identifier: {}, "skip": True}
        q = [
            inquirer.Checkbox(
                name="q",
                message="Choose which assassins are in this event",
                choices=assassins,
                default=list(html_component.default.keys())
            )]
        chosen_assassins = inquirer_prompt_with_abort(q)["q"]
        mappings = {}
        for player in chosen_assassins:
            values = [a[1] for a in html_component.assassins if a[0] == player][0]
            choices = [(c, i) for i, c in enumerate(values) if c]  # hide any null (i.e. deleted) pseudonyms
            if len(choices) != 1:
                q = [
                    inquirer.List(
                        name="q",
                        message=f"{escape_format_braces(player)}: Choose pseudonym",
                        choices=choices,
                        default=html_component.default.get(player, "")
                    )]
                pseudonym_index = inquirer_prompt_with_abort(q)["q"]
            else:
                pseudonym_index = choices[0][1]
            pseudonym = values[pseudonym_index]
            mappings[player] = pseudonym_index
            print(f"Using {player}: {pseudonym}")
        return {html_component.identifier: mappings}

    # dependent component
    elif isinstance(html_component, AssassinDependentReportEntry):
        dependent = html_component.pseudonym_list_identifier
        assert (dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        if not assassins_mapping:
            return {html_component.identifier: [], "skip": True}
        q = [inquirer.Checkbox(
            name="q",
            message="Reports (select players with reports)",
            choices=list(assassins_mapping.keys()),
            default=list(a[0] for a in html_component.default)  # default: List[Tuple[str, int, str]]
        )]
        reporters = inquirer_prompt_with_abort(q)["q"]
        results = []
        default_mapping = {
            a[:2]: a[2] for a in html_component.default
        }
        if assassins_mapping:
            print("FORMATTING ADVICE")
            print("    [PX] Renders pseudonym of assassin with ID X (if in the event)")
            print(
                "    [PX_i] Renders the ith pseudonym (with 0 as first pseudonym) of assassin with ID X (if in the event)")
            print("    [DX] Renders ALL pseudonyms of assassin with ID X (if in the event)")
            print("    [NX] Renders real name of assassin with ID X (if in the event)")
            print("ASSASSIN IDENTIFIERS")
            for a in assassins_mapping:
                assassin_model = ASSASSINS_DATABASE.get(a)
                print(f"    ({assassin_model._secret_id}) {assassin_model.real_name}")
        for r in reporters:
            key = (r, assassins_mapping[r])
            q = [inquirer.Editor(
                name="report",
                message=f"Report: {escape_format_braces(r)}",
                default=escape_format_braces(default_mapping.get(key, ''))
            )]
            report = inquirer_prompt_with_abort(q)["report"]
            results.append((r, assassins_mapping[r], report))
        return {html_component.identifier: results}

    # dependent component
    elif isinstance(html_component, AssassinDependentKillEntry):
        dependent = html_component.assassins_list_identifier
        assert (dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        if not assassins_mapping:
            return {html_component.identifier: [], "skip": True}
        assassins = list(assassins_mapping.keys())
        if len(assassins) <= 1:
            return {html_component.identifier: tuple(), "skip": True}
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
        a = inquirer_prompt_with_abort(q)["q"]
        a = tuple(potential_kills[k] for k in a)
        return {html_component.identifier: a}

    # dependent component
    elif isinstance(html_component, AssassinDependentCrimeEntry):
        dependent = html_component.pseudonym_list_identifier
        assert (dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        if not assassins_mapping:
            return {html_component.identifier: {}, "skip": True}
        q = [inquirer.Checkbox(
            name="q",
            message=escape_format_braces(html_component.title),
            choices=list(assassins_mapping.keys()),
            default=list(html_component.default.keys())  # default: Dict[str, int]
        )]
        assassins = inquirer_prompt_with_abort(q)["q"]
        results = {}
        if assassins:
            print("Duration is specified in days:")
            print("    >0 sets them as WANTED")
            print("    =0 sets them as NOT WANTED")
            print("    <0 removes any mention of wantedness from this event")
        for a in assassins:
            q = [
                inquirer.Text(
                    name="duration",
                    message=f"WANTED DURATION for: {escape_format_braces(a)} ",
                    default=html_component.default.get(a, ("", "", ""))[0],
                    validate=integer_validator
                ), inquirer.Text(
                    name="crime",
                    message=f"CRIME for: {escape_format_braces(a)}",
                    default=escape_format_braces(html_component.default.get(a, ("", "", ""))[1]),
                    ignore=lambda x: int(x["duration"]) <= 0
                ), inquirer.Text(
                    name="redemption",
                    message=f"REDEMPTION for: {escape_format_braces(a)}",
                    default=escape_format_braces(html_component.default.get(a, ("", "", ""))[2]),
                    ignore=lambda x: int(x["duration"]) <= 0
                )]
            value = inquirer_prompt_with_abort(q)
            if int(value["duration"]) >= 0:
                results[a] = (int(value["duration"]), value.get("crime", ""), value.get("redemption", ""))
        return {html_component.identifier: results}

    # dependent component
    elif isinstance(html_component, AssassinDependentSelector):
        dependent = html_component.pseudonym_list_identifier
        assert (dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        if not assassins_mapping:
            return {html_component.identifier: [], "skip": True}
        assassins = [a for a in assassins_mapping]
        q = [inquirer.Checkbox(
            name=html_component.identifier,
            message=escape_format_braces(html_component.title),
            choices=assassins,
            default=html_component.default
        )]
        return inquirer_prompt_with_abort(q)

    # dependent component
    elif isinstance(html_component, AssassinDependentFloatEntry):
        dependent = html_component.pseudonym_list_identifier
        assert (dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        if not assassins_mapping:
            return {html_component.identifier: {}, "skip": True}
        assassins = [a for a in assassins_mapping]
        q = [inquirer.Checkbox(
            name="assassins",
            message=escape_format_braces(html_component.title),
            choices=assassins,
            default=list(html_component.default.keys())
        )]
        selected_assassins = inquirer_prompt_with_abort(q)["assassins"]
        q = []
        for a in selected_assassins:
            q.append(inquirer.Text(
                name=a,
                message=f"Value for {escape_format_braces(a)}",
                default=html_component.default.get(a, None),
                validate=float_validator
            ))
        points = inquirer_prompt_with_abort(q)
        return {html_component.identifier: {k: float(v) for (k, v) in points.items()}}

    # dependent component
    elif isinstance(html_component, AssassinDependentIntegerEntry):
        dependent = html_component.pseudonym_list_identifier
        assert (dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        if not assassins_mapping:
            return {html_component.identifier: {}, "skip": True}
        assassins = [a for a in assassins_mapping]
        q = [inquirer.Checkbox(
            name="assassins",
            message=escape_format_braces(html_component.title),
            choices=assassins,
            default=list(html_component.default.keys())
        )]
        selected_assassins = inquirer_prompt_with_abort(q)["assassins"]
        q = []
        for a in selected_assassins:
            val_if_exists = html_component.default.get(a, None)
            q.append(inquirer.Text(
                name=a,
                message=f"Value for {escape_format_braces(a)}",
                default=val_if_exists if val_if_exists is not None else html_component.global_default,
                validate=integer_validator
            ))
        points = inquirer_prompt_with_abort(q)
        return {html_component.identifier: {k: int(v) for (k, v) in points.items()}}

    # dependent component
    elif isinstance(html_component, AssassinDependentTextEntry):
        dependent = html_component.pseudonym_list_identifier
        assert (dependent in dependency_context)
        assassins_mapping = dependency_context[dependent]
        if not assassins_mapping:
            return {html_component.identifier: {}, "skip": True}
        assassins = [a for a in assassins_mapping]
        q = [inquirer.Checkbox(
            name="assassins",
            message=escape_format_braces(html_component.title),
            choices=assassins,
            default=list(html_component.default.keys())
        )]
        selected_assassins = inquirer_prompt_with_abort(q)["assassins"]
        q = []
        for a in selected_assassins:
            q.append(inquirer.Text(
                name=a,
                message=f"Value for {escape_format_braces(a)}",
                default=escape_format_braces(html_component.default.get(a, ""))
            ))
        points = {}
        if q:
            points = inquirer_prompt_with_abort(q)
        return {html_component.identifier: points}

    elif isinstance(html_component, DatetimeEntry):
        q = [inquirer.Text(
            name="dt",
            message=f"{escape_format_braces(html_component.title)} (YYYY-MM-DD HH:MM)",
            default=html_component.default.strftime(DATETIME_FORMAT),
            validate=datetime_validator
        )]
        datetime_str = inquirer_prompt_with_abort(q)["dt"]
        return {
            html_component.identifier: datetime.datetime.strptime(datetime_str, DATETIME_FORMAT).astimezone(TIMEZONE)}

    elif isinstance(html_component, OptionalDatetimeEntry):
        default = html_component.default.strftime(DATETIME_FORMAT) if html_component.default else ""
        q = [inquirer.Text(
            name="dt",
            message=f"{escape_format_braces(html_component.title)} (YYYY-MM-DD HH:MM)",
            default=default,
            validate=optional_datetime_validator
        )]
        datetime_str = inquirer_prompt_with_abort(q)["dt"]
        ts = (datetime.datetime.strptime(datetime_str, DATETIME_FORMAT).astimezone(TIMEZONE) if datetime_str
              else None)
        return {
            html_component.identifier: ts}

    elif isinstance(html_component, IntegerEntry):
        q = [inquirer.Text(
            name="int",
            message=escape_format_braces(html_component.title),
            default=html_component.default,
            validate=integer_validator
        )]
        integer = inquirer_prompt_with_abort(q)["int"]
        return {html_component.identifier: int(integer)}

    elif isinstance(html_component, FloatEntry):
        q = [inquirer.Text(
            name="float",
            message=escape_format_braces(html_component.title),
            default=html_component.default,
            validate=float_validator
        )]
        number = inquirer_prompt_with_abort(q)["float"]
        return {html_component.identifier: float(number)}

    elif isinstance(html_component, PathEntry):
        q = [inquirer.Path(
            name=html_component.identifier,
            message=escape_format_braces(html_component.title),
            default=html_component.default
        )]
        return inquirer_prompt_with_abort(q)

    elif isinstance(html_component, Label):
        print(html_component.title)
        return {}

    elif isinstance(html_component, Table):
        print(tabulate.tabulate(html_component.rows, headers=html_component.headings,
                                maxcolwidths=[len(h) for h in html_component.headings]))
        return {}

    elif isinstance(html_component, Checkbox):
        q = [
            inquirer.List(
                name="q",
                message=escape_format_braces(html_component.title),
                choices=["No", "Yes"],
                default="Yes" if html_component.checked else "No"
            )]
        a = inquirer_prompt_with_abort(q)
        return {html_component.identifier: a["q"] == "Yes"}

    elif isinstance(html_component, HiddenTextbox):
        return {html_component.identifier: html_component.default}

    elif isinstance(html_component, NamedSmallTextbox):
        q = [inquirer.Text(name=html_component.identifier, message=escape_format_braces(html_component.title))]
        return inquirer_prompt_with_abort(q)

    elif isinstance(html_component, LargeTextEntry):
        q = [inquirer.Editor(name=html_component.identifier, message=escape_format_braces(html_component.title),
                             default=escape_format_braces(html_component.default))]
        return inquirer_prompt_with_abort(q)

    elif isinstance(html_component, InputWithDropDown):
        q = [inquirer.List(
            name=html_component.identifier,
            message=escape_format_braces(html_component.title),
            choices=html_component.options,
            default=html_component.selected)]
        return inquirer_prompt_with_abort(q)

    elif isinstance(html_component, DefaultNamedSmallTextbox):
        q = [inquirer.Text(
            name=html_component.identifier,
            message=escape_format_braces(html_component.title),
            default=escape_format_braces(html_component.default))]
        return inquirer_prompt_with_abort(q)

    # TODO: fundamentally this component is just editing a list where each entry has multiple parts to this value,
    #       so we may want to abstract this component
    elif isinstance(html_component, EditablePseudonymList):
        values = html_component.values
        old_n_values = len(values)
        edited = {}  # dict mapping index to new value
        new_values = []
        deleted_indices = set()
        while True:
            q = [inquirer.List(
                name=html_component.identifier,
                message=escape_format_braces(html_component.title),
                choices=[("*CONTINUE*", -1)] + [(v.text, i) for i, v in enumerate(values) if v.text] + [("*NEW*", -2)],
            )]
            a = inquirer_prompt_with_abort(q)
            c = a[html_component.identifier]  # index of choice
            if c == -2:  # case where "*NEW*" selected
                q = [inquirer.Text(
                    name="newpseudonym",
                    message="Enter a new pseudonym",
                )]
                try:
                    p = inquirer_prompt_with_abort(q)["newpseudonym"]
                except KeyboardInterrupt:
                    continue
                if p.strip() == "":
                    continue

                q = [inquirer.Text(
                    name="dt",
                    message=f"Enter start of validity (YYYY-MM-DD HH:MM) (blank if always valid)",
                    default=get_now_dt().strftime(DATETIME_FORMAT),
                    validate=optional_datetime_validator,
                )]
                try:
                    dt_str = inquirer_prompt_with_abort(q)["dt"]
                    valid_from = (None if dt_str == ""
                                  else datetime.datetime.strptime(dt_str, DATETIME_FORMAT).astimezone(TIMEZONE))
                except KeyboardInterrupt:
                    continue

                p_data = PseudonymData(p, valid_from)
                new_values.append(p_data)
                values.append(p_data)
            elif c == -1:  # case where "*CONTINUE*" selected
                break
            else:
                v = values[c]
                q = [inquirer.Text(
                    name="editpseudonym",
                    message="Enter replacement" + ("" if c == 0 else " (blank to delete)"),
                    # cannot delete initial pseudonym
                    default=escape_format_braces(v.text)
                )]
                try:
                    p = inquirer_prompt_with_abort(q)["editpseudonym"]
                except KeyboardInterrupt:
                    continue
                # whitespace values => delete.
                # could change this to some other input e.g. "-"
                if p.strip() == "":
                    if c == 0:  # if we don't catch this case then delete_pseudonym will throw an error down the line...
                        print("Can't delete initial pseudonym!")
                        continue

                    q = [inquirer.Confirm(
                        name="deletepseudonym",
                        message=f"Do you wish to delete the pseudonym {escape_format_braces(v.text)}?",
                        default=False
                    )]
                    try:
                        if inquirer_prompt_with_abort(q)["deletepseudonym"]:
                            deleted_indices.add(c)
                            values[c] = PseudonymData("", None)
                    finally:
                        continue

                if c == 0:  # initial pseudonym should always be valid forever
                    valid_from = v.valid_from
                else:
                    q = [inquirer.Text(
                        name="dt",
                        message=f"Enter start of validity (YYYY-MM-DD HH:MM) (blank if always valid)",
                        default=v.valid_from.strftime(DATETIME_FORMAT) if v.valid_from else "",
                        validate=optional_datetime_validator,
                    )]
                    try:
                        dt_str = inquirer_prompt_with_abort(q)["dt"]
                    except KeyboardInterrupt:
                        continue
                    valid_from = (None if dt_str == ""
                                  else datetime.datetime.strptime(dt_str, DATETIME_FORMAT).astimezone(TIMEZONE))
                p_data = PseudonymData(p, valid_from)
                values[c] = p_data
                if c < old_n_values:
                    edited[c] = p_data
                else:
                    new_values[c - old_n_values] = p_data

        return {html_component.identifier:
                    ListUpdates(edited, new_values, deleted_indices)}

    elif isinstance(html_component, SelectorList):
        q = [
            inquirer.Checkbox(
                name=html_component.identifier,
                message=escape_format_braces(html_component.title),
                choices=html_component.options,
                default=html_component.defaults
            )
        ]
        return inquirer_prompt_with_abort(q)

    elif isinstance(html_component, EmailSelector):
        q = [
            inquirer.List(
                name="emails",
                message="Which assassins would you like to email? (All options exclude hidden assassins)",
                choices=["UPDATES ONLY", "ALL", "ALL ALIVE", "ALL POLICE", "MANUAL SELECTION"],
                default="UPDATES ONLY",
            )
        ]
        out = inquirer_prompt_with_abort(q)["emails"]
        if out == "ALL":
            return {html_component.identifier: html_component.assassins}
        elif out == "ALL ALIVE":
            return {html_component.identifier: html_component.alive_assassins}
        elif out == "ALL POLICE":
            return {html_component.identifier: html_component.police_assassins}
        elif out == "UPDATES ONLY":
            return {html_component.identifier: ["UPDATES ONLY"]}
        else:
            q = [
                inquirer.Checkbox(
                    name=html_component.identifier,
                    message="Select assassins to send an email:",
                    choices=html_component.assassins
                )
            ]
            return inquirer_prompt_with_abort(q)

    else:
        raise Exception("Unknown component type:", type(html_component))


def move_dependent_to_front(dependency: Dependency) -> None:
    # only the required element should have score False(=0) (and the rest True(=1))
    dependency.htmlComponents.sort(key=lambda h: h.identifier != dependency.dependentOn)
    assert (dependency.htmlComponents[0].identifier == dependency.dependentOn)


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


def replace_overrides(component_list: List[HTMLComponent], existing_overrides={}) -> List[HTMLComponent]:
    override_map: Dict[str, ComponentOverride]
    if not existing_overrides:
        override_map = {o.overrides: o for o in component_list
                        if isinstance(o, ComponentOverride)}
    else:
        override_map = existing_overrides

    others: List[HTMLComponent] = [o for o in component_list if not isinstance(o, ComponentOverride)]
    final = []

    for component in others:
        if isinstance(component, Dependency):
            component.htmlComponents = replace_overrides(component.htmlComponents, override_map)
            final.append(component)
        elif component.identifier in override_map:
            override_map[component.identifier].replacement_effects(component,
                                                                   override_map[component.identifier].replace_with)
            final.append(override_map[component.identifier].replace_with)
        else:
            final.append(component)
    return final


def main():
    while True:
        core_plugin: CorePlugin = PLUGINS["CorePlugin"]
        exports = core_plugin.get_all_exports()

        q = [inquirer.List(name="mode", message="Select mode",
                           choices=["Exit"] + sorted([e.display_name for e in exports]))]
        try:
            a = inquirer_prompt_with_abort(q)["mode"]
        except KeyboardInterrupt:
            a = "Exit"
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
            qs.append(inquirer.List(name=i, choices=["*EXIT*"] + f(),
                                    ignore=lambda x: any(a[j] == "*EXIT*" for j in range(i))))
            i += 1
        if qs:
            try:
                a = inquirer_prompt_with_abort(qs)
            except KeyboardInterrupt:
                continue
            if any(a[k] == "*EXIT*" for k in range(i)):
                continue
            for k in range(i):
                params.append(a[k])

        inp = {}
        components = exp.ask(*params)
        components = replace_overrides(components)
        components = merge_dependency(components)
        iteration = 0
        last_step = 1
        while iteration < len(components):
            try:
                if iteration == -1:
                    break
                if last_step == -1 and components[iteration].noInteraction:
                    iteration -= 1
                    continue
                result = render(components[iteration])
                if result.get("skip", False) and last_step == -1:
                    iteration -= 1
                    continue
                inp.update(result)
                iteration += 1
                last_step = 1
            except KeyboardInterrupt:
                iteration -= 1
                last_step = -1
        if iteration != -1:
            components = exp.answer(inp)
            for component in components:
                render(component)

            print("Saving databases...")
            ASSASSINS_DATABASE.save()
            EVENTS_DATABASE.save()
            GENERIC_STATE_DATABASE.save()  # utility database


if __name__ == "__main__":
    main()
