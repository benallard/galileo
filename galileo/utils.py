"""\
We internally use array of int as data representation, those routines
translate them to one or the other format
"""

import sys

def a2x(a, delim=' '):
    """ array to string of hexa
    delim is the delimiter between the hexa
    """
    return delim.join('%02X' % x for x in a)


def x2a(hexstr):
    """ String of hexa to array """
    hexstr = hexstr.replace('\n', ' ').replace(':', ' ')
    return [int(x, 16) for x in hexstr.split(' ')]


def a2s(a, toPrint=True):
    """ array to string
    toPrint indicates that the resulting string is to be printed (stop at the
    first \0)
    """
    s = []
    for c in a:
        if toPrint and (c == 0):
            break
        s.append(chr(c))
    return ''.join(s)

def a2b(a):
    """ array to `bytes` """
    if sys.version_info > (3, 0):
        return bytes(a)
    return a2s(a, False)

def a2lsbi(array):
    """ array to int (LSB first) """
    integer = 0
    for i in range(len(array) - 1, -1, -1):
        integer *= 256
        integer += array[i]
    return integer


def a2msbi(array):
    """ array to int (MSB first) """
    integer = 0
    for i in range(len(array)):
        integer *= 256
        integer += array[i]
    return integer


def i2lsba(value, width):
    """ int to array (LSB first) """
    a = [0] * width
    for i in range(width):
        a[i] = (value >> (i*8)) & 0xff
    return a


def i2msba(value, width):
    """ int to bytearray (MSB first) """
    a = bytearray(width)
    for i in range(width):
        a[width - i - 1] = (value >> (i*8)) & 0xff
    return a

def s2a(s):
    """ string to array """
    if isinstance(s, str):
        return [ord(c) for c in s]
    return [c for c in s]
