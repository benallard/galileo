import unittest

from galileo.utils import a2x, a2s, x2a
from galileo.xtea import xtea_encrypt, xtea_decrypt

class testXTEA(unittest.TestCase):
    def testEncrypt(self):
        z = xtea_encrypt(bytearray('0123456789012345', 'utf-8'), bytearray('ABCDEFGH', 'utf-8'))
        self.assertEqual(a2x(z), 'B6 7C 01 66 2F F6 96 4A')

    def testDecrypt(self):
        z = xtea_decrypt(bytearray('0123456789012345', 'utf-8'), bytearray(x2a('B6 7C 01 66 2F F6 96 4A')))
        self.assertEqual(a2s(z), 'ABCDEFGH')
