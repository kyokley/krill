#!/usr/bin/env python
# krill - the hacker's way of keeping up with the world
#
# Copyright (c) 2015 Philipp Emanuel Weidmann <pew@worldwidemann.com>
#
# Nemo vir est qui mundum non reddat meliorem.
#
# Released under the terms of the GNU General Public License, version 3
# (https://gnu.org/licenses/gpl.html)
from __future__ import unicode_literals

import asyncio
import httpx
import argparse
import calendar
import codecs
import random
import re
import sys
import warnings
from collections import namedtuple
from datetime import datetime

import feedparser
from blessings import Terminal
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from .lexer import filter_lex
from .parser import TokenParser

warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)

rand = random.SystemRandom()

base_type_speed = 0.01

REQUESTS_TIMEOUT = 5
NUM_WORKERS = 3

_invisible_codes = re.compile(
    r"^(\x1b\[\d*m|\x1b\[\d*\;\d*\;\d*m|\x1b\(B)"
)  # ANSI color codes
_link_regex = re.compile(r"(?<=\S)(https?://|pics?.twitter.com)")

StreamItem = namedtuple("StreamItem", ["source", "time", "title", "text", "link"])

HN_TOP_STORIES_URL = 'https://hacker-news.firebaseio.com/v0/topstories.json'
HN_NEW_STORIES_URL = 'https://hacker-news.firebaseio.com/v0/newstories.json'
HN_STORY_URL_TEMPLATE = 'https://hacker-news.firebaseio.com/v0/item/{}.json'
MIN_NUMBER_OF_HN_STORIES = 1
MAX_NUMBER_OF_HN_STORIES = 5


TERMINAL = Terminal()


class PromptTimeout(Exception):
    pass


class Quit(Exception):
    pass


async def fix_html(text):
    return _link_regex.sub(r' \1', text)


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

            # Remove ellipsis characters added by Twitter
            text = await cls._html_to_text(str(tweet).replace("\u2026", " "))

            tweet_href = header.find("a", class_="tweet-timestamp")["href"]
            link = f"https://twitter.com{tweet_href}"

            yield StreamItem(
                ("%s (@%s)" % (name, username) if name else "@%s" % (username,)),
                timestamp,
                None,
                await fix_html(text),
                link,
            )

    @classmethod
    async def get_feed_items(cls, xml, url):
        feed_data = feedparser.parse(xml)
        # Default to feed URL if no title element is present
        feed_title = feed_data.feed.get("title", url)

        for entry in feed_data.entries:
            timestamp = (
                datetime.fromtimestamp(calendar.timegm(entry.published_parsed))
                if "published_parsed" in entry and entry.published_parsed
                else None
            )
            title = entry.get("title")
            if 'description' in entry:
                text = await cls._html_to_text(entry.description)
            else:
                text = None

            link = entry.get("link")

            # Some feeds put the text in the title element
            if text is None and title is not None:
                text = title
                title = None

            # At least one element must contain text for the item to be useful
            if title or text or link:
                yield StreamItem(feed_title, timestamp, title, await fix_html(text), link)


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
                match = pattern.search(text)
                if match:
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
        if len(text) <= max_length:
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


