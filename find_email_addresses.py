#!/usr/bin/env python
#
# requires python version 3 or greater.
#
# @copyright 2016 Nicholas Hinsch, based on work by Arun-UB https://github.com/Arun-UB
#
# @license MIT
#
# This script supports extracting multiple email addresses in mailto links from multiple webpages on any number of supplied domains.
# The page crawler is somewhat intelligent (it will skip assets like images, videos and documents as well as skipping offsite links.
# It also normalizes links that don't have the FQDN in the href.
#
# This doesn't parse javascript, so obfuscated emails are not detected. If I get any more spare time, I will see about adding that support.
# You can also set a crawl rate (delay) and maximum number of pages.
#
# Duplicate emails per domain are also stripped out. You're welcome :p
# sample use:
# python3 find_email_addresses.py --domains www.rapidtables.com/web/html/mailto.htm https://developer.mozilla.org/en-US/docs/Web/Guide/HTML/Email_links --delay 1 --maxpages 2 --outfile emails.txt
#
# Crawling www.rapidtables.com for email addresses.
# - Found email addresses:
# -- name1@rapidtables.com
# -- name2@rapidtables.com
# -- name@rapidtables.com
# -- name3@rapidtables.com
#
# Crawling developer.mozilla.org for email addresses.
# - Found email addresses:
# -- nowhere@mozilla.org
# -- nobody@mozilla.org
#
# If you run into problems, enable debug mode by supplying --verbose on the command line
#

from bs4 import BeautifulSoup
import html
import urllib
import argparse
import re
import queue
import time
import random

