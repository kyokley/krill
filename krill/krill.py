#!/usr/bin/env python
# krill - the hacker's way of keeping up with the world
#
# Copyright (c) 2015 Philipp Emanuel Weidmann <pew@worldwidemann.com>
#
# Nemo vir est qui mundum non reddat meliorem.
#
# Released under the terms of the GNU General Public License, version 3
# (https://gnu.org/licenses/gpl.html)
import re
import sys
import time
import codecs
import argparse
import calendar
import requests
from datetime import datetime
from collections import namedtuple

import feedparser
from bs4 import BeautifulSoup
from blessings import Terminal

from .lexer import filter_lex
from .parser import TokenParser

base_type_speed = .01

_invisible_codes = re.compile(r"^(\x1b\[\d*m|\x1b\[\d*\;\d*\;\d*m|\x1b\(B)")  # ANSI color codes

StreamItem = namedtuple("StreamItem", ["source", "time", "title", "text", "link"])

class StreamParser(object):
    @staticmethod
    def _html_to_text(html):
        # Hack to prevent Beautiful Soup from collapsing space-keeping tags
        # until no whitespace remains at all
        html = re.sub("<(br|p|li)", " \\g<0>", html, flags=re.IGNORECASE)
        text = BeautifulSoup(html, "html.parser").get_text()
        # Idea from http://stackoverflow.com/a/1546251
        return " ".join(text.strip().split())

    @classmethod
    def get_tweets(cls, html):
        document = BeautifulSoup(html, "html.parser")

        for tweet in document.find_all("p", class_="tweet-text"):
            header = tweet.find_previous("div", class_="stream-item-header")

            name = header.find("strong", class_="fullname").string
            username = header.find("span", class_="username").b.string

            time_string = header.find("span", class_="_timestamp")["data-time"]
            timestamp = datetime.fromtimestamp(int(time_string))

            # For Python 2 and 3 compatibility
            to_unicode = unicode if sys.version_info[0] < 3 else str
            # Remove ellipsis characters added by Twitter
            text = cls._html_to_text(to_unicode(tweet).replace(u"\u2026", ""))

            link = "https://twitter.com%s" % header.find("a", class_="tweet-timestamp")["href"]

            yield StreamItem("%s (@%s)" % (name, username), timestamp, None, text, link)

    @classmethod
    def get_feed_items(cls, xml, url):
        feed_data = feedparser.parse(xml)
        # Default to feed URL if no title element is present
        feed_title = feed_data.feed.get("title", url)

        for entry in feed_data.entries:
            timestamp = datetime.fromtimestamp(calendar.timegm(entry.published_parsed)) \
                   if "published_parsed" in entry else None
            title = entry.get("title")
            text = cls._html_to_text(entry.description) if "description" in entry else None
            link = entry.get("link")

            # Some feeds put the text in the title element
            if text is None and title is not None:
                text = title
                title = None

            # At least one element must contain text for the item to be useful
            if title or text or link:
                yield StreamItem(feed_title, timestamp, title, text, link)

