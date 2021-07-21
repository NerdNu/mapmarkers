#!/usr/bin/env python3
#------------------------------------------------------------------------------
# pip3 install PyYAML
# pip3 install nbtlib

import glob
import os
import os.path
import re
import sys
import time
import yaml
import nbtlib

#------------------------------------------------------------------------------
# Some configuration that probably won't change.
# If DEBUG is True, mark2 will try to interpret the print statements, which is
# not desirable.

DEBUG = False
MARKER_Y = 64 # Y coordinate to create markers at

#------------------------------------------------------------------------------

def debug(*args):
    if DEBUG:
        print(*(['#'] + list(args)))

#------------------------------------------------------------------------------

def eprint(*args, **kwargs):
    '''
    Print to stderr.
    '''
    print(*args, file=sys.stderr, **kwargs)

#------------------------------------------------------------------------------

def error(*args, **kwargs):
    '''
    Print an error message beginning with ERROR: to stderr.
    '''
    eprint(*(['#ERROR:'] + list(args)), **kwargs)

#------------------------------------------------------------------------------

def warning(*args, **kwargs):
    '''
    Print a warning message beginning with WARNING: to stderr.
    '''
    eprint(*(['#WARNING:'] + list(args)), **kwargs)

#------------------------------------------------------------------------------

def usage():
    '''
    Print usage to standard error and exit with error status.
    '''
    eprint(f'''
#Usage: {sys.argv[0]} <server> <world> <maps-dir> <markers-file> <marker-set>

Add dynmap markers in the specified world for all Minecraft maps in that world.
Markers are named after the map number. They are created by issuing console
commands with "mark2 send -n <server>".

<maps-dir> is the path to the directory containing "map_<n>.dat" files, e.g.
"/servers/pve/worlds/world/data".

<markers-file> is the path to the dynmap markers configuration file, e.g.
"/servers/pve/plugins/dynmap/markers.yml".

<marker-set> is the name of the set of markers to update, e.g. "markers".
''')
    sys.exit(1)

#------------------------------------------------------------------------------

def loadMarkers(markersFileName, markerSet, world):
    '''
    Load the specified markers.yml file and return all markers in the specified
    marker set and world as a map from marker ID to dict.

    :param markersFileName: The path to "plugins/dynmap/markers.yml".
    :param markerSet: The set of markers (usually "markers").
    :param world: The world whose markers are updated.
    :returns a dict from marker ID to dict describing the marker.
    '''
    try:
        with open(markersFileName, 'r') as f:
            markers = yaml.safe_load(f)
    except IOError as e:
        error(f'cannot open markers file {markersFileName}" to read!')
        sys.exit(1)

    if 'sets' not in markers:
        error(f'"{markersFileName}" doesn\'t seem to be a markers file!')
        sys.exit(1)

    result = {}
    for id, marker in markers['sets'][markerSet]['markers'].items():
        # Only return markers in the specified world whose ID matches the label.
        if marker['world'] == world and marker['label'] == id:
            result[id] = marker
    return result

#------------------------------------------------------------------------------

def loadMaps(mapsDir, world):
    '''
    Load information about all Minecraft maps in the specified directory that
    show terrain in the specified world.

    :param mapsDir: The path to the directory containing "map_<n>.dat" files.
    :param world: The world whose maps will be updated as dynmap markers.
    :return: a dict from marker ID (string) to dict of marker x, z.
    '''

    # Use a map from stringified X:Z coordinates of map centre to ID to work
    # out the highest map ID for a given set of coords.
    highestMapID = {}

    # Use to track mapID -> dict for all maps, even those superceded by higher IDs.
    allMaps = {}
    pattern = f'.*/map_(\\d+).dat'
    for file in sorted(glob.glob(f'{mapsDir}/map_*.dat', recursive=False)):
        nbt = nbtlib.load(file)
        if nbt.root['data']['dimension'] == 'minecraft:' + world:
            match = re.match(pattern, file)
            mapID = int(match.group(1))
            scale = int(nbt.root['data']['scale'].real)

            # Ignore zoomed out maps.
            if scale == 0:
                x = int(nbt.root['data']['xCenter'].real)
                z = int(nbt.root['data']['zCenter'].real)
                allMaps[mapID] = {'x': x, 'z': z}

                coordsKey = f'{x}:{z}'
                #debug(f'{mapID} -> {coordsKey}')
                if coordsKey not in highestMapID or highestMapID[coordsKey] < mapID:
                    highestMapID[coordsKey] = mapID

    # Add the highest map ID at a given coordinate pair to the result.
    result = {}
    for coordsKey, mapID in highestMapID.items():
        result[str(mapID)] = allMaps[mapID]
    return result

