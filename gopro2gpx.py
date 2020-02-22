#!/usr/bin/env python3
#
# 17/02/2019 
# Juan M. Casillas <juanm.casillas@gmail.com>
# https://github.com/juanmcasillas/gopro2gpx.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
#


import subprocess
import re
import struct
import os
import platform
import argparse
from collections import namedtuple
import array
import sys
import time

from datetime import datetime, timedelta

import config
import gpmf
import fourCC
import time
import sys

import gpshelper

def BuildGPSPoints(data, skip=False):
    """
    Data comes UNSCALED so we have to do: Data / Scale.
    Do a finite state machine to process the labels.
    GET
     - SCAL     Scale value
     - GPSF     GPS Fix
     - GPSU     GPS Time
     - GPS5     GPS Data
    """

    points = []
    SCAL = fourCC.XYZData(1.0, 1.0, 1.0)
    GPSU = None    
    SYST = fourCC.SYSTData(0, 0)

    stats = { 
        'ok': 0,
        'badfix': 0,
        'badfixskip': 0,
        'empty' : 0
    }

    GPSFIX = 0 # no lock.
    for d in data:
        if d.fourCC == 'SCAL':
            SCAL = d.data
        elif d.fourCC == 'GPSU':
            GPSU = d.data
        elif d.fourCC == 'GPSF':
            if d.data != GPSFIX:
                print("GPSFIX change to %s [%s]" % (d.data,fourCC.LabelGPSF.xlate[d.data]))
            GPSFIX = d.data
        elif d.fourCC == 'GPS5':
            if d.data.lon == d.data.lat == d.data.alt == 0:
                print("Warning: Skipping empty point")
                stats['empty'] += 1
                continue

            if GPSFIX == 0:
                stats['badfix'] += 1
                if skip:
                    print("Warning: Skipping point due GPSFIX==0")
                    stats['badfixskip'] += 1
                    continue                    

            data = [ float(x) / float(y) for x,y in zip( d.data._asdict().values() ,list(SCAL) ) ]
            gpsdata = fourCC.GPSData._make(data)
            p = gpshelper.GPSPoint(gpsdata.lat, gpsdata.lon, gpsdata.alt,
                                   datetime.fromtimestamp(time.mktime(GPSU)),
                                   gpsdata.speed)
            points.append(p)
            stats['ok'] += 1

        elif d.fourCC == 'SYST':
            data = [ float(x) / float(y) for x,y in zip( d.data._asdict().values() ,list(SCAL) ) ]
            if data[0] != 0 and data[1] != 0:
                SYST = fourCC.SYSTData._make(data)


        elif d.fourCC == 'GPRI':
            # KARMA GPRI info

            if d.data.lon == d.data.lat == d.data.alt == 0:
                print("Warning: Skipping empty point")
                stats['empty'] += 1
                continue

            if GPSFIX == 0:
                stats['badfix'] += 1
                if skip:
                    print("Warning: Skipping point due GPSFIX==0")
                    stats['badfixskip'] += 1
                    continue
                    
            data = [ float(x) / float(y) for x,y in zip( d.data._asdict().values() ,list(SCAL) ) ]
            gpsdata = fourCC.KARMAGPSData._make(data)
            
            if SYST.seconds != 0 and SYST.miliseconds != 0:
                p = gpshelper.GPSPoint(gpsdata.lat, gpsdata.lon, gpsdata.alt, datetime.fromtimestamp(SYST.miliseconds), gpsdata.speed)
                points.append(p)
                stats['ok'] += 1
                        

 

    print("-- stats -----------------")
    total_points =0
    for i in stats.keys():
        total_points += stats[i]
    print("- Ok:              %5d" % stats['ok'])
    print("- GPSFIX=0 (bad):  %5d (skipped: %d)" % (stats['badfix'], stats['badfixskip']))
    print("- Empty (No data): %5d" % stats['empty'])
    print("Total points:      %5d" % total_points)
    print("--------------------------")
    return(points)

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="count")
    parser.add_argument("-b", "--binary", help="read data from bin file", action="store_true")
    parser.add_argument("-s", "--skip", help="Skip bad points (GPSFIX=0)", action="store_true", default=False)
    parser.add_argument("file", nargs="+", help="Video file(s) or binary metadata dump(s)")
    parser.add_argument("outputfile", help="output file. builds KML and GPX")
    args = parser.parse_args()

    return args        

if __name__ == "__main__":

    args = parseArgs()
    config = config.setup_environment(args)
    parser = gpmf.Parser(config)

    total_duration = timedelta(0)
    output_append_timestamp = None
    total_points = []
    for file in args.file:
        data = parser.readFrom(file, not args.binary)

        # build some funky tracks from camera GPS
        print(args.skip)
        points = BuildGPSPoints(data, skip=args.skip)

        if len(points) == 0:
            print("No GPS info in %s." % file)
            continue

        if args.binary:
            file_start_timestamp = points[0].time
            file_end_timestamp = points[len(points) - 1].time
        else:
            (file_start_timestamp, file_end_timestamp) = parser.ffmtools.get_video_time_range(file)

        if not output_append_timestamp:
            output_append_timestamp = file_start_timestamp

        # Shift time of current file to start at output_append_timestamp.
        for point in points:
            point.time -= (file_start_timestamp - output_append_timestamp)

        total_points += points

        file_duration = file_end_timestamp - file_start_timestamp
        output_append_timestamp += file_duration
        total_duration += file_duration

    if len(total_points) == 0:
        print("Can't create file. No GPS info in input files. Exitting")
        sys.exit(0)

    kml = gpshelper.generate_KML(total_points)
    fd = open("%s.kml" % args.outputfile , "w+")
    fd.write(kml)
    fd.close()

    gpx = gpshelper.generate_GPX(total_points, trk_name="gopro-track-%s" % args.outputfile)
    fd = open("%s.gpx" % args.outputfile , "w+")
    fd.write(gpx)
    fd.close()

    print("Total duration: ", total_duration)
   
   # falla el 46 y el 48
