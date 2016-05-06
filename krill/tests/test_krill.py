import unittest
import mock
from krill.krill import Application, fix_html

from sys import version_info
if version_info.major == 2:
    import __builtin__ as builtins
else:
    import builtins

class TestFixLinks(unittest.TestCase):
    def test_fix_http(self):
        test_str = 'This is a link.http://twitter.com'

        expected = 'This is a link. http://twitter.com'
        actual = fix_html(test_str)

        self.assertEqual(expected, actual)

    def test_fix_https(self):
        test_str = 'This is a link.https://twitter.com'

        expected = 'This is a link. https://twitter.com'
        actual = fix_html(test_str)

        self.assertEqual(expected, actual)

    def test_fix_link(self):
        test_str = 'This is a link.pic.twitter.com'
        expected = 'This is a link. pic.twitter.com'
        actual = fix_html(test_str)

        self.assertEqual(expected, actual)

class TestReadSourceFile(unittest.TestCase):
    def setUp(self):
        self.mock_readlines_sources = [
                'https://twitter.com/hashtag/programming python',
                'http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml bailout',
                "# I'm a commented line!",
                ]
        self.mock_readlines_filters = [
                '# This is a comment',
                'python',
                'programming',
                'esm bailout',
                'new horizons',
                ]
        self.mock_myfile = mock.MagicMock()
        self.args = mock.MagicMock()
        self.application = Application(self.args)

    @mock.patch.object(builtins, 'open')
    def test_read_filters_file(self,
                               mock_open,
                               ):
        self.mock_myfile.readlines.return_value = self.mock_readlines_filters
        mock_open.return_value.__enter__.return_value = self.mock_myfile
        actual = self.application._read_filters_file('test')
        expected = ['python',
                    'programming',
                    'esm bailout',
                    'new horizons',
                    ]
        self.assertEqual(actual, expected)

    @mock.patch.object(builtins, 'open')
    def test_read_source_file(self, mock_open):
        self.mock_myfile.readlines.return_value = self.mock_readlines_sources
        mock_open.return_value.__enter__.return_value = self.mock_myfile
        actual = self.application._read_sources_file('filename')
        expected = {
                'https://twitter.com/hashtag/programming': 'python',
                'http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml': 'bailout',
                }
        self.assertEqual(actual, expected)
