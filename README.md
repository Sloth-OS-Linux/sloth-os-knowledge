# Sloth OS knowledge

`knowledge.json` lists which settings make Windows programs start on [Sloth OS](https://github.com/bathorizsolt),
learned from anonymous reports of Sloth OS machines whose users turned on
*Sloth Center → Windows programs → Share experiences*.

Sloth OS machines download this file in the background and use the setting as the first attempt for a
program, so it starts on the first try. The file is updated hourly by the `export` workflow from the
Sloth OS knowledge service.

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

Program names are never collected: machines compute the hash locally. A setting appears here only after
it worked on at least 3 different machines with a success rate of at least 75%. Only allowlisted values
are accepted (Proton line, profile and a fixed list of components), both by the service and by the
machines that read this file.
