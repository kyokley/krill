import re
import warnings
from collections import namedtuple
from itertools import chain
from urllib.parse import urlparse

from dateutil import parser as dt_parser
from datetime import datetime
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from krill.utils import validate_timestamp


warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


_link_regex = re.compile(r"(?<=\S)(https?://|pics?.(x|twitter).com)")

StreamItem = namedtuple("StreamItem", ["source", "time", "title", "text", "link"])


async def fix_html(text):
    return _link_regex.sub(r" \1", text)


async def extract_link(link):
    match = re.search(r'https?://[^\s"]*', str(link))
    return match and match.group()


class StreamParser:
    @staticmethod
    async def _html_to_text(html):
        # Hack to prevent Beautiful Soup from collapsing space-keeping tags
        # until no whitespace remains at all
        html = re.sub(r"<(br|p|li)", " \\g<0>", html, flags=re.IGNORECASE)
        text = BeautifulSoup(html, "html.parser").get_text()
        # Idea from http://stackoverflow.com/a/1546251
        return " ".join(text.strip().split())

    @classmethod
    async def get_tweets(cls, html):
        document = BeautifulSoup(html, "html.parser")

        for tweet in document.find_all("p", class_="tweet-text"):
            header = tweet.find_previous("div", class_="stream-item-header")

            name = header.find("strong", class_="fullname").string
            username = header.find("span", class_="username").b.string

            time_string = header.find("span", class_="_timestamp")["data-time"]
            timestamp = datetime.fromtimestamp(int(time_string))

            if not validate_timestamp(timestamp):
                continue

            # Remove ellipsis characters added by Twitter
            text = await cls._html_to_text(str(tweet).replace("\u2026", " "))

            tweet_href = header.find("a", class_="tweet-timestamp")["href"]
            link = f"https://x.com{tweet_href}"

            yield StreamItem(
                (f"{name} (@{username})" if name else "@{username}"),
                timestamp,
                None,
                await fix_html(text),
                link,
            )

    @classmethod
    async def _parse_feed(cls, xml):
        soup = BeautifulSoup(xml, "xml")
        found = False
        for entry in chain(soup.find_all("entry"), soup.find_all("item")):
            yield entry
            found = True

        if not found:
            raise Exception("Failed to find entries")

    @classmethod
    def _feed_item_date(cls, item):
        if stripped := (item.date and item.date.text.strip()):
            date_str = stripped
        elif stripped := (item.published and item.published.text.strip()):
            date_str = stripped
        elif stripped := (item.pubDate and item.pubDate.text.strip()):
            date_str = stripped
        else:
            return None

        timestamp = dt_parser.parse(date_str)
        return timestamp

    @classmethod
    async def get_feed_items(cls, xml, url):
        feed_title = urlparse(url).netloc

        async for entry in cls._parse_feed(xml):
            timestamp = cls._feed_item_date(entry)

            if not validate_timestamp(timestamp):
                continue

            title = entry.title.text.strip()
            description = (
                entry.description and entry.description.text.strip()
            ) or entry.text.strip()
            text = await cls._html_to_text(description)

            link = (entry.link and entry.link.text.strip()) or str(entry.link)
            link = await extract_link(link)

            # Some feeds put the text in the title element
            if text is None and title is not None:
                text = title
                title = None

            # At least one element must contain text for the item to be useful
            if title or text or link:
                yield StreamItem(
                    feed_title, timestamp, title, await fix_html(text), link
                )


class TextExcerpter:
    # Clips the text to the position succeeding the first whitespace string
    @staticmethod
    async def _clip_left(text):
        return re.sub(r"^\S*\s*", "", text, 1)

    # Clips the text to the position preceding the last whitespace string
    @staticmethod
    async def _clip_right(text):
        return re.sub(r"\s*\S*$", "", text, 1)

    @staticmethod
    async def _get_max_pattern_span(text, patterns):
        min_start, max_end = None, None
        if patterns is not None:
            for pattern in patterns:
                if isinstance(pattern, str):
                    regex = re.compile(pattern)
                else:
                    regex = pattern

                if match := regex.search(text):
                    start, end = match.span()
                    if min_start is None:
                        min_start = start
                    else:
                        min_start = min(min_start, start)
                    if max_end is None:
                        max_end = end
                    else:
                        max_end = max(max_end, end)

        return min_start, max_end

    # Returns a portion of text at most max_length in length
    # and containing the first match of pattern, if specified
    @classmethod
    async def get_excerpt(cls, text, max_length, patterns=None):
        if len(text) <= max_length or True:
            return text, False, False

        start, end = await cls._get_max_pattern_span(text, patterns)
        if start is None and end is None:
            return await cls._clip_right(text[:max_length]), False, True
        else:
            remaining_length = max_length - (end - start)
            if remaining_length <= 0:
                # Matches are never clipped
                return text[start:end], False, False

            excerpt_start = max(start - (remaining_length // 2), 0)
            excerpt_end = min(
                end + (remaining_length - (start - excerpt_start)), len(text)
            )
            # Adjust start of excerpt in case the string after the match was too short
            excerpt_start = max(excerpt_end - max_length, 0)
            excerpt = text[excerpt_start:excerpt_end]
            if excerpt_start > 0:
                excerpt = await cls._clip_left(excerpt)
            if excerpt_end < len(text):
                excerpt = await cls._clip_right(excerpt)

            return excerpt, excerpt_start > 0, excerpt_end < len(text)
