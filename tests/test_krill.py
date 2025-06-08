import pytest

from unittest import mock
from krill.krill import Application, fix_html
import builtins

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
class TestFixLinks:
    async def test_fix_http(self):
        test_str = "This is a link.http://twitter.com"

        expected = "This is a link. http://twitter.com"
        actual = await fix_html(test_str)

        assert expected == actual

    async def test_http_start_of_line(self):
        test_str = "http://twitter.com"

        expected = "http://twitter.com"
        actual = await fix_html(test_str)

        assert expected == actual

    async def test_https_start_of_line(self):
        test_str = "https://twitter.com"

        expected = "https://twitter.com"
        actual = await fix_html(test_str)

        assert expected == actual

    async def test_fix_https(self):
        test_str = "This is a link.https://twitter.com"

        expected = "This is a link. https://twitter.com"
        actual = await fix_html(test_str)

        assert expected == actual

    async def test_fix_link(self):
        test_str = "This is a link.pic.twitter.com"
        expected = "This is a link. pic.twitter.com"
        actual = await fix_html(test_str)

        assert expected == actual

    async def test_link_start_of_line(self):
        test_str = "pic.twitter.com"

        expected = "pic.twitter.com"
        actual = await fix_html(test_str)

        assert expected == actual


@pytest.mark.asyncio
class TestReadSourceFile:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.mock_readlines_sources = [
            "https://twitter.com/hashtag/programming python",
            "http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml bailout",
            "# I'm a commented line!",
        ]
        self.mock_readlines_filters = [
            "# This is a comment",
            "python",
            "programming",
            "esm bailout",
            "new horizons",
        ]
        self.mock_myfile = mock.MagicMock()
        self.args = mock.MagicMock()
        self.application = Application(self.args)

    @mock.patch.object(builtins, "open")
    async def test_read_filters_file(self, mock_open):
        self.mock_myfile.readlines.return_value = self.mock_readlines_filters
        mock_open.return_value.__enter__.return_value = self.mock_myfile
        actual = await self.application._read_filters_file("test")
        expected = ["python", "programming", "esm bailout", "new horizons"]
        assert expected == actual

    @mock.patch.object(builtins, "open")
    async def test_read_source_file(self, mock_open):
        self.mock_myfile.readlines.return_value = self.mock_readlines_sources
        mock_open.return_value.__enter__.return_value = self.mock_myfile
        actual = await self.application._read_sources_file("filename")
        expected = {
            "https://twitter.com/hashtag/programming": "python",
            "http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml": "bailout",
        }
        assert expected == actual