class Application:
    def __init__(self, args):
        self.item_count = 0
        self._known_items = set()
        self.args = args
        if self.args.text_speed_ave.lower() == 'fast':
            self.text_speed_ave = 1
        elif self.args.text_speed_ave.lower() == 'slow':
            self.text_speed_ave = 10
        else:
            speed = int(self.args.text_speed_ave)
            if speed < 0 or speed > 10:
                raise ValueError('Speed is invalid. Got %s' % speed)
            self.text_speed_ave = speed

        self.clear()

    async def populate_sources(self):
        self.sources = []
        global_patterns = await self._global_patterns()
        for source, source_patterns in (await self._sources()).items():
            re_funcs = []
            if source_patterns:
                tokens = filter_lex(source_patterns)
                parser = TokenParser(tokens)
                re_funcs = [parser.buildFunc()]
            else:
                re_funcs = global_patterns
            self.sources.append((source, re_funcs))


    def clear(self):
        self.items = list()
        self._queue = asyncio.Queue()
        self._items_queue = asyncio.Queue()
        self._output_queue = asyncio.Queue()
        self._links = dict()

    async def add_item(self, item, patterns=None):
        item_id = (item.source, item.link)
        if item_id in self._known_items:
            # Do not print an item more than once
            return
        self._known_items.add(item_id)
        self._output_queue.put_nowait((item, patterns))

    def text_speed(self, interval_ave):
        if interval_ave == 0:
            return 0
        else:
            val = base_type_speed * (interval_ave + rand.normalvariate(0, 3.5))
            if val <= 0:
                return base_type_speed * interval_ave
            return val

    @staticmethod
    async def _print_error(error):
        print()
        print(TERMINAL.red(error))

    @classmethod
    async def _hn_story_ids(cls, url, cb=None):
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, timeout=REQUESTS_TIMEOUT)
            story_ids = resp.json()
        except Exception as e:
            await cls._print_error(str(e))
            story_ids = []

        if cb and story_ids:
            cb(story_ids)
        return story_ids

    @classmethod
    async def hn_stories_generator(cls):
        story_ids = set()

        def extend_story_ids(ids):
            story_ids.update(ids)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(cls._hn_story_ids(HN_TOP_STORIES_URL, cb=extend_story_ids))
            tg.create_task(cls._hn_story_ids(HN_NEW_STORIES_URL, cb=extend_story_ids))

        story_ids = list(story_ids)

        rand.shuffle(story_ids)

        number_of_stories = len(story_ids)
        if not number_of_stories:
            yield ()

        number_of_stories = rand.randint(
            min(MIN_NUMBER_OF_HN_STORIES, number_of_stories),
            min(MAX_NUMBER_OF_HN_STORIES, number_of_stories),
        )

        for story_id in story_ids[:number_of_stories]:
            try:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    resp = await client.get(HN_STORY_URL_TEMPLATE.format(story_id),
                                            timeout=REQUESTS_TIMEOUT)
            except Exception as e:
                await cls._print_error('Error getting HackerNews stories')
                await cls._print_error(str(e))
                break
            story = resp.json()
            if not story:
                continue
            story_time = story.get('time')

            if story.get('url'):
                yield StreamItem(
                    story.get('by', ''),
                    datetime.fromtimestamp(story_time) if story_time else '',
                    story.get('title', ''),
                    story.get('text', '').replace('<p>', '\n'),
                    story.get('url', ''),
                )

    @classmethod
    async def _read_sources_file(cls, filename):
        output = dict()
        lines = await cls._read_lines(filename)
        for line in lines:
            data = line.partition(' ')
            if data[1] and data[2]:
                output[data[0]] = data[2]
            else:
                output[data[0]] = list()
        return output

    @classmethod
    async def _read_lines(cls, filename):
        try:
            with open(filename, "r") as myfile:
                lines = [line.strip() for line in myfile.readlines()]
        except Exception as error:
            await cls._print_error("Unable to read file '%s': %s" % (filename, str(error)))
            sys.exit(1)

        # Discard empty lines and comments
        return [line for line in lines if line and not line.startswith("#")]

    _read_filters_file = _read_lines

    # Extracts feed URLs from an OPML file (https://en.wikipedia.org/wiki/OPML)
    @classmethod
    async def _read_opml_file(cls, filename):
        try:
            with open(filename, "r") as myfile:
                opml = myfile.read()
        except Exception as error:
            await cls._print_error("Unable to read file '%s': %s" % (filename, str(error)))
            sys.exit(1)

        return [
            match.group(2).strip()
            for match in re.finditer(
                r"""xmlUrl\s*=\s*(["'])(.*?)\1""", opml, flags=re.IGNORECASE
            )
        ]

    @staticmethod
    async def _highlight_pattern(text, patterns, pattern_style, text_style=None):
        if patterns is None:
            return text if text_style is None else text_style(text)
        if text_style is None:
            for pattern in patterns:
                text = pattern.sub(pattern_style("\\g<0>"), text)
            return text
        for pattern in patterns:
            text = text_style(pattern.sub(pattern_style("\\g<0>") + text_style, text))
        return text

    async def _queue_item(self, item, patterns=None):
        self.item_count += 1

        if not self.args.snapshot:
            self._queue.put_nowait("")
        else:
            snapshot_item = dict()

        time_label = (
            " on %s at %s"
            % (
                TERMINAL.yellow(item.time.strftime("%a, %d %b %Y")),
                TERMINAL.yellow(item.time.strftime("%H:%M")),
            )
            if item.time is not None
            else ""
        )

        if not self.args.snapshot:
            self._queue.put_nowait(
                "%s. %s%s:" % (self.item_count, TERMINAL.cyan(item.source), time_label)
            )

        indent = ' ' * (len(str(self.item_count)) + 2)

        if item.title is not None:
            if not self.args.snapshot:
                self._queue.put_nowait(
                    "%s%s"
                    % (
                        indent,
                        await self._highlight_pattern(
                            item.title,
                            patterns,
                            TERMINAL.bold_black_on_bright_yellow,
                            TERMINAL.bold,
                        ),
                    )
                )
            else:
                snapshot_item['title'] = item.title

        if item.text is not None and not self.args.snapshot:
            (excerpt, clipped_left, clipped_right) = await TextExcerpter.get_excerpt(
                item.text, 300, patterns
            )

            # Hashtag or mention
            excerpt = re.sub(
                r"(?<!\w)([#@])(\w+)",
                TERMINAL.green("\\g<1>") + TERMINAL.green("\\g<2>"),
                excerpt,
            )

            # URL in one of the forms commonly encountered on the web
            excerpt = re.sub(
                r"(\w+://)?[\w.-]+\.[a-zA-Z]{2,4}(?(1)|/)[\w#?&=%/:.-]*",
                TERMINAL.magenta_underline("\\g<0>"),
                excerpt,
            )

            excerpt = await self._highlight_pattern(
                excerpt, patterns, TERMINAL.black_on_yellow
            )

            self._queue.put_nowait(
                "%s%s%s%s"
                % (
                    indent,
                    "... " if clipped_left else "",
                    excerpt,
                    " ..." if clipped_right else "",
                )
            )

        if item.link is not None:
            self._links[self.item_count] = item.link
            if not self.args.snapshot:
                self._queue.put_nowait(
                    "%s%s"
                    % (
                        indent,
                        await self._highlight_pattern(
                            item.link,
                            patterns,
                            TERMINAL.black_on_yellow_underline,
                            TERMINAL.blue_underline,
                        ),
                    )
                )
            else:
                snapshot_item['link'] = item.link

        if self.args.snapshot:
            self._queue.put_nowait(snapshot_item)

    async def source_worker(self, queue):
        while True:
            url, patterns = await queue.get()

            if 'hackernews' not in url.lower():
                try:
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        headers = {
                            'User-Agent': 'krillbot/0.4 (+http://github.com/kyokley/krill)',
                        }
                        data = (await client.get(url, timeout=REQUESTS_TIMEOUT, headers=headers)).content

                    if "//twitter.com/" in url:
                        async for stream_data in StreamParser.get_tweets(data):
                            self._items_queue.put_nowait((stream_data, patterns))
                    else:
                        async for stream_data in StreamParser.get_feed_items(data, url):
                            self._items_queue.put_nowait((stream_data, patterns))

                except Exception as error:
                    await self._print_error(
                        "Unable to retrieve data from URL '%s': %s" % (url, str(error))
                    )
                    # The problem might be temporary, so we do not exit

            else:
                async for stream_data in self.hn_stories_generator():
                    self._items_queue.put_nowait((stream_data, patterns))

            queue.task_done()

    async def stream_worker(self, queue):
        while True:
            item, re_funcs = await queue.get()

            if re_funcs:
                for re_func in re_funcs:
                    title_matches = (
                        item.title is not None
                        and re_func(item.title)
                        or (False, set())
                    )
                    text_matches = (
                        item.text is not None
                        and re_func(item.text)
                        or (False, set())
                    )
                    link_matches = (
                        item.link is not None
                        and re_func(item.link)
                        or (False, set())
                    )
                    if title_matches[0] or text_matches[0] or link_matches[0]:
                        matched_texts = set()
                        matched_texts.update(
                            title_matches[1], text_matches[1], link_matches[1]
                        )
                        await self.add_item(item, matched_texts)
                        break
            else:
                # No filter patterns specified; simply print all items
                await self.add_item(item)

            queue.task_done()

    async def output_worker(self, queue):
        while True:
            item = await queue.get()
            await self._queue_item(item[0], item[1])
            queue.task_done()

    async def flush_worker(self, queue, interval=.1):
        while True:
            text = await queue.get()

            if not self.args.snapshot:
                idx = 0
                while idx < len(text):
                    await asyncio.sleep(self.text_speed(interval))
                    match = re.search(_invisible_codes, text[idx:])
                    if match:
                        end = idx + match.span()[1]
                        sys.stdout.write(text[idx:end])
                        idx = end
                    else:
                        sys.stdout.write(text[idx])
                        idx += 1
                    sys.stdout.flush()
                sys.stdout.write('\n')
                sys.stdout.flush()
            else:
                print(text)

            queue.task_done()

    async def _sources(self):
        # Reload sources and filters to allow for live editing
        sources = dict()
        if self.args.sources is not None:
            for source in self.args.sources:
                sources[source] = list()
        if self.args.sources_file is not None:
            if self.args.sources_file.endswith(".opml"):
                for source in await self._read_opml_file(self.args.sources_file):
                    sources[source] = list()
            else:
                sources.update(await self._read_sources_file(self.args.sources_file))

        if not sources:
            await self._print_error("No source specifications found")
            sys.exit(1)

        return sources

    async def _global_patterns(self):
        filters = list()
        if self.args.filters is not None:
            filters.extend(self.args.filters)
        if self.args.filters_file is not None:
            filters.extend(await self._read_filters_file(self.args.filters_file))

        global_patterns = list()
        for filter_string in filters:
            try:
                tokens = filter_lex(filter_string)
                parser = TokenParser(tokens)
                global_patterns.append(parser.buildFunc())
            except Exception as error:
                await self._print_error(
                    "Error while compiling regular expression '%s': %s"
                    % (filter_string, str(error))
                )
                sys.exit(1)

        return global_patterns

    async def update(self):
        self.clear()

        source_queue = asyncio.Queue()

        for source, source_patterns in self.sources:
            source_queue.put_nowait((source, source_patterns))

        self.items = list()

        tasks = []
        for _ in range(NUM_WORKERS):
            for x in range(2):
                task = asyncio.create_task(self.source_worker(source_queue))
                tasks.append(task)

            task = asyncio.create_task(self.stream_worker(self._items_queue))
            tasks.append(task)

            task = asyncio.create_task(self.output_worker(self._output_queue))
            tasks.append(task)

        task = asyncio.create_task(self.flush_worker(self._queue, self.text_speed_ave))
        tasks.append(task)

        await source_queue.join()
        await self._items_queue.join()
        await self._output_queue.join()
        await self._queue.join()

        for task in tasks:
            task.cancel()

        # Wait until all worker tasks are cancelled.
        await asyncio.gather(*tasks, return_exceptions=True)


    async def run(self):
        await self.populate_sources()

        if not self.args.snapshot:
            print(
                "%s (%s)"
                % (
                    TERMINAL.bold("krill 0.5.0"),
                    TERMINAL.underline("https://github.com/kyokley/krill"),
                )
            )

        try:
            original_text_speed = self.text_speed_ave
            self.text_speed_ave = 0

            await self.update()

            self.text_speed_ave = original_text_speed

            if self.args.snapshot:
                return

            if self.args.update_interval > 0:
                while True:
                    await asyncio.sleep(self.args.update_interval)

                    await self.update()
        except (KeyboardInterrupt, Quit, asyncio.exceptions.CancelledError):
            # Do not print stacktrace if user exits with Ctrl+C
            sys.exit()


