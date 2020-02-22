#
# 17/02/2019 
# Juan M. Casillas <juanm.casillas@gmail.com>
# https://github.com/juanmcasillas/gopro2gpx.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
#

# based on the info from:
#   https://github.com/gopro/gpmf-parser
#   https://docs.python.org/3/library/struct.html
#   https://github.com/stilldavid/gopro-utils/blob/master/telemetry/reader.go


import os
import array
import sys
import struct

from ffmpegtools import FFMpegTools
from klvdata import KLVData

       

class Parser:
    def __init__(self, config):
        self.config = config
        self.ffmtools = FFMpegTools(self.config)

        # map some handy shortcuts
        self.verbose = config.verbose

    
    def readFrom(self, input_file, is_video):
        """
        Read the metadata track from video/metadata file. Requires FFMPEG wrapper when is_video
        is True.
        -vv creates a dump file with the binary metadata called <input_file>.meta.bin
        """
        
        if not os.path.exists(input_file):
            raise FileNotFoundError("Can't open %s" % input_file)

        if is_video:
            track_number, lineinfo = self.ffmtools.getMetadataTrack(input_file)
            if not track_number:
                raise Exception("File %s doesn't have any metadata" % input_file)

            if self.verbose:
                print("Working on file %s track %s (%s)" % (input_file, track_number, lineinfo))

            metadata_raw = self.ffmtools.getMetadata(track_number, input_file)
        else:
            if self.verbose:
                print("Reading metadata binary file %s" % input_file)

            fd = open(input_file, 'rb')
            metadata_raw = fd.read()
            fd.close()

        if self.verbose == 2:
            dump_file = "%s.meta.bin" % input_file
            print("Creating output file for binary metadata: %s" % dump_file)
            f = open(dump_file, "wb")
            f.write(metadata_raw)
            f.close() 
        
        # process the data here
        metadata = self.parseStream(metadata_raw)
        return(metadata)

    def parseStream(self, data_raw):
        """
        main code that reads the points
        """
        data = array.array('b')
        data.fromstring(data_raw)

        offset = 0
        klvlist = []

        while offset < len(data):
            
            klv = KLVData(data,offset)
            if not klv.skip():
                klvlist.append(klv)
                if self.verbose == 3:
                    print(klv)
            offset += 8
            if klv.type != 0:
                offset += klv.padded_length
                #print(">offset:%d length:%d padded:%d" % (offset, length, padded_length))
            
        return(klvlist)
    


            