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

    def testdedent1(self):
        self.assertEquals(parser._dedent("""\
a:
  - a
  - b
""".split('\n'), 1), ['  - a', '  - b'])
    def testdedent2(self):
        self.assertEquals(parser._dedent("""\
-
  a:
    b
  c:
    5
""".split('\n'), 1), ['  a:', '    b', '  c:', '    5'])

class testload(unittest.TestCase):

    def testEmpty(self):
        self.assertEquals(parser.loads(""), None)

    def testSimpleComment(self):
        self.assertEquals(parser.loads("""\
# This is a comment
"""), None)

    def testOneKey(self):
        self.assertEquals(parser.loads("""\
test:
"""), {"test":None})

    def testOneKeyWithComment(self):
        self.assertEquals(parser.loads("""\
test: # This is the test Key
"""), {"test": None})

    def testMultiLines(self):
        self.assertEquals(parser.loads("\n"*5 + "test: # This is the test Key" + "\n" * 8), {"test": None})

    def testMultipleKeys(self):
        self.assertEquals(parser.loads("""
test:
test_2:
test-3:
"""), {"test": None, 'test_2': None, 'test-3': None})

    def testOnlyOneValue(self):
        self.assertEquals(parser.loads('5'), 5)
        self.assertEquals(parser.loads('a'), 'a')
        self.assertEquals(parser.loads('true'), True)

    def testOneArray(self):
        self.assertEquals(parser.loads('- a\n- b'), ['a', 'b'])

    def testIntegerValue(self):
        self.assertEquals(parser.loads("t: 5"), {'t': 5})
    def testSimpleStringValue(self):
        self.assertEquals(parser.loads('t: abcd'), {'t': 'abcd'})
    def testStringValue(self):
        self.assertEquals(parser.loads("t: '5'"), {'t': '5'})
    def testOtherStringValue(self):
        self.assertEquals(parser.loads('t: "5"'), {'t': '5'})
    def testBoolValue(self):
        self.assertEquals(parser.loads("t: false"), {'t': False})
    def testInlineArrayValue(self):
        self.assertEquals(parser.loads("t: [4, 6]"), {'t': [4, 6]})
    def testArrayValue(self):
        self.assertEquals(parser.loads("""
test:
  - a
  - 5
"""), {'test': ['a', 5]})

    def testDoubleDict(self):
        self.assertEquals(parser.loads("""\
a:
  b: c
"""), {'a': {'b': 'c'}})
    def testDoubleDict2(self):
        self.assertEquals(parser.loads("""\
a:
  b:
    c
"""), {'a': {'b': 'c'}})

    def testMultiArray(self):
        self.assertEquals(parser.loads("""\
-
  -
    a:
      b
    c:
      5
  -
    a:
      8
"""), [[{'a':'b', 'c': 5}, {'a': 8}]])

    def testArrayOfDict(self):
        self.assertEquals(parser.loads("""\
- a: b
"""), [{'a':'b'}])
