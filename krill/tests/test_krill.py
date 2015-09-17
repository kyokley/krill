import unittest
import mock
from krill.krill import Application

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

    @mock.patch('krill.krill.open')
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

    @mock.patch('krill.krill.open')
    def test_read_source_file(self, mock_open):
        self.mock_myfile.readlines.return_value = self.mock_readlines_sources
        mock_open.return_value.__enter__.return_value = self.mock_myfile
        actual = self.application._read_sources_file('filename')
        expected = {
                'https://twitter.com/hashtag/programming': 'python',
                'http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml': 'bailout',
                }
        self.assertEqual(actual, expected)
