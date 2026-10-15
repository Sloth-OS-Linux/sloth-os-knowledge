# Sloth OS knowledge

`knowledge.json` lists which settings make Windows programs start on [Sloth OS](https://github.com/bathorizsolt),
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

## License

`knowledge.json` and `games.json` contain data derived from the ProtonDB data dump, which is made available
under the [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/); individual
contents under the [Database Contents License](https://opendatacommons.org/licenses/dbcl/1-0/). Accordingly,
these files are also made available under the ODbL 1.0. Data source: ProtonDB, https://www.protondb.com.
The scripts and workflows in this repository are available under the MIT License.