class Crawler(object):
    def __init__(self, url, delay, maxpages, outfile, verbose):

        self.delay = delay
        self.maxpages = maxpages
        self.verbose = verbose
        self.outfile = outfile

        # normalize the supplied url protocol
        if not re.match('https?://|www\\\.', url):
            url = 'http://' + url

        # Strip off query string params on url
        self.url = urllib.parse.urljoin(url, urllib.parse.urlparse(url).path)

        # extract the domain name from the url
        self.domainName = urllib.parse.urlparse(url).netloc

        self.emails = []

    def get_emails(self):

        addresses = list(set(self.emails))

        if self.outfile:
            with open(self.outfile, "a") as text_file:
                for i in addresses:
                    print(i, file=text_file)

        return addresses

    def extract_emails(self, page):
        for link in page.select('a[href^=mailto]'):

            # split apart multi-recipient mailto links
            emailaddresses = link.get('href')[7:].split(',')

            for addy in emailaddresses:
                #extract recipients, cc's and bcc's

                all_recipients = []

                # defeat some basic obfuscation techniques (html entities, urlencode)
                if '?' not in addy:
                    if '#&' or '%' in addy:
                        # obfuscated email address
                        deobfus = html.unescape(addy)
                        if '@' in deobfus:
                            all_recipients.append(deobfus)

                elif '?' in addy:
                    # multiple email addresses in this mailto
                    pattern = re.compile("[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
                    all_recipients = pattern.findall(addy)

                else:
                    # just a standard email address, plain and simple
                    all_recipients.append(addy)

                for i in all_recipients:
                    self.emails.append(i)


    def get_links(self, page):
        links = []

        for link in page.find_all('a'):
            if link.get('href') is None:
                self.debug('skipping homepage link!')

            elif link.get('href').startswith('#'):
                self.debug('skipping anchor!')

            elif link.get('href').startswith('//'):
                self.debug('skipping external or protocol relative link!')

            elif link.get('href').startswith('/'):
                link = urllib.parse.urljoin(self.url, link.get('href'))
                links.append(link)

            elif self.domainName not in link.get('href'):
                self.debug('skipping external link!')

            else:
                link = urllib.parse.urljoin(self.url, link.get('href'))
                links.append(link)

        self.debug('found the following url links:')
        self.debug(links)

        return list(links)

    def crawl(self):
        pagecount = 0
        excludedExtensions = (
            '.jpg', '.jpeg', '.png', '.gif',
            '.tif', '.doc', '.docx', '.xls',
            '.xlsx', '.pdf', '.log', '.msg',
            '.odt', '.pages', '.rtf', '.tex',
            '.wpd', '.wps', '.csv', '.ppt',
            '.pptx', '.zip', '.tar', '.xml',
            '.bz', '.tgz', '.tar.gz', '.vcf',
            '.aif', '.m3u', '.m4a', '.mid',
            '.mp3', '.mpa', '.wav', '.wma',
            '.avi', '.flv', '.mpg', '.mov',
            '.m4v', '.mp4', '.rm', '.swf',
            '.wmv', '.obs', '.3dm', '.3ds',
            '.max', '.bmp', '.psd', '.ai',
            '.tiff', '.eps', '.ps', '.svg',
            '.indd', '.pct', '.xlr', '.db',
            '.sql', '.dbf', '.pdb', '.app',
            '.bat', '.jar', '.wsf', '.rom',
            '.sav', '.dwg', '.dxf', '.kmz',
            '.ini', '.cfg', '.7z', '.cbr',
            '.rar', '.pkg', '.sitx', '.zipx',
            '.bin', '.cue', '.dmg', '.iso',
            '.mdf', '.toast', '.vcd', '.c',
            '.py', '.cpp', '.class', '.java',
            '.pl', '.sh', '.vb', '.swift',
            '.bak', '.tmp', '.ics', '.exe',
            '.msi', '.torrent', '.lua', '.deb',
            '.rpm', '.hqx', '.uue', '.sys'
        )
        tocrawl = queue.Queue()
        crawled = []
        tocrawl.put(self.url)

        #setup some headers to fool sites that try to prevent scraping :p
        user_agents = [
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36',
            'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:41.0) Gecko/20100101 Firefox/41.0',
            'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:41.0) Gecko/20100101 Firefox/41.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0',
            'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:41.0) Gecko/20100101 Firefox/41.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:41.0) Gecko/20100101 Firefox/41.0',
        ]

        user_agent = random.choice(user_agents)

        headers = {
            'User-Agent': user_agent,
            'Referer': self.url
        }

        while tocrawl.qsize():

            if pagecount == self.maxpages:
                break

            link = str(tocrawl.get())

            if link.lower().endswith(excludedExtensions):
                self.debug('Skipping : ' + link + ' because it\'s an asset, not a page!')

            elif link not in crawled:
                self.debug('Found a new page to crawl: ' + link)

                # skip dead links and pages we've already crawled
                try:
                    req = urllib.request.Request(link, None, headers)
                    page_content = urllib.request.urlopen(req)
                    page = BeautifulSoup(page_content, 'html.parser')

                    crawled.append(link)

                    # queue up new links found on this page
                    for l in self.get_links(page):
                        if l not in crawled:
                            tocrawl.put(l)
                            self.debug('-- Adding link: ' + l + ' found on page')

                    self.extract_emails(page)

                    pagecount += 1

                except urllib.error.HTTPError as e:
                    if e.code == 403:
                        self.debug('Skipping page: ' + link + ' because the crawler was forbidden access (403)!')
                    elif e.code == 404:
                        self.debug('Skipping page: ' + link + ' because the link is dead (404)!')
                    else:
                        self.debug('Skipping page: ' + link + 'because something else went wrong.  HTTP error code: ' + e.code)

                except urllib.error.URLError as e:
                    self.debug('Skipping unknown URL type!')

                    crawled.append(link)

                # wait for the specified amount of time between page requests...be nice to webservers!
                time.sleep(self.delay)

            else:
                self.debug('Skipping page: ' + link + ' because we\'ve already crawled this page!')

    # Log all the things!
    def debug(self, msg, prefix='DEBUG'):
        if self.verbose:
            print(prefix + ' ' + str(msg))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enter a URL")

    parser.add_argument(
        '--domains', nargs='+',
        help='Space-separated list of domains to crawl'
    )

    parser.add_argument(
        '--delay', nargs='?',
        default=5,
        help='The delay between page requests in seconds (default is 5 seconds)'
    )

    parser.add_argument(
        '--maxpages', nargs='?',
        default=100,
        help='The maximum number of pages to crawl per domain (default is 100 pages)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose mode. This prints a fuck-load of debug info to stdout (your terminal).'
    )

    parser.add_argument(
        '--outfile',
        help='Save scraped email addresses to a txt file, newline delimited.'
    )

    args = parser.parse_args()

    domains = args.domains
    delay = int(args.delay)
    maxpages = int(args.maxpages)
    verbose = args.verbose
    outfile = args.outfile

    for domain in domains:

        c = Crawler(str(domain).strip(), delay, maxpages, outfile, verbose)

        print("\nCrawling " + c.domainName + " for email addresses.")
        c.crawl()

        print("- Found email addresses:")
        for email in c.get_emails():
            print('-- ' + email)
