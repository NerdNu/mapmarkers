# Map Markers

This is a Python 3 script that reconciles `dynmap` markers in a specified world against
Minecraft map items in that world. It creates a "pin" marker named after the map
ID number in the centre of each map's render region.

This script assumes an environment running the `mark2` server wrapper to send
commands to the server console.


## Principle of Operation

The `dynmap` plugin stores all markers in `plugins/dynmap/markers.yml`. Minecraft
maps are stored in `worlds/world/data/map_<n>.dat` for each map ID, *`<n>`*.

The script works out the highest (most recent) map ID number at each (x,z) coordinate
pair, discards information about older (obsoleted) maps centred on those coordinates
and adjusts the `dynmap` markers by issuing `/dmarker delete` and `/dmarker add`
commands in the server console using `mark2 send -n <server>`. In Minecraft 1.16,
`dynmap` breaks if you issue `/dynmap reload`, so directly updating the `markers.yml`
file and reloading it is out of the question.

To ensure that map files are up-to-date on disk, the script issues a `/save-all`
command and then waits a few seconds before reading map files.


## Usage

```
Usage: mapmarkers.py <server> <world> <maps-dir> <markers-file> <marker-set>

Add dynmap markers in the specified world for all Minecraft maps in that world.
Markers are named after the map number. They are created by issuing console
commands with "mark2 send -n <server>".

<maps-dir> is the path to the directory containing "map_<n>.dat" files, e.g.
"/servers/pve/worlds/world/data".

<markers-file> is the path to the dynmap markers configuration file, e.g.
"/servers/pve/plugins/dynmap/markers.yml".

<marker-set> is the name of the set of markers to update, e.g. "markers".
```


## Configuration

The script should be configured to run every few minutes. The easiest way to
do this is with the `mark2` scheduling facility, `scripts.txt`:

```
# scripts.txt

*/5     *    *    *    *    $python3 /home/minecraft/scripts/mapmarkers.py pve27 mapworld /servers/pve/worlds/world/data /servers/pve/plugins/dynmap/markers.yml markers
```


## Python Dependencies

To install library dependencies, run these commands:
```
pip3 install PyYAML
pip3 install nbtlib
```


## Bugs/Quirks

Intermittently, map markers will not appear for some map items placed in item frames.
This is because the corresponding `map_<n>.dat` file does not list the map as having
been placed in an item frame. This is a bug in Mojang or Spigot/Paper code.

To make the marker appear, pop the item out of the frame and place it again.
