# Auto-Umpire 2 (AU2)

AU2 is a management system for running the Cambridge Assassins' Guild — a real-world assassination game played across Cambridge University. It handles player management, kill/event tracking, targeting, scoring, and game page generation through an interactive command-line interface.

---

## Features

- **Player management** — track assassins with pseudonyms (per-datetime validity), colleges, contact info, and water weapon status
- **Event tracking** — log kills, crimes, and reports with participant details and structured headlines
- **Targeting** — automatic target chain generation and email dispatch
- **Scoring** — points, competency tracking, and stats page generation
- **City Watch** — manage non-playing referee roles with ranking and auto-promotion
- **Page generation** — generate HTML news and stats pages for player-facing game websites
- **Bounty & Wanted systems** — track bounties and most-dangerous-assassin status
- **Player import** — bulk-import players from CSV or Google Sheets
- **Plugin architecture** — enable/disable game features per run; 14+ built-in plugins
- **Crash reporting** — automatic core dump generation for debugging

---

## Installation

### From PyPI (recommended)

```bash
pip install "Auto-Umpire 2"
```

### From source

```bash
git clone <repo-url>
cd au2
pip install -e .
```

### Bundled installer (Windows/macOS)

Run `AU2/frontends/au2_installer.py` to set up a self-contained virtual environment with convenience launchers (`au2_win.bat` on Windows, `au2_mac` on macOS).

---

## Usage

Launch the interactive CLI:

```bash
au2
```

Or via Python:

```bash
python -m AU2
```

AU2 presents an inquiry-based menu system. From the main menu you can:

- **Setup Game** — configure a new game (dates, colleges, plugins)
- **Manage Assassins** — add, edit, clone, or remove players
- **Log Events** — record kills, crimes, and other game events
- **Generate Pages** — publish HTML output to `~/pages/`
- **Plugin Actions** — access targeting, scoring, city watch, and other plugin menus

All data is persisted as JSON in `~/database/`.

---

## Architecture

```
AU2/
├── __main__.py              # Entry point with crash handling
├── database/
│   ├── AssassinsDatabase.py # Player storage and querying
│   ├── EventsDatabase.py    # Event storage
│   ├── GenericStateDatabase.py
│   └── model/
│       ├── Assassin.py      # Player data model
│       └── Event.py         # Event data model
├── plugins/
│   ├── AbstractPlugin.py    # Plugin base class
│   ├── CorePlugin.py        # Setup Game and core actions
│   └── custom_plugins/      # TargetingPlugin, ScoringPlugin,
│                            # PageGeneratorPlugin, CityWatchPlugin,
│                            # PlayerImporterPlugin, BountyPlugin,
│                            # MafiaPlugin, WantedPlugin, ...
├── html_components/         # UI component framework
│   ├── SimpleComponents/
│   ├── DependentComponents/
│   └── DerivativeComponents/
└── frontends/
    ├── inquirer_cli.py      # Main interactive frontend
    ├── au2_installer.py     # Bundled installer
    └── au2_packager.py      # Release packager (entry: au2_packager)
```

### Plugin system

Plugins extend the game with additional actions, state, and page sections. Each plugin subclasses `AbstractPlugin` and declares:

- **Exports** — menu actions surfaced in the CLI
- **State** — arbitrary JSON-serialisable data persisted between sessions
- **Hooks** — inter-plugin callbacks for coordinated behaviour

Enable or disable plugins per game via the Setup Game wizard.

---

## Event Headlines

Event headlines support format specifiers for dynamic content:

| Specifier | Expands to |
|---|---|
| `[DX]` | Killer's display pseudonym |
| `[VX]` | Victim's display pseudonym |
| `[NX]` | Killer's real name |

---

## Packaging a Release

```bash
au2_packager
```

Produces a `.zip` distribution suitable for end-user installation.

