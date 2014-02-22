import unittest

from galileo import parser

class testUtilities(unittest.TestCase):

    def testStripCommentEmpty(self):
        self.assertEquals(parser._stripcomment(""), "")
    def testStripCommentOnlyComment(self):
        self.assertEquals(parser._stripcomment("# abcd"), "")
    def testStripCommentSmallLine(self):
        self.assertEquals(parser._stripcomment("ab # cd"), "ab")
    def testStripCommentDoubleComment(self):
        self.assertEquals(parser._stripcomment("ab # cd # ef"), "ab")

class testload(unittest.TestCase):

    def testEmpty(self):
        self.assertEquals(parser.load(""), None)

    def testSimpleComment(self):
        self.assertEquals(parser.load("""\
# This is a comment
"""), None)

    def testOneKey(self):
        self.assertEquals(parser.load("""\
test:
"""), {"test":None})

    def testOneKeyWithComment(self):
        self.assertEquals(parser.load("""\
test: # This is the test Key
"""), {"test": None})

    def testMultiLines(self):
        self.assertEquals(parser.load("\n"*5 + "test: # This is the test Key" + "\n" * 8), {"test": None})

    def testMultipleKeys(self):
        self.assertEquals(parser.load("""
test:
test_2:
test-3:
"""), {"test": None, 'test_2': None, 'test-3': None})

    def testIntegerValue(self):
        self.assertEquals(parser.load("t: 5"), {'t': 5})
    def testSimpleStringValue(self):
        self.assertEquals(parser.load('t: abcd'), {'t': 'abcd'})
    def testStringValue(self):
        self.assertEquals(parser.load("t: '5'"), {'t': '5'})
    def testOtherStringValue(self):
        self.assertEquals(parser.load('t: "5"'), {'t': '5'})
    def testBoolValue(self):
        self.assertEquals(parser.load("t: false"), {'t': False})
    def testInlineArrayValue(self):
        self.assertEquals(parser.load("t: [4, 6]"), {'t': [4, 6]})
    def testArrayValue(self):
        self.assertEquals(parser.load("""
test:
  - a
  - 5
"""), {'test': ['a', 5]})
