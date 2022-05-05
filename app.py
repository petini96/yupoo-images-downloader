import asyncio
import aiohttp
import aiofiles
import requests
from bs4 import BeautifulSoup
import lxml
import regex
from time import perf_counter, sleep
from config import URL,PATH

class YupooDownloader():
	def __init__(self):
		self.start_time = perf_counter()
		self.albums = {}
		self.pages = self.get_pages()
		self.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36', 'referer': "https://yupoo.com/"}
		self.timeout = aiohttp.ClientTimeout(total=25)

	async def main(self):
		session = aiohttp.ClientSession(headers=self.headers)
		async with session as self.session:
			#getting albums from pages resp
			async def _(tasks, function):
				print(len(tasks))
				errors = []
				resp = await asyncio.gather(*tasks)
				for r in resp:
					if len(r) != 1:
						if r[1] == 200:
							if 'get_album ' in repr(function):
								self.__.append(r)
								# print(f"zz:{len(self.__)}")
								if len(self.__) == 30:
									print('ax')
									self.__ = []
							await function(r)
						else:
							errors.append(r[2])
					else:
						errors.append(r[0])
				if len(errors) > 0:
					tasks = []
					for error in errors:
						tasks.append(asyncio.ensure_future(self.async_req(error)))
					await _(tasks, function)

			tasks = []
			for page in self.pages:
				tasks.append(asyncio.ensure_future(self.async_req(page)))
			await _(tasks, self.get_albums)

			print(self.albums[23])

			#getting images from albums resp
			self.__ = []
			tasks = []
			for page in self.albums:
				for album in self.albums[page]:
					tasks.append(asyncio.ensure_future(self.async_req(self.albums[page][album]['album_link'])))
					# if len(tasks) == 58:
				await _(tasks, self.get_album)
				tasks=[]

			print(self.albums)
			print(perf_counter()-self.start_time)
			import json
			async with aiofiles.open('albums.json', 'w') as f:
				json.dump(self.albums,f)
				

	async def async_req(self, url):
		try:
			async with self.session.get(url, timeout=self.timeout) as resp:
				return [await resp.text(), resp.status, url]
		except Exception as e:
			return [url]

	def get_pages(self):
		try:
			url = f"{URL}/albums?tab=gallery&page=1"
			print('d')
			resp = requests.get(url)
			print('e')
			if resp.status_code != 200:
				print('b')
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

	async def get_albums(self, page):
		num_page = int(regex.findall(r"&page=(.+)", page[2])[0])
		page = page[0]

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

	async def get_album(self, r):
		keys = await self.find_key(self.albums, r[2])
		soup = BeautifulSoup(r[0].encode("ascii", "ignore").decode("utf-8"), "lxml")
		album_imgs_links = []
		for img in soup.find_all("div", {"class": "showalbum__children"}):
			img = img.find("img")
			src = img.get("data-origin-src")
			album_imgs_links.append(f"https:{src}")
		self.albums[keys[0]][keys[1]]['imgs'] = album_imgs_links

	async def find_key(self, d, value):
		for k,v in d.items():
				if isinstance(v, dict):
						p = await self.find_key(v, value)
						if p:
							return [k] + p
				elif v == value:
						return [k]

asyncio.run(YupooDownloader().main())