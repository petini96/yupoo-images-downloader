if __name__ == "__main__":
	import app
else:
	import os
	os.environ['PYTHONASYNCIODEBUG'] = '1'

	import logging
	DEFAULT_PATH = os.path.dirname(__file__)
	logger = logging.getLogger()
	logger.setLevel(logging.INFO)
	formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

	fh = logging.FileHandler(f"{DEFAULT_PATH}/info.log",mode="a",encoding="utf-8")
	fh.setFormatter(formatter)
	logger.addHandler(fh)

	logger.info("start")

	import asyncio
	import re
	import aiohttp
	import aiofiles
	import requests
	from bs4 import BeautifulSoup
	import lxml
	import regex
	from time import sleep, perf_counter
	from alive_progress import alive_bar
	from rich.console import Console
	import traceback
	import piexif
	from PIL import ImageFile
	ImageFile.LOAD_TRUNCATED_IMAGES = True
	from PIL import Image as Image
	from io import BytesIO

	import ssl
	import certifi
	sslcontext = ssl.create_default_context(cafile=certifi.where())

	import json
	with open(DEFAULT_PATH + '/config.json', 'r') as f:
		config = json.load(f)
	OUTPUT_PATH = config['path_to_save']
	logger.info(OUTPUT_PATH)

	class YupooDownloader():
		def __init__(self, all_albums, urls = None, cover=False):
			self.start_time_class = perf_counter()
			self.now = lambda: round(perf_counter()-self.start_time, 2)
			self.console = Console(color_system="auto")
			self.all_albums = all_albums
			self.urls = urls
			logger.info(str(self.urls))
			self.cover = cover
			self.albums = {}
			if self.all_albums:
				self.pages = self.get_pages()

			self.headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36', 'referer': "https://yupoo.com/"}
			self.timeout_connect = [25]
			self.connect_control = [0]
			self.connect_errors = [0]

			self.timeout_read = [25]
			self.read_control = [0]
			self.read_errors = [0]

			self.sem = asyncio.Semaphore(120)
			self.timeout = aiohttp.ClientTimeout(connect=self.timeout_connect[0], sock_read=self.timeout_read[0])
			self.oldtimeout = [self.timeout.connect, self.timeout.sock_read]

		class FatalException(Exception):
			pass

		async def main(self):
			session = aiohttp.ClientSession()
			async with session as self.session:
				if self.all_albums:
					#getting albums from pages resp
					self.tasks = []
					for page in self.pages:
						self.tasks.append(asyncio.ensure_future(self.async_req(page, self.get_albums)))
					logger.info(f"[all_albums] getting albums from pages resp: {len(self.tasks)}")
					self.console.print("\n[#6149ab]Pegando álbuns das páginas[/]")
					with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
						self.start_time = perf_counter()
						await self._(self.tasks, self.get_albums)
					logger.info(self.now())

					#getting images from albums resp
					self.tasks = []
					for page in self.albums:
						for album in self.albums[page]:
							self.tasks.append(asyncio.ensure_future(self.async_req(self.albums[page][album]['album_link'], self.get_album)))
					logger.info(f"[all_albums] getting images from albums resp: {len(self.tasks)}")
					self.console.print("\n[#6149ab]Pegando as imagens dos álbuns[/]")
					with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
						self.start_time = perf_counter()
						if len(self.tasks) > 0:
							await self._(self.tasks, self.get_album)
					logger.info(self.now())

				else:
					#getting images from albums resp
					self.tasks = []
					for url in self.urls:
						self.tasks.append(asyncio.ensure_future(self.async_req(url, self.get_album)))
					logger.info(f"[all_albums == False] getting images from albums resp: {len(self.tasks)}")
					self.console.print("\n[#6149ab]Pegando as imagens dos álbuns[/]")
					with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
						self.start_time = perf_counter()
						await self._(self.tasks, self.get_album)
					logger.info(self.now())

				#downloading imgs in albums
				self.tasks=[]
				self.start_time = perf_counter()
				if self.all_albums:
					for page in self.albums:
						for album in self.albums[page]:
							for img in self.albums[page][album]['imgs']:
								img_link = img
								if img_link == "video": continue
								img_title = re.findall(r'/((?:(?!/).)*)$', img_link)[0].split('.')[0] #/((?:(?!/).)*)$
								path = f"{OUTPUT_PATH}/fotos_yupoo/{album}/{img_title}.jpeg"
								if os.path.exists(path) == True:
									continue
								self.tasks.append(asyncio.ensure_future(self.async_req(img_link, self.get_imgs)))
					if len(self.tasks) > 0:
						self.console.print('\n[#6149ab]Baixando as imagens dos álbuns[#6149ab]')
						with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
							logger.info(f"[all_albums] downloading imgs in albums: {len(self.tasks)}")
							await self._(self.tasks, self.get_imgs)
				else:
						for album in self.albums:
							for img in self.albums[album]['imgs']:
								if img == "video":
									continue
								img_link = img
								if img_link == "video": continue
								img_title = re.findall(r'/((?:(?!/).)*)$', img_link)[0].split('.')[0] #/((?:(?!/).)*)$
								path = f"{OUTPUT_PATH}/fotos_yupoo/{album}/{img_title}.jpeg"
								if os.path.exists(path) == True:
									continue
								self.tasks.append(asyncio.ensure_future(self.async_req(img_link, self.get_imgs)))
						if len(self.tasks) > 0:
							logger.info(f"[all_albums == False] downloading imgs in albums: {len(self.tasks)}")
							self.console.print('\n[#6149ab]Baixando as imagens dos álbuns[#6149ab]')
							with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
								await self._(self.tasks, self.get_imgs)
								
				logger.info(self.now())
				logger.info(f"finish: {round(perf_counter() - self.start_time_class, 2)}")

		async def async_req(self, url, function = None):
			timeout_ = [self.timeout.connect, self.timeout.sock_read]

			def auto_timeout(timeout, control, errors, e, add, type):
				if errors[0] != 0:
					if type == "connect":
						difference = timeout_[0] != self.oldtimeout[0]
					elif type == "read":
						difference = timeout_[1] != self.oldtimeout[1]
					if difference:
						control[0] = 0
						errors[0] = 0
						return
					if control[0] // errors[0] <= e:
						self.oldtimeout = [self.timeout.connect, self.timeout.sock_read]
						timeout[0] += add
						control[0] = 0
						errors[0] = 0
						self.timeout = aiohttp.ClientTimeout(connect=self.timeout_connect[0], sock_read=self.timeout_read[0])
						logger.info(f"timeout: {self.timeout}")
					else:
						control[0] = 0
						errors[0] = 0
				else:
					control[0] = 0
					errors[0] = 0

			if self.connect_control[0] // 10 >= 1:
				auto_timeout(self.timeout_connect, self.connect_control, self.connect_errors, 4, 4, "connect")
			if self.read_control[0] // 10 >= 1:
				auto_timeout(self.timeout_read, self.read_control, self.read_errors, 4, 4, "read")

			self.connect_control[0] +=1
			self.read_control[0] +=1
			
			async with self.sem:
				async def req():
					try:
						if len(self.connections_alive) < 120 or url in self.connections_alive:
							if url not in self.connections_alive:
								self.connections_alive.append(url)
							async with self.session.get(url, timeout=self.timeout, headers=self.headers, ssl=sslcontext) as resp:
								if resp.status == 200:
									self.connections_alive.pop(self.connections_alive.index(url))
									if 'get_imgs' in repr(function):
										await function([await resp.read(), resp.status, url])
									else:
										self.bar()
										await function([await resp.text(), resp.status, url])
								else:
									await asyncio.sleep(2)
									await req()
						else:
							await asyncio.sleep(0.3)
							await req()
					except self.FatalException:
						raise self.FatalException()
					except TimeoutError:
						logger.info('error: TimeoutError')
						await req()
					except aiohttp.ServerDisconnectedError:
						logger.info('error: ServerDisconnectedError')
						await req()
					except aiohttp.ClientPayloadError:
						logger.info('error: ClientPayloadError')
						await req()
					except aiohttp.ClientError:
						logger.info('error: ClientError')
						await req()
					except Exception as e:
						if "Timeout on reading data from socket" in str(e):
							self.read_errors[0] += 1
						elif "Connection timeout to host" in str(e):
							self.connect_errors[0] += 1
						elif "TimeoutError: [Errno 10060] Connect call failed" in str(e):
							logger.info(e)
							await req()
						elif "[WinError 10054]" in str(e):
							logger.info(e)
							await req()
						elif url == str(e):
							self.error = 'link inválido!"'
							raise self.FatalException()
						elif "No space left on device" in str(e):
							self.error = 'sem espaço no computador para baixar as imagens!"'
							raise self.FatalException()
						else:
							logger.info(f"erro async: {e}")
							self.error = 'erro async!'
							raise self.FatalException()
						await req()
				await req()

		def get_pages(self):
			try:
				url = f"{self.urls}/albums?tab=gallery&page=1"
				while True:
					logging.info('getting pages')
					resp = requests.get(url)
					if resp.status_code == 200:
						logging.info('pages 200')
						break
					logger.info("getting pages again")

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
				elif pages == None:
					sleep(1)
					self.get_pages()
				else:
					sleep(1)
					self.get_pages()
			except Exception as e:
				sleep(1)
				self.get_pages()

		async def get_albums(self, page):
			num_page = str(regex.findall(r"&page=(.+)", page[2])[0])
			page = page[0]
			

			self.albums[num_page] = {}
			soup = BeautifulSoup(page.encode("ascii", "ignore").decode("utf-8"), "lxml")
			for album in soup.find_all("a", {"class": "album__main"}):
				title = await self.parse_title(album.get('title'))
				if title == '':
					title = await self.parse_title('blank')
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
				self.error = 'não encontrado imagens no álbum, link potencialmente inválido!'
				raise self.FatalException()
			for img in album_div:
				typee_ = img.select_one(".image__imagewrap")
				if typee_.get("data-type") == "video":
					album_imgs_links.append(f"video")
					continue
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
				if title == '':
					title = await self.parse_title('blank')
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

			path = f"{OUTPUT_PATH}/fotos_yupoo/{album}"
			if os.path.exists(path) == False:
				os.makedirs(path)

			try:
				async with aiofiles.open(f'{OUTPUT_PATH}/fotos_yupoo/{album}/{img_title}.jpeg', mode='wb') as f:
					img = Image.open(BytesIO(r[0]))
					img = img.convert('RGB')
					if "exif" in img.info:
						try:
							exif_dict = piexif.load(img.info["exif"])
							del exif_dict['thumbnail']
							del exif_dict['1st']
							try:
								del exif_dict['Exif'][piexif.ExifIFD.SceneType]
							except:
								pass
							if piexif.ImageIFD.Orientation in exif_dict["0th"]:
								orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)
								exif_bytes = piexif.dump(exif_dict)

								if orientation == 2:
									img = img.transpose(Image.FLIP_LEFT_RIGHT)
								elif orientation == 3:
									img = img.rotate(180)
								elif orientation == 4:
									img = img.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
								elif orientation == 5:
									img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
								elif orientation == 6:
									img = img.rotate(-90, expand=True)
								elif orientation == 7:
									img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
								elif orientation == 8:
									img = img.rotate(90, expand=True)

								img_byte_arr = BytesIO()
								img.save(img_byte_arr, exif=exif_bytes, format='JPEG')
								img_byte_arr = img_byte_arr.getvalue()
								await f.write(img_byte_arr)
						except Exception as e:
							keys = await self.find_key(self.albums, r[2])
							if self.all_albums:
								key = self.albums[keys[0]][keys[1]]['album_link']
							else:
								key = self.albums[keys[0]]['album_link']
							if 'unpack requires a buffer of' in repr(e):
								logger.info(f'{e}:  [{key}, {r[2]}]')
								await f.write(r[0])
							else:
								logger.info(f'{traceback.format_exc()}')
								logger.info(f'{e}:  [{key}, {r[2]}]')
								try:
									await f.write(r[0])
								except:
									self.error = e
									raise self.FatalException()
						else:
							await f.write(r[0])
					else:
						await f.write(r[0])
				self.bar()
			except Exception as e:
				keys = await self.find_key(self.albums, r[2])
				if self.all_albums:
					key = self.albums[keys[0]][keys[1]]['album_link']
				else:
					key = self.albums[keys[0]]['album_link']
				logger.info(traceback.format_exc())
				logger.info(f'error write file URL: [{key}, {r[2]}]')
				self.error = f'error write file: {e}'
				raise self.FatalException

		async def _(self, tasks, function):
			try:
				self.connections_alive = []
				resp = await asyncio.gather(*self.tasks)
			except self.FatalException:
				for task in self.tasks:
					task.cancel()
				raise Exception(self.error)


		async def parse_title(self, title):
			title = title.replace('.', '_').replace('/', '_').replace(':', '').replace('"', '').replace("'", '').replace('*','')
			title = title.strip()
			it = 0
			while True:
				it+=1
				if it == 1:
					if await self.find_key(self.albums, title) == None and self.all_albums:
						break
					elif title not in self.albums:
						break
				else:
					if await self.find_key(self.albums, f"{title} - {str(it)}") == None and self.all_albums:
						title = f"{title} - {str(it)}"
						break
					elif f"{title} - {str(it)}" not in self.albums:
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