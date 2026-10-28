# Sloth OS knowledge

`knowledge.json` lists which settings make Windows programs start on [Sloth OS](https://github.com/Sloth-OS-Linux/sloth-os),
learned from anonymous reports of Sloth OS machines whose users turned on
*Sloth Center → Windows programs → Share experiences*.

Sloth OS machines download this file in the background and use the setting as the first attempt for a
program, so it starts on the first try. It has two sources:

- **`programs`**: reports of Sloth OS machines, updated hourly by the `export` workflow from the Sloth OS
  knowledge service.
- **`games`**: derived monthly from the [ProtonDB](https://www.protondb.com) public data dump
  ([bdefore/protondb-data](https://github.com/bdefore/protondb-data)) by the `protondb` workflow
  (`seed/protondb.py`), keyed by Steam AppID (`umu-<appid>`). Only structured fields are used (Proton
  variant, launch flags, launch options, and allowlisted component names), only reports from the last two
  years, and a game is listed only if the setting that worked most often is not the default one and at
  least 3 reports back it up.

Format:

```json
{
 "version": 1,
 "programs": {
  "<sha256 of the program's normalized name and .exe file name>": {
   "<amd|nvidia|intel|other>": {
    "line": "UMU-Proton",
    "profile": "nofsync",
    "fixes": [["verb", "vcrun2022"]],
    "machines": 12
   }
  }
 }
}
```

For `games`, the key is `umu-<Steam AppID>` and `reports` replaces `machines`; a `"any"` entry covers all
GPU vendors.

Program names are never collected from Sloth OS machines: machines compute the hash locally. A setting appears here only after
it worked on at least 3 different machines with a success rate of at least 75%. Only allowlisted values
are accepted (Proton line, profile, a fixed list of Proton on/off switches and components), both by the
service and by the machines that read this file.

## "Will it run?" game list

`games-index.json` is the list behind *Sloth Center → Games → Will it run?*: type a game's name and see how well it
runs. It is made monthly by the `protondb` workflow (`seed/games_index.py`) from:

- **ProtonDB** reports of the last two years ([ODbL](https://opendatacommons.org/licenses/odbl/)): how many say the
  game works (in total and per GPU vendor), and whether most played its own Linux version. Rating: `great` if at
  least 85% say it works, `ok` if at least half, `poor` below that, empty with fewer than 3 reports.
- **[AreWeAntiCheatYet](https://areweanticheatyet.com)** (MIT): games whose anti-cheat blocks Linux (`denied`: the
  makers do not allow it; `broken`: it does not work) or works (`supported`, `running`).
- **`sloth-tested.json`**: games the Sloth OS team tried itself (edit it by hand, in the GitHub web editor too):

```json
{"version": 1, "games": {"steam:1245620": {"name": "ELDEN RING", "result": "works", "date": "2026-10-28"}}}
```

`result` is `works`, `issues` or `no`; the key is `steam:<AppID>`, or `awacy:<slug>` for a game not on Steam.

## Recipes

`recipes.json` holds hand-curated settings for well-known launchers and programs (Battle.net, Epic Games
Launcher, GOG Galaxy, Ubisoft Connect…), as data rather than code: which short-lived launcher should be replaced
by its client, which `.exe` belongs in the Start menu and which helpers to skip, plus components, Proton switches,
program arguments and DLL overrides. Sloth OS ships a copy and downloads this file in the background; the newer
one (`updated`) wins.

Only allowlisted fields and values are accepted, both by the `recipes` workflow (`seed/validate_recipes.py`, on
every push and pull request) and again by every Sloth OS machine: no arbitrary commands, environment variables,
arguments or native DLL loading. A recipe that fails the check is ignored; the others keep working.

```json
{
 "version": 1,
 "updated": "2026-10-19",
 "recipes": [
  {
   "id": "battlenet",
   "name": "Battle.net",
   "match": {"dirs": ["Program Files (x86)/Battle.net"], "exe": ["battle.net*.exe"]},
   "stubs": {"battle.net launcher.exe": "Battle.net.exe"},
   "prefer": ["battle.net launcher.exe"],
   "skip": ["battle.net uninstaller.exe"],
   "dll_overrides": ["locationapi=d"]
  }
 ]
}
```

To add or change a recipe, open a pull request and bump `updated`.

## License

`knowledge.json` and `games.json` contain data derived from the ProtonDB data dump, which is made available
under the [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/); individual
contents under the [Database Contents License](https://opendatacommons.org/licenses/dbcl/1-0/). Accordingly,
these files are also made available under the ODbL 1.0. Data source: ProtonDB, https://www.protondb.com.
The scripts and workflows in this repository, and `recipes.json`, are available under the MIT License.