def main():
    # Force UTF-8 encoding for stdout as we will be printing Unicode characters
    # which will fail with a UnicodeEncodeError if the encoding is not set,
    # e.g. because stdout is being piped.
    # See http://www.macfreek.nl/memory/Encoding_of_Python_stdout and
    # http://stackoverflow.com/a/4546129 for extensive discussions of the issue.
    if sys.stdout.encoding != "UTF-8":
        # For Python 2 and 3 compatibility
        prev_stdout = sys.stdout.buffer
        sys.stdout = codecs.getwriter("utf-8")(prev_stdout)

    arg_parser = argparse.ArgumentParser(
        prog="krill", description="Read and filter web feeds."
    )
    arg_parser.add_argument(
        "-s", "--sources", nargs="+", help="URLs to pull data from", metavar="URL"
    )
    arg_parser.add_argument(
        "-S",
        "--sources-file",
        help="file from which to load source URLs "
        + "(OPML format assumed if filename ends with \".opml\")",
        metavar="FILE",
    )
    arg_parser.add_argument(
        "-f",
        "--filters",
        nargs="+",
        help="patterns used to select feed items to print",
        metavar="REGEX",
    )
    arg_parser.add_argument(
        "-F",
        "--filters-file",
        help="file from which to load filter patterns",
        metavar="FILE",
    )
    arg_parser.add_argument(
        "--snapshot",
        action='store_true',
        help="return a single snapshot of all headlines in json format",
    )
    arg_parser.add_argument(
        "-u",
        "--update-interval",
        default=300,
        type=int,
        help="time between successive feed updates "
        + "(default: 300 seconds, 0 for single pull only)",
        metavar="SECONDS",
    )
    arg_parser.add_argument(
        "-t",
        "--text-speed-ave",
        default='0',
        type=str,
        help="text speed (0-10) 10 is slowest. 0 represents no delay. Default is 0.",
    )
    args = arg_parser.parse_args()

    if args.sources is None and args.sources_file is None:
        arg_parser.error(
            "either a source URL (-s) or a sources file (-S) must be given"
        )

    asyncio.run(
            Application(args).run()
            )


if __name__ == "__main__":
    main()
