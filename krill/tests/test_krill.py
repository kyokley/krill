import unittest
import mock
from krill.krill import Application

class TestReadSourceFile(unittest.TestCase):
    def setUp(self):
        self.mock_readlines = [
                'https://twitter.com/hashtag/programming python',
                'http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml bailout',
                "# I'm a commented line!",
                ]
        self.mock_myfile = mock.MagicMock()
        self.mock_myfile.readlines.return_value = self.mock_readlines
        self.application = Application(None)

    @mock.patch('krill.krill.open')
    def test_read_file(self,
                       mock_open):
        import pdb; pdb.set_trace()
        mock_open.return_value.__enter__.return_value = self.mock_myfile
        actual = self.application._read_file('test')
        pass
