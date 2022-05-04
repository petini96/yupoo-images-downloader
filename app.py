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

	async def main(self):
		session = aiohttp.ClientSession(headers={'referer': "https://yupoo.com/"})
		async with session as self.session:
			#getting albums from pages resp
			async def _(tasks, function):
				errors = []
				resp = await asyncio.gather(*tasks)
				for r in resp:
					if len(r) != 1:
						if r[1] == 200:
							if 'get_album ' in repr(function):
								self.__.append(r)
								if len(self.__) == 60:
									print('a')
									self.__ ==0
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
			for page in self.albums:
				tasks = []
				for album in self.albums[page]:
					tasks.append(asyncio.ensure_future(self.async_req(self.albums[page][album]['album_link'])))
				print(len(tasks))
				await _(tasks, self.get_album)
				print('x')
				

	async def async_req(self, url):
		try:
			async with self.session.get(url) as resp:
				try:
					if resp == None:
						print('c')
					if resp != None:
						return [await resp.text(), resp.status, url]
					return [url]
				except Exception as e:
					print(type(resp))
					print(resp)
					print(e)
		except Exception as e:
			i =1
			# print(e)
			# print('error - async_req')

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
		soup = BeautifulSoup(r[0].encode("ascii", "ignore").decode("utf-8"), "lxml")
		album_imgs_links = []
		for img in soup.find_all("div", {"class": "showalbum__children"}):
			img = img.find("img")
			src = img.get("data-origin-src")
			album_imgs_links.append(f"https:{src}")

asyncio.run(YupooDownloader().main())