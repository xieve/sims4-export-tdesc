# sims4-export-tdesc
Tool to export TDESC files for your custom tuning

## Warning
This mod injects into some very, very important tuning code and removes some performance improvements. I don't think the impact should be huge, but I still strongly advise against leaving this in your Mods folder when you don't need it.

## Installation
Put the .py into `Mods/export_tdesc/scripts/export_tdesc.py`. It has to be at `Mods/<folder>/scripts/` or it will not be loaded by the game.

## Usage
Open the console (<kbd>Ctrl</kbd> <kbd>Shift</kbd> <kbd>C</kbd>) and enter
```
export_tdesc my.module
```
to export the TDESCs for all classes in `my.module` (without submodules), or
```
export_tdesc my.module MyClass
```
to export the TDESCs specifically for the class `MyClass` in the module `my.module`.
