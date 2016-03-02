from bs4 import BeautifulSoup, SoupStrainer
import urllib
import urlparse
import argparse
import re
import Queue

class Crawler(object):
	def __init__(self, domainName):
		self.domainName = domainName
		self.url = domainName
		self.emails = []
		
		if not re.match(r'http(s?)\:www', domainName):
			self.url = 'http://www.' + domainName

	def get_emails(self):
		return list(set(self.emails))

	def extract_emails(self,page):
		[self.emails.append(link.get('href')[7:]) for link in
				page.select('a[href^=mailto]')]
		
	def get_links(self,page):
		links = {}
		links = {link.get('href') for link in page.find_all('a') 
							if self.domainName in str(link.get('href'))}
		return list(links)

	def crawl(self):

		tocrawl = Queue.Queue()
		crawled = []
		tocrawl.put(self.url)

		while tocrawl.qsize():
			link = str(tocrawl.get())
			#To remove query string params
			link = urlparse.urljoin(link, urlparse.urlparse(link).path)

			page = BeautifulSoup(urllib.urlopen(link).read(),'html.parser')			# print(tocrawl.qsize())
			crawled.append(link)
			[tocrawl.put(l) for l in self.get_links(page) if l not in crawled]
			self.extract_emails(page)


if __name__=="__main__":
	parser = argparse.ArgumentParser(description="Enter a URL")
	parser.add_argument('domainName')
	args = parser.parse_args()
	c = Crawler(args.domainName.strip())
	c.crawl()
	print("The following emails were found")
	for email in c.get_emails():
		print(email)