class TextExcerpter(object):
    # Clips the text to the position succeeding the first whitespace string
    @staticmethod
    def _clip_left(text):
        return re.sub("^\S*\s*", "", text, 1)

    # Clips the text to the position preceding the last whitespace string
    @staticmethod
    def _clip_right(text):
        return re.sub("\s*\S*$", "", text, 1)

    @staticmethod
    def _get_max_pattern_span(text, patterns):
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
    def get_excerpt(cls, text, max_length, patterns=None):
        if len(text) <= max_length:
            return text, False, False

        start, end = cls._get_max_pattern_span(text, patterns)
        if start is None and end is None:
            return cls._clip_right(text[:max_length]), False, True
        else:
            remaining_length = max_length - (end - start)
            if remaining_length <= 0:
                # Matches are never clipped
                return text[start:end]

            excerpt_start = max(start - (remaining_length // 2), 0)
            excerpt_end = min(end + (remaining_length - (start - excerpt_start)), len(text))
            # Adjust start of excerpt in case the string after the match was too short
            excerpt_start = max(excerpt_end - max_length, 0)
            excerpt = text[excerpt_start:excerpt_end]
            if excerpt_start > 0:
                excerpt = cls._clip_left(excerpt)
            if excerpt_end < len(text):
                excerpt = cls._clip_right(excerpt)

            return excerpt, excerpt_start > 0, excerpt_end < len(text)

class Application(object):
    def __init__(self, args):
        self._known_items = set()
        self.args = args
        if self.args.type_speed.lower() == 'fast':
            self.type_speed = .01
        elif self.args.type_speed.lower() == 'slow':
            self.type_speed = .1
        else:
            speed = int(self.args.type_speed)
            if speed < 0 or speed > 10:
                raise ValueError('Speed is invalid. Got %s' % speed)
            self.type_speed = speed * base_type_speed
        self.items = list()
        self._queue = list()

    def add_item(self, item, patterns=None):
        item_id = (item.source, item.link)
        if item_id in self._known_items:
            # Do not print an item more than once
            return
        self._known_items.add(item_id)
        self.items.append((item, patterns))

    @staticmethod
    def _print_error(error):
        print("")
        print(Terminal().bright_red(error))

    @classmethod
    def _get_stream_items(cls, url):
        try:
            data = requests.get(url).content
        except Exception as error:
            cls._print_error("Unable to retrieve data from URL '%s': %s" % (url, str(error)))
            # The problem might be temporary, so we do not exit
            return list()

        if "//twitter.com/" in url:
            return StreamParser.get_tweets(data)
        else:
            return StreamParser.get_feed_items(data, url)

    @classmethod
    def _read_sources_file(cls, filename):
        output = dict()
        lines = cls._read_lines(filename)
        for line in lines:
            data = line.partition(' ')
            if data[1] and data[2]:
                output[data[0]] = data[2]
            else:
                output[data[0]] = list()
        return output

    @classmethod
    def _read_lines(cls, filename):
        try:
            with open(filename, "r") as myfile:
                lines = [line.strip() for line in myfile.readlines()]
        except Exception as error:
            cls._print_error("Unable to read file '%s': %s" % (filename, str(error)))
            sys.exit(1)

        # Discard empty lines and comments
        return [line for line in lines if line and not line.startswith("#")]
    _read_filters_file = _read_lines

    # Extracts feed URLs from an OPML file (https://en.wikipedia.org/wiki/OPML)
    @classmethod
    def _read_opml_file(cls, filename):
        try:
            with open(filename, "r") as myfile:
                opml = myfile.read()
        except Exception as error:
            cls._print_error("Unable to read file '%s': %s" % (filename, str(error)))
            sys.exit(1)

        return [match.group(2).strip() for match in
                re.finditer("xmlUrl\s*=\s*([\"'])(.*?)\\1", opml, flags=re.IGNORECASE)]

    @staticmethod
    def _highlight_pattern(text, patterns, pattern_style, text_style=None):
        if patterns is None:
            return text if text_style is None else text_style(text)
        if text_style is None:
            for pattern in patterns:
                text = pattern.sub(pattern_style("\\g<0>"), text)
            return text
        for pattern in patterns:
            text = text_style(pattern.sub(pattern_style("\\g<0>") + text_style, text))
        return text

    def _queue_item(self, item, patterns=None):
        self._queue.append("")

        term = Terminal()
        time_label = " on %s at %s" % (term.yellow(item.time.strftime("%a, %d %b %Y")),
                                       term.yellow(item.time.strftime("%H:%M"))) \
                     if item.time is not None else ""
        self._queue.append("%s%s:" % (term.cyan(item.source), time_label))

        if item.title is not None:
            self._queue.append("   %s" % self._highlight_pattern(item.title,
                                                   patterns,
                                                   term.bold_black_on_bright_yellow,
                                                   term.bold))

        if item.text is not None:
            (excerpt,
             clipped_left,
             clipped_right) = TextExcerpter.get_excerpt(item.text,
                                                        300,
                                                        patterns)

            # Hashtag or mention
            excerpt = re.sub("(?<!\w)([#@])(\w+)",
                             term.green("\\g<1>") + term.bright_green("\\g<2>"),
                             excerpt)

            # URL in one of the forms commonly encountered on the web
            excerpt = re.sub("(\w+://)?[\w.-]+\.[a-zA-Z]{2,4}(?(1)|/)[\w#?&=%/:.-]*",
                             term.bright_magenta_underline("\\g<0>"), excerpt)

            # TODO: This can break previously applied highlighting (e.g. URLs)
            excerpt = self._highlight_pattern(excerpt,
                                             patterns,
                                             term.black_on_bright_yellow)

            self._queue.append("   %s%s%s" % ("... " if clipped_left else "", excerpt,
                                 " ..." if clipped_right else ""))

        if item.link is not None:
            self._queue.append("   %s" % self._highlight_pattern(item.link,
                                                   patterns,
                                                   term.black_on_bright_yellow_underline,
                                                   term.bright_blue_underline))

    def flush_queue(self, interval=.1):
        for text in self._queue:
            idx = 0
            while idx < len(text):
                time.sleep(interval)
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
        self._queue = list()

    def update(self):
        # Reload sources and filters to allow for live editing
        sources = dict()
        if self.args.sources is not None:
            for source in self.args.sources:
                sources[source] = list()
        if self.args.sources_file is not None:
            if self.args.sources_file.endswith(".opml"):
                for source in self._read_opml_file(self.args.sources_file):
                    sources[source] = list()
            else:
                sources.update(self._read_sources_file(self.args.sources_file))
        if not sources:
            self._print_error("No source specifications found")
            sys.exit(1)

        filters = list()
        if self.args.filters is not None:
            filters.extend(self.args.filters)
        if self.args.filters_file is not None:
            filters.extend(self._read_filters_file(self.args.filters_file))

        global_patterns = list()
        for filter_string in filters:
            try:
                tokens = filter_lex(filter_string)
                parser = TokenParser(tokens)
                global_patterns.append(parser.buildFunc())
            except Exception as error:
                self._print_error("Error while compiling regular expression '%s': %s" %
                                  (filter_string, str(error)))
                sys.exit(1)

        self.items = list()

        for source, source_patterns in sources.items():
            re_funcs = None
            if source_patterns:
                tokens = filter_lex(source_patterns)
                parser = TokenParser(tokens)
                re_funcs = [parser.buildFunc()]
            else:
                re_funcs = global_patterns

            for item in self._get_stream_items(source):
                if re_funcs:
                    for re_func in re_funcs: 
                        title_matches = item.title is not None and re_func(item.title) or (False, set())
                        text_matches = item.text is not None and re_func(item.text) or (False, set())
                        link_matches = item.link is not None and re_func(item.link) or (False, set())
                        if (title_matches[0] or
                                text_matches[0] or
                                link_matches[0]):
                            matched_texts = set()
                            matched_texts.update(title_matches[1], text_matches[1], link_matches[1])
                            self.add_item(item, matched_texts)
                            break
                else:
                    # No filter patterns specified; simply print all items
                    self.add_item(item)

        # Print latest news last
        self.items.sort(key=lambda item: datetime.now() if item[0].time is None else item[0].time)

        for item in self.items:
            self._queue_item(item[0], item[1])

    def run(self):
        term = Terminal()
        print("%s (%s)" % (term.bold("krill++ 0.4.0"),
                           term.underline("https://github.com/kyokley/krill")))

        try:
            self.update()
            #self.flush_queue(interval=0)
            self.flush_queue(interval=self.type_speed)
            if self.args.update_interval > 0:
                while True:
                    time.sleep(self.args.update_interval)
                    self.update()
                    self.flush_queue(interval=self.type_speed)
        except KeyboardInterrupt:
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
        prev_stdout = sys.stdout if sys.version_info[0] < 3 else sys.stdout.buffer
        sys.stdout = codecs.getwriter("utf-8")(prev_stdout)

    arg_parser = argparse.ArgumentParser(prog="krill", description="Read and filter web feeds.")
    arg_parser.add_argument("-s", "--sources", nargs="+",
            help="URLs to pull data from", metavar="URL")
    arg_parser.add_argument("-S", "--sources-file",
            help="file from which to load source URLs " +
                 "(OPML format assumed if filename ends with \".opml\")", metavar="FILE")
    arg_parser.add_argument("-f", "--filters", nargs="+",
            help="patterns used to select feed items to print", metavar="REGEX")
    arg_parser.add_argument("-F", "--filters-file",
            help="file from which to load filter patterns", metavar="FILE")
    arg_parser.add_argument("-u", "--update-interval", default=300, type=int,
            help="time between successive feed updates " +
                 "(default: 300 seconds, 0 for single pull only)", metavar="SECONDS")
    arg_parser.add_argument("-t", "--type-speed", default='0', type=str,
            help="text speed (0-10) 10 is slowest. 0 represents no delay. Default is 0.")
    args = arg_parser.parse_args()

    if args.sources is None and args.sources_file is None:
        arg_parser.error("either a source URL (-s) or a sources file (-S) must be given")

    Application(args).run()

if __name__ == "__main__":
    main()
