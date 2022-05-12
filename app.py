import asyncio
import os
import re
import aiohttp
import aiofiles
import requests
from bs4 import BeautifulSoup
import lxml
import regex
from time import sleep
from alive_progress import alive_bar
from rich.console import Console

PATH = str(os.path.join(os.environ["HOMEPATH"], "Desktop")).replace('\\', '/')

class YupooDownloader():
	def __init__(self, all_albums, urls = None, cover=False):
		self.console = Console(color_system="auto")
		self.all_albums = all_albums
		self.urls = urls
		self.cover = cover
		self.albums = {}
		if self.all_albums:
			self.pages = self.get_pages()

		self.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36', 'referer': "https://yupoo.com/"}
		self.timeout_connect = [10]
		self.connect_control = [0]
		self.connect_errors = [0]

		self.timeout_read = [10]
		self.read_control = [0]
		self.read_errors = [0]

		self.timeout = aiohttp.ClientTimeout(connect=self.timeout_connect[0], sock_read=self.timeout_read[0])

	class FatalException(Exception):
		pass

	async def main(self):
		if self.all_albums:
			#getting albums from pages resp
			self.tasks = []
			for page in self.pages:
				self.tasks.append(asyncio.ensure_future(self.async_req(page, self.get_albums)))
			self.console.print("\n[#6149ab]Pegando álbuns das páginas[/]")
			with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
				await self._(self.tasks, self.get_albums)

			#getting images from albums resp
			self.tasks = []
			for page in self.albums:
				for album in self.albums[page]:
					self.tasks.append(asyncio.ensure_future(self.async_req(self.albums[page][album]['album_link'], self.get_album)))
			self.console.print("\n[#6149ab]Pegando as imagens dos álbuns[/]")
			with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
				await self._(self.tasks, self.get_album)
		else:
			#getting images from albums resp
			self.tasks = []
			for url in self.urls:
				self.tasks.append(asyncio.ensure_future(self.async_req(url, self.get_album)))
			self.console.print("\n[#6149ab]Pegando as imagens dos álbuns[/]")
			with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
				await self._(self.tasks, self.get_album)

		#downloading imgs in albums
		self.console.print('\n[#6149ab]Baixando as imagens dos álbuns[#6149ab]')
		self.tasks=[]
		if self.all_albums:
			for page in self.albums:
				for album in self.albums[page]:
					for img in self.albums[page][album]['imgs']:
						img_link = img
						img_title = re.findall(r'/((?:(?!/).)*)$', img_link)[0].split('.')[0] #/((?:(?!/).)*)$
						path = f"{PATH}/fotos_camisa/{album}/{img_title}.jpg"
						if os.path.exists(path) == True:
							continue
						self.tasks.append(asyncio.ensure_future(self.async_req(img_link, self.get_imgs)))
				if len(self.tasks) > 0:
					with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
						await self._(self.tasks, self.get_imgs)
		else:
				for album in self.albums:
					for img in self.albums[album]['imgs']:
						img_link = img
						img_title = re.findall(r'/((?:(?!/).)*)$', img_link)[0].split('.')[0] #/((?:(?!/).)*)$
						path = f"{PATH}/fotos_camisa/{album}/{img_title}.jpg"
						if os.path.exists(path) == True:
							continue
						self.tasks.append(asyncio.ensure_future(self.async_req(img_link, self.get_imgs)))
				if len(self.tasks) > 0:
					with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
						await self._(self.tasks, self.get_imgs)

	async def async_req(self, url, function = None):
		def auto_timeout(timeout, control, errors, e, add):
			if errors[0] != 0:
				if control[0] // errors[0] <= e:
					timeout[0] += add
					control[0] = 0
					errors[0] = 0
					self.timeout = aiohttp.ClientTimeout(connect=self.timeout_connect[0], sock_read=self.timeout_read[0])
					print(self.timeout)
			else:
				control[0] = 0
				errors[0] = 0

		if self.connect_control[0] // 10 >= 1:
			auto_timeout(self.timeout_connect, self.connect_control, self.connect_errors, 4, 1)
		if self.read_control[0] // 10 >= 1:
			auto_timeout(self.timeout_read, self.read_control, self.read_errors, 4, 1)

		self.connect_control[0] +=1
		self.read_control[0] +=1

		try:
			async with aiohttp.ClientSession(headers=self.headers) as session:
				async with session.get(url, timeout=self.timeout, headers=self.headers) as resp:
					if resp.status == 200:
						if 'get_imgs' in repr(function):
							await function([await resp.read(), resp.status, url])
						else:
							self.bar()
							await function([await resp.text(), resp.status, url])
					else:
						return await self.async_req(url, function)
				
		except self.FatalException:
			raise self.FatalException()
		except Exception as e:
			if "Timeout on reading data from socket" in str(e):
				# print(self.read_errors, self.read_control)
				self.read_errors[0] += 1
			elif "Connection timeout to host" in str(e):
				self.connect_errors[0] += 1
			if url == str(e):
				self.error = 'link inválido!\n"'
				raise self.FatalException()
			return await self.async_req(url, function)

	def get_pages(self):
		# print('x')
		try:
			url = f"{self.urls}/albums?tab=gallery&page=1"
			while True:
				resp = requests.get(url)
				if resp.status_code == 200:
					break
				# print('again')

			soup = BeautifulSoup(resp.text.encode("ascii", "ignore").decode("utf-8"), "lxml")
			total_pages = soup.select_one("form.pagination__jumpwrap > span").get_text()
			print(f"pages: {total_pages}")
			pages = []
			for page in range(1, int(total_pages)+1):
					pages.append(f"{url[:-1]}{page}")
			if type(pages) == list:
				if None in pages:
					sleep(1)
					self.get_pages()
				else: 
					return pages
			elif pages == None:
				sleep(1)
				self.get_pages()
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
			self.albums[num_page][title] = {"album_link": self.urls+album.get('href')}

	async def get_album(self, r):
		keys = await self.find_key(self.albums, r[2])
		soup = BeautifulSoup(r[0].encode("ascii", "ignore").decode("utf-8"), "lxml")
		album_imgs_links = []
		if self.cover:
			cover = soup.select_one(".showalbumheader__gallerycover > img")
			src_cover = cover.get("src")
			src_cover = re.findall('/((?:(?!/).)*)/medium', src_cover)
		album_div = soup.find_all("div", {"class": "showalbum__children"})
		if len(album_div) == 0:
			self.error = 'não encontrado imagens no álbum, link potencialmente inválido!\n'
			raise self.FatalException()
		for img in album_div:
			img = img.find("img")
			src = img.get("data-origin-src") #data-origin-src
			if self.cover:
				src_re = re.findall('/((?:(?!/).)*)/((?:(?!/).)*)\.((?:(?!\.).)*)$', src)
				if src_cover[0] == src_re[0][0]:
					album_imgs_links.append(f"https:{src}")
					break
				continue
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
			img_title = re.findall(r'/((?:(?!/).)*)$', r[2])[0].split('.')[0] #/((?:(?!/).)*)$
		except:
			return

		path = f"{PATH}/fotos_camisa/{album}"
		if os.path.exists(path) == False:
			os.makedirs(path)
				
		try:
			async with aiofiles.open(f'{PATH}/fotos_camisa/{album}/{img_title}.jpg', mode='wb') as f:
				await f.write(r[0])
			self.bar()
		except Exception as e:
			None
			# print(e)

	async def _(self, tasks, function):
		try:
			resp = await asyncio.gather(*self.tasks)
		except self.FatalException:
			for task in self.tasks:
				task.cancel()
			raise Exception(self.error)


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

if __name__ == "__main__":
	import gui