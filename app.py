import asyncio
from logging import error
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
	def __init__(self, all_albums, urls = None, cover=False):
		self.all_albums = all_albums
		self.urls = urls
		self.cover = cover
		self.start_time = perf_counter()
		self.albums = {}
		self.pages = self.get_pages()
		self.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36', 'referer': "https://yupoo.com/"}
		self.timeout_connect = [0]
		self.connect_control = [0]
		self.connect_errors = [0]

		self.timeout_read = [0]
		self.read_control = [0]
		self.read_errors = [0]

		self.timeout = aiohttp.ClientTimeout(connect=self.timeout_connect[0], sock_read=self.timeout_read[0])

	async def main(self):
		session = aiohttp.ClientSession(headers=self.headers)
		async with session as self.session:
			print()
			if self.all_albums:
				print("getting albums from pages resp")
				#getting albums from pages resp
				tasks = []
				for page in self.pages:
					tasks.append(asyncio.ensure_future(self.async_req(page)))
				await self._(tasks, self.get_albums)

				print("getting images from albums resp")
				#getting images from albums resp
				tasks = []
				for page in self.albums:
					for album in self.albums[page]:
						tasks.append(asyncio.ensure_future(self.async_req(self.albums[page][album]['album_link'])))
				await self._(tasks, self.get_album)
			else:
				print("getting images from albums resp")
				tasks = []
				for url in self.urls:
					tasks.append(asyncio.ensure_future(self.async_req(url)))
				await self._(tasks, self.get_album)

	async def async_req(self, url, function = None):
		try:
			def auto_timeout(timeout, control, errors, e, add):
				if errors[0] != 0:
					if control[0] // errors[0] <= e:
						timeout[0] += add
						control[0] = 0
						errors[0] = 0
						self.timeout = aiohttp.ClientTimeout(connect=self.timeout_connect[0], sock_read=self.timeout_read[0])

			async with self.session.get(url, timeout=self.timeout, headers=self.headers) as resp:
				if function == None:
					self.connect_control[0] +=1
					self.read_control[0] +=1

					if self.connect_control[0] == 10:
						auto_timeout(self.timeout_connect, self.connect_control, self.connect_errors, 5, 4)
						print(self.timeout)

					elif self.read_control[0] == 10:
						auto_timeout(self.timeout_read, self.read_control, self.read_errors, 5, 4)
						print(self.timeout)

					return [await resp.text(), resp.status, url]
				else:
					return [await resp.read(), resp.status, url]
		except Exception as e:
			self.read_control[0] +=1
			self.connect_control[0] +=1
			if "Timeout on reading data from socket" in str(e):
				self.read_errors[0] += 1
			elif "Connection timeout to host" in str(e):
				self.connect_errors[0] += 1

			if self.connect_control[0] == 10:
				auto_timeout(self.timeout_connect, self.connect_control, self.connect_errors, 5, 4)
				print(self.timeout)

			elif self.read_control[0] == 10:
				auto_timeout(self.timeout_read, self.read_control, self.read_errors, 5, 4)
				print(self.timeout)

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
			title = await self.parse_title(album.get('title'))
			self.albums[num_page][title] = {"album_link": URL+album.get('href')}

	async def get_album(self, r):
		keys = await self.find_key(self.albums, r[2])
		soup = BeautifulSoup(r[0].encode("ascii", "ignore").decode("utf-8"), "lxml")
		album_imgs_links = []
		if self.cover:
			cover = soup.select_one(".showalbumheader__gallerycover > img")
			src_cover = cover.get("src")
			src_cover = re.findall('/((?:(?!/).)*)/medium', src_cover)
		for img in soup.find_all("div", {"class": "showalbum__children"}):
			img = img.find("img")
			src = img.get("src") #data-origin-src
			src_re = re.findall('/((?:(?!/).)*)/((?:(?!/).)*)\.((?:(?!\.).)*)$', src)
			if len(src_cover) == 0 or src_re[0][0] == "alisports":
				continue
			if self.cover == True and src_cover[0] == src_re[0][0]:
				album_imgs_links.append(f"https:{src}")
				break
			elif self.cover == False:
				album_imgs_links.append(f"https:{src}")
		if self.all_albums:
			self.albums[keys[0]][keys[1]]['imgs'] = album_imgs_links
		else:
			title = soup.select_one("span.showalbumheader__gallerytitle").text
			title = await self.parse_title(title)
			self.albums[title] = {}
			self.albums[title]["album_link"] = r[2]
			self.albums[title]["imgs"] = album_imgs_links

	async def get_imgs(self, r):
		keys = await self.find_key(self.albums, r[2])
		if self.all_albums:
			album = keys[1]
		else:
			album = keys[0]
		try:
			img_title = re.findall(r'/((?:(?!/).)*)/small', r[2])[0].split('.')[0] #/((?:(?!/).)*)$
		except:
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

					
			#downloading imgs in albums
			print()
			print("downloading imgs in albums")
			tasks=[]
			if self.all_albums:
				for page in self.albums:
					for album in self.albums[page]:
						for img in self.albums[page][album]['imgs']:
							img_link = img
							img_title = re.findall(r'/((?:(?!/).)*)/small', img_link)[0].split('.')[0] #/((?:(?!/).)*)$
							path = f"{PATH}/photos/{album}/{img_title}.jpg"
							if os.path.exists(path) == True:
								print(f'{img_title} já existe')
								continue
							tasks.append(asyncio.ensure_future(self.async_req(img_link, 'get_imgs')))
					if len(tasks) > 0:
						await self._(tasks, self.get_imgs)
			else:
					for album in self.albums:
						for img in self.albums[album]['imgs']:
							img_link = img
							img_title = re.findall(r'/((?:(?!/).)*)/small', img_link)[0].split('.')[0] #/((?:(?!/).)*)$
							path = f"{PATH}/photos/{album}/{img_title}.jpg"
							if os.path.exists(path) == True:
								print(f'{img_title} já existe')
								continue
							tasks.append(asyncio.ensure_future(self.async_req(img_link, 'get_imgs')))
					if len(tasks) > 0:
						await self._(tasks, self.get_imgs)

			#####
			print(self.albums)
			print(perf_counter()-self.start_time)

	async def parse_title(self, title):
		title = title.replace('.', '_').replace('/', '_').replace(':', '').replace('"', '').replace("'", '').replace('*','')
		it = 0
		while True:
			it+=1
			if it == 1:
				if await self.find_key(self.albums, title) == None:
					break
			else:
				if await self.find_key(self.albums, f"{title} - {str(it)}") == None:
					title = f"{title} - {str(it)}"
					break
				else:
					continue
		return title

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
	
asyncio.run(YupooDownloader(all_albums= False, cover=True).main())