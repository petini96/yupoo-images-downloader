import asyncio
import os
import re
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
		self.timeout = aiohttp.ClientTimeout(connect=15, sock_read=25)

	async def _(self, tasks, function):
		print(len(tasks))
		errors = []
		resp = await asyncio.gather(*tasks)
		for r in resp:
			if len(r) != 1:
				if r[1] == 200:
						await function(r)
				else:
					errors.append(r[2])
			else:
				errors.append(r[0])
		if len(errors) > 0:
			tasks = []
			for error in errors:
				if 'get_imgs' in repr(function):
					tasks.append(asyncio.ensure_future(self.async_req(error, 'get_imgs')))
				else:
					tasks.append(asyncio.ensure_future(self.async_req(error)))
			await asyncio.sleep(1.6)
			await self._(tasks, function)

	async def main(self):
		session = aiohttp.ClientSession(headers=self.headers)
		async with session as self.session:
					
			#getting albums from pages resp
			print()
			print("getting albums from pages resp")
			tasks = []
			for page in self.pages:
				tasks.append(asyncio.ensure_future(self.async_req(page)))
			await self._(tasks, self.get_albums)

			#getting images from albums resp
			print()
			print("getting images from albums resp")
			tasks = []
			for page in self.albums:
				for album in self.albums[page]:
					tasks.append(asyncio.ensure_future(self.async_req(self.albums[page][album]['album_link'])))
			await self._(tasks, self.get_album)
	
			#downloading imgs in albums
			print()
			print("downloading imgs in albums")
			for page in self.albums:
				tasks=[]
				for album in self.albums[page]:
					for img in self.albums[page][album]['imgs']:
						img_link = img
						tasks.append(asyncio.ensure_future(self.async_req(img_link, 'get_imgs')))
				await self._(tasks, self.get_imgs)

			#####
			print(perf_counter()-self.start_time)

	async def async_req(self, url, function = None):
		try:
			async with self.session.get(url, timeout=self.timeout, headers=self.headers) as resp:
				if function == None:
					return [await resp.text(), resp.status, url]
				else:
					return [await resp.read(), resp.status, url]
		except Exception as e:
			return [url]

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
			if type(pages) == list:
				if None in pages:
					sleep(1)
					self.get_pages()
				else: 
					return pages
			else:
				sleep(1)
				self.get_pages()
		except Exception as e:
			print(e)
			print('error - get_pages')
			sleep(1)
			self.get_pages()

	async def get_albums(self, page):
		num_page = str(regex.findall(r"&page=(.+)", page[2])[0])
		page = page[0]

		self.albums[num_page] = {}
		soup = BeautifulSoup(page.encode("ascii", "ignore").decode("utf-8"), "lxml")
		for album in soup.find_all("a", {"class": "album__main"}):
			title = album.get('title').replace('.', '_').replace('/', '_').replace(':', '').replace('"', '').replace("'", '').replace('*','')

			it = 0
			while True:
				it+=1
				if it == 1:
					if await self.find_key(self.albums, title) == None:
						self.albums[num_page][title] = {"album_link": URL+album.get('href')}
						break
				else:
					if await self.find_key(self.albums, f"{title} - {str(it)}") == None:
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
			src = img.get("src") #data-origin-src
			album_imgs_links.append(f"https:{src}")
		self.albums[keys[0]][keys[1]]['imgs'] = album_imgs_links
	
	async def find_key(self, d, value):
		for k,v in d.items():
				if isinstance(v, dict):
						p = await self.find_key(v, value)
						if p:
							return [k] + p
				elif isinstance(v, list) == True and k == "imgs":
					if value in v:
						return [k]
				elif v == value:
						return [k]

	async def get_imgs(self, r):
		keys = await self.find_key(self.albums, r[2])
		album = keys[1]
		try:
			img_title = re.findall(r'/((?:(?!/).)*)/small', r[2])[0].split('.')[0] #/((?:(?!/).)*)$
		except:
			return

		path = f"{PATH}/photos/{album}/{img_title}.jpg"
		if os.path.exists(path) == True:
			print(f'{img_title} já existe')
			return

		path = f"{PATH}/photos/{album}"
		if os.path.exists(path) == False:
				os.makedirs(path)
				
		try:
			async with aiofiles.open(f'./photos/{album}/{img_title}.jpg', mode='wb') as f:
				await f.write(r[0])
			print(f'200 - {img_title}')
		except Exception as e:
			print(e)
		

	
asyncio.run(YupooDownloader().main())