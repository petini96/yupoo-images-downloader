import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
import lxml
import regex
from time import time, sleep
from config import URL,PATH

class YupooDownloader():
	def __init__(self):
		self.albums = {}
		self.pages = self.get_pages()
		self.timeout = aiohttp.ClientTimeout(total=35)
		asyncio.run(self.main())

	async def main(self):
		async with aiohttp.ClientSession(headers={'referer': "https://yupoo.com/"}) as self.session:
			#getting albums
			tasks = []
			for page in self.pages:
				tasks.append(asyncio.ensure_future(self.async_req(page)))
			await self.get_albums(await asyncio.gather(*tasks))
		# print(self.albums)

	async def async_req(self, url):
		try:
			async with self.session.get(url) as resp:
				return await resp.text()
		except Exception as e:
			print(e)
			print('error - async_req')

	def get_pages(self):
		try:
			url = f"{URL}/albums?tab=gallery&page=1"
			resp = requests.get(url)
			if resp.status_code != 200:
				sleep(1)
				self.get_pages()

			soup = BeautifulSoup(resp.text.encode("ascii", "ignore").decode("utf-8"), "lxml")
			total_pages = soup.select_one("form.pagination__jumpwrap > span").get_text()
			pages = []
			for page in range(1, int(total_pages)+1):
					pages.append(f"{url[:-1]}{page}")
			if pages[0] == None:
				sleep(1)
				self.get_pages()
			else:
				return pages
		except Exception as e:
			print(e)
			print('error - get_pages')
			sleep(1)
			self.get_pages()

	async def get_albums(self, pages):
		for i,page in enumerate(pages):
			num_page = i+1
			self.albums[num_page] = {}
			soup = BeautifulSoup(page.encode("ascii", "ignore").decode("utf-8"), "lxml")
			for album in soup.find_all("a", {"class": "album__main"}):
				title = album.get('title').replace('.', '_').replace('/', '_').replace(':', '').replace('"', '').replace("'", '')

				it = 0
				while True:
					it+=1
					if it == 1:
						if title not in self.albums[num_page]:
							self.albums[num_page][title] = {"album_link": URL+album.get('href')}
							break
					else:
						if f"{title} - {str(it)}" not in self.albums[num_page]:
							self.albums[num_page][f"{title} - {str(it)}"] = {"album_link": URL+album.get('href')}
							break
						else:
							continue

YupooDownloader()