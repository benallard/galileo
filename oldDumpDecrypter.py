import argparse
import os

from galileo.databases.local import LocalDatabase, UnknownDumpTypeError
from galileo.dump import Dump, DumpResponse, MEGADUMP
from galileo.utils import x2a
from galileo.megadumpDecrypter import decrypt

def main():
    parser = argparse.ArgumentParser(description='Decrypt dumps collected earlier')
    parser.add_argument('trackerId')
    args = parser.parse_args()

    dumpDir = '~/.galileo'

    db = LocalDatabase(dumpDir)

    trackerId = args.trackerId
    trackerDumpDir = db.getDeviceDirectoryName(trackerId)
    key = db.loadKey(trackerId)

    files  = os.listdir(trackerDumpDir)
    files = [x for x in files if not 'dec' in x]
    for filename in files:
        dumpname = os.path.join(trackerDumpDir, filename)
        file = open(dumpname)

        data = file.read()

        pieces = data.split('\n\n')

        responsePresent = len(pieces)==2
        if responsePresent:
            [megadumpData, megadumpResponseData] = pieces
        else:
            [megadumpData] = pieces

        megadump = Dump(MEGADUMP)
        megadump.data = bytearray(x2a(megadumpData))
        megadump.megadump()

        try:
            decrypt(megadump, key)
        except UnknownDumpTypeError:
                print('Encountered an UnknownDumpTypeError in the dump of file: '+ filename)
        megadump.toFile(dumpname.replace('.txt','_dec.txt'))

        if responsePresent:
            CHUNK_LEN = 20
            megadumpResponse = DumpResponse(x2a(megadumpResponseData), CHUNK_LEN)

            megadumpResponse.megadump()
            try:
                decrypt(megadumpResponse, key, offset=10)
            except UnknownDumpTypeError:
                print('Encountered an UnknownDumpTypeError in the responsedump of file: '+ filename)
            megadumpResponse.toFile(dumpname.replace('.txt','_resp_dec.txt'))


if __name__ == "__main__":
    #execute only when if run as a script
    main()