#------------------------------------------------------------------------------

def serverCommand(server, command):
    '''
    Run the specified command in the specified server's console.

    Note that command should omit the leading '/'.

    :param server: The mark2 name of the server to run the command, e.g. "pve27".
    :param command: The command, with the leading '/' omitted.
    '''
    os.system(f'mark2 send -n {server} {command}')

#------------------------------------------------------------------------------

def deleteMarker(server, id):
    '''
    Send the /dmarker command to the server to delete the specified marker ID.
    :param server: The mark2 server name, e.g. "pve27".
    :param id: The marker ID string.
    '''
    command = f'dmarker delete id:{id}'
    debug(command)
    serverCommand(server, command)

#------------------------------------------------------------------------------

def addMarker(server, id, markerSet, world, x, y, z):
    '''
    Send the /dmarker command to the server to add a new marker for the specified
    world and coordinates.

    The marker's label is set to match its ID.

    Note that to update the position of a marker, it is necessary to delete it
    and re-create it with "/dmarker add". There is no "/dmarker update" variant
    that accepts coordinates.

    :param server: The mark2 server name, e.g. "pve27".
    :param id: The marker's ID and label as a string.
    :param markerSet: The set to which the marker is added; usually "markers".
    :param world: The name of the world containing the marker.
    :param x: The X coordinate.
    :param y: The Y coordinate.
    :param z: The Z coordinate.
    '''
    command = f'dmarker add id:{id} {id} icon:pin set:{markerSet} x:{x} y:{y} z:{z} world:{world}'
    debug(command)
    serverCommand(server, command)

#------------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) != 6:
        usage()

    # <server> <world> <maps-dir> <markers-file> <marker-set>
    _, server, world, mapsDir, markersFileName, markerSet = sys.argv

    if not os.path.isfile(markersFileName):
        error(f'"{markersFileName}" doesn\'t exist!')
        sys.exit(1)

    if not os.path.isdir(mapsDir):
        error(f'"{mapsDir}" is not a directory!')
        sys.exit(1)

    # The server must save all files so that new map files hit the disk.
    serverCommand(server, 'save-all')
    time.sleep(5)
    maps = loadMaps(mapsDir, world)

    markers = loadMarkers(markersFileName, markerSet, world)

    #for id in sorted(markers.keys()):
    #    marker = markers[id]
    #    debug(f"{id} -> {marker['x']} {marker['y']} {marker['z']}")

    # Delete unused markers.
    debug('DELETING UNUSED MARKERS')
    for mapID in markers.keys():
        if mapID not in maps.keys():
            deleteMarker(server, mapID)

    # Update markers according to current maps.
    debug('UPDATING MARKERS')
    for mapID, mapData in maps.items():
        if mapID in markers.keys():
            # Update markers that don't exactly match.
            if mapData['x'] != int(markers[mapID]['x']) or MARKER_Y != int(markers[mapID]['y']) or mapData['z'] != int(markers[mapID]['z']):
                deleteMarker(server, mapID)
                addMarker(server, mapID, markerSet, world, mapData['x'], MARKER_Y, mapData['z'])
        else:
            # Create markers where they don't yet exist.
            addMarker(server, mapID, markerSet, world, mapData['x'], MARKER_Y, mapData['z'])
