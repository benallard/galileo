#!/usr/bin/env python

import os
import sys
import time
import base64

def readlog(f):
    """ input is from stdin in the format of lines of long string starting
    with a tab ('\t') representing the hexadcimal representation of the data
    (megadump)"""
    d = []
    for line in f:
        if line[0] != '\t':
            if d:
                return d
            continue
        line = line.strip()
        for i in range(0, len(line), 2):
            d.append(int(line[i:i+2], 16))
    return d

def readdump(f):
    """ imput is from ./galileo.py """
    d = []
    r = []
    current = d
    for line in f:
        if line.strip() == '':
            current = r
            continue
        current.extend(int(x,16) for x in line.strip().split())
    return d, r

def a2s(array):
    """ array of int to string """
    return ''.join(chr(c) for c in array)

def a2x(array):
    """ array of int to hex representation """
    return ' '.join("%02X" % i for i in array)

def a2lsbi(array):
    """ array to int (LSB first) """
    integer = 0
    for i in range(len(array)-1, -1, -1):
        integer *= 256
        integer += array[i]
    #    print a2x(array), hex(integer)
    return integer

def a2msbi(array):
    """ array to int (MSB first) """
    integer = 0
    for i in range(len(array)):
        integer *= 256
        integer += array[i]
    return integer

def first_field(array, start):
    """ 'daily' is highly hypothetical """
    # first timestamp
    index = start
    while array[index] != 0xc0:
        tstamp = a2lsbi(array[index:index+4])
        print time.strftime("%x %X", time.localtime(tstamp)), hex(tstamp)
        index += 4
        print "\t%s" % a2x(array[index:index+11])
        index += 11
    return index

def minutely(array, start):
    """ this analyses the minute-by-minute information
    """
    index = start
    tstamp = 0
    while array[index] != 0xc0:
        if not (array[index] & 0x80):
            tstamp = a2msbi(array[index:index+4])
        else:
            if array[index] != 0x81:
                print '-',
                index += 1
            if array[index] != 0x81:
                print '--',
                index += 1
            print time.strftime("%x %X", time.localtime(tstamp)), a2x(array[index:index+4])
            tstamp += 60
        index += 4

    return index

def stairs(array, start):
    """ Looks like stairs informations are put here """
    index = start
    tstamp = 0
    while array[index] != 0xc0:
        if not (array[index] & 0x80):
            tstamp = a2msbi(array[index:index+4])
            index += 4
        else:
            if array[index] != 0x80:
                #print a2x([array[index]])
                index += 1
            print time.strftime("%x %X", time.localtime(tstamp)), a2x(array[index:index+2])
            tstamp += 60
            index += 2
    return index

def daily(array, start):
    index = start
    while array[index] != 0xc0:
        tstamp = a2lsbi(array[index:index+4])
        index += 4
        print time.strftime("%x %X", time.localtime(tstamp)), a2x(array[index:index + 12])
        index += 12
    return index

ESC = 0xdb
END = 0xc0
ESC_ = {0xdc: END, 0xdd: ESC}

def unSLIP(data):
    """ This remove SLIP escaping and yield the parts"""
    currentpart = -1 # -1 header, 0 body, 1 footer
    part = []
    escape = False
    for c in data:
#        print "%x" % c
        if not escape:
            if c == ESC:
                escape = True
            else:
                part.append(c)
                if c == END:
                    if len(part) > 1:
                        if (part[0] == END) or (currentpart == -1):
                            yield currentpart, part[1:-1]
                            part = []
                            if currentpart == -1:
                                currentpart = 0
                        else:
                            print "skipping", a2x(part[:-1])
                            part = [c]
        else:
            part.append(ESC_[c])
            escape = False
    yield 1, part

def analyse(data):


    for typ, part in unSLIP(data):
        print typ, len(part) #, a2x(part))

    return
    # empirical value
    index = 60

    # Greetings
    print "Greetings: '%s'" % a2s(data[index:index+10])
    index += 10

    # Cheering
    print "Cheering"
    for i in range(3):
        print "'%s'" % a2s(data[index:index+10])
        index += 10

    # 'C0' looks like a magical value there ...
    next_index = data.index(0xc0, index)
    print a2x(data[index:next_index])
    index = next_index

    assert(data[index:index+4] == [0xc0, 0xdb, 0xdc, 0xdd]), a2x(data[index:index+10])
    index += 4

    print "First field"
    index = first_field(data, index)

    assert(data[index:index+5] == [0xc0, 0xc0, 0xdb, 0xdc, 0xdd]), a2x(data[index:index+10])
    index += 5

    print "Second field"
    index = minutely(data, index)

    assert(data[index:index+5] == [0xc0, 0xc0, 0xdb, 0xdc, 0xdd]), a2x(data[index:index+10])
    index += 5

    print "Third field"
    index = stairs(data, index)

    assert(data[index:index+5] == [0xc0, 0xc0, 0xdb, 0xdc, 0xdd]), a2x(data[index:index+10])
    index += 5

    print "Fourth field"
    index = daily(data, index)

    print "Remainder"
    print a2x(data[index:])

def analysedump(dump_dir, index):
    for root, dirs, files in os.walk(dir):
        file = sorted(files)[idx]
        print "Analysing %s" % file
        with open(os.path.join(root, file)) as f:
            analyse(readdump(f))

if __name__ == "__main__":
    if len(sys.argv) == 1:
        analyse(sys.stdin)
    else:
        dir = sys.argv[1]
        idx = -1
        if len(sys.argv) > 2:
            idx = int(sys.argv[2])
        analysedump(dir, idx)
