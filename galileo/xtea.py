""" -- http://code.activestate.com/recipes/496737/
XTEA Block Encryption Algorithm

Author: Paul Chakravarti (paul_dot_chakravarti_at_gmail_dot_com)
License: Public Domain

This module provides a Python implementation of the XTEA block encryption
algorithm (http://www.cix.co.uk/~klockstone/xtea.pdf).

The module implements the basic XTEA block encryption algortithm
(`xtea_encrypt`/`xtea_decrypt`).

This module is intended to provide a simple 'privacy-grade' Python encryption
algorithm with no external dependencies. The implementation is relatively slow
and is best suited to small volumes of data. Note that the XTEA algorithm has
not been subjected to extensive analysis (though is believed to be relatively
secure - see http://en.wikipedia.org/wiki/XTEA). For applications requiring
'real' security please use a known and well tested algorithm/implementation.

The security of the algorithm is entirely based on quality (entropy) and
secrecy of the key. You should generate the key from a known random source and
exchange using a trusted mechanism. In addition, you should always use a random
IV to seed the key generator (the IV is not sensitive and does not need to be
exchanged securely)
"""

from .utils import i2msba, a2msbi

def xtea_encrypt(key, block, n=32):
    """
        Encrypt 64 bit data block using XTEA block cypher
        * key = 128 bit (16 char)
        * block = 64 bit (8 char)
        * n = rounds (default 32)
    """
    v0, v1 = a2msbi(block[:4]), a2msbi(block[4:])
    k = [a2msbi(key[:4]), a2msbi(key[4:8]), a2msbi(key[8:12]), a2msbi(key[12:])]
    sum, delta, mask = 0, 0x9e3779b9, 0xffffffff
    for round in range(n):
        v0 = (v0 + (((v1<<4 ^ v1>>5) + v1) ^ (sum + k[sum & 3]))) & mask
        sum = (sum + delta) & mask
        v1 = (v1 + (((v0<<4 ^ v0>>5) + v0) ^ (sum + k[sum>>11 & 3]))) & mask
    return i2msba(v0, 4) + i2msba(v1, 4)

def xtea_decrypt(key, block, n=32):
    """
        Decrypt 64 bit data block using XTEA block cypher
        * key = 128 bit (16 char)
        * block = 64 bit (8 char)
        * n = rounds (default 32
    """
    v0, v1 = a2msbi(block[:4]), a2msbi(block[4:])
    k = [a2msbi(key[:4]), a2msbi(key[4:8]), a2msbi(key[8:12]), a2msbi(key[12:])]
    delta, mask = 0x9e3779b9, 0xffffffff
    sum = (delta * n) & mask
    for round in range(n):
        v1 = (v1 - (((v0<<4 ^ v0>>5) + v0) ^ (sum + k[sum>>11 & 3]))) & mask
        sum = (sum - delta) & mask
        v0 = (v0 - (((v1<<4 ^ v1>>5) + v1) ^ (sum + k[sum & 3]))) & mask
    return i2msba(v0, 4) + i2msba(v1, 4)
