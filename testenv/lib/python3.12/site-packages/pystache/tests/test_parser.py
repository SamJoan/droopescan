# coding: utf-8

"""
Unit tests of parser.py.

"""

import unittest

from pystache.defaults import DELIMITERS
from pystache.parser import _compile_template_re as make_re, parse, ParsingError


class RegularExpressionTestCase(unittest.TestCase):
    """Tests the regular expression returned by _compile_template_re()."""

    def test_re(self):
        """
        Test getting a key from a dictionary.
        """
        re = make_re(DELIMITERS)
        match = re.search("b  {{test}}")

        self.assertEqual(match.start(), 1)


class ParseTestCase(unittest.TestCase):
    """Tests the parse() function."""

    def test_parse_okay(self):
        """
        Test parsing templates in the cases there are no errors.
        """
        ts = [
            '<div>{{>A}}</div>',
            '{{#A}}<div> some text</div>',
            '{{^A}}<div> some text</div>{{/A}}',
            '{{#A}} {{^B}} {{/B}} {{/A}}',
            '{{#A}} {{^B}} {{/B}} {{/A}} {{#C}} {{/C}}',
        ]
        for t in ts:
            with self.subTest(template=t):
                parse(t)

    def test_parse_fail(self):
        """
        Test parsing templates in the cases there are errors.
        """
        ts = [
            '{{#A}}<div> some text</div>',
            '{{#A}}<div> some text</div>{{/A}} <div> TEXT </div> {{/B}}',
            '{{#A}} {{#B}} {{/A}} {{/B}}',
        ]
        for t in ts:
            with self.subTest(template=t):
                with self.assertRaises(ParsingError) as e:
                    parse(t, raise_on_mismatch=True)
                self.assertTrue('Did not find a matching tag', str(e))
