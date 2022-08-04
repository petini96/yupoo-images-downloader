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

	logger.info("start v1.4.1")

	import winshell
	from win32com.client import Dispatch
	import asyncio
	import re
	import aiohttp
	import aiofiles
	from bs4 import BeautifulSoup
	import lxml
	import regex
	from time import perf_counter
	from alive_progress import alive_bar
	from rich.console import Console
	import traceback
	import piexif
	from PIL import ImageFile
	ImageFile.LOAD_TRUNCATED_IMAGES = True
	from PIL import Image as Image
	from io import BytesIO
	from copy import deepcopy

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
			self.normpath = lambda path: os.path.normpath(path)

			self.headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36', 'referer': "https://yupoo.com/"}
			self.timeout_connect = [30]
			self.connect_control = [0]
			self.connect_errors = [0]

			self.timeout_read = [30]
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
					self.pages = await self.get_pages()
					#getting albums from pages resp
					self.tasks = []
					for page in self.pages:
						self.tasks.append(asyncio.ensure_future(self.async_req(page, self.get_albums)))
					logger.info(f"[all_albums] getting albums from pages resp: {len(self.tasks)}")
					self.console.print("\n[#6149ab]Pegando álbuns das páginas[/]")
					self.start_time = perf_counter()
					with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
						await self._(self.tasks, self.get_albums)
					logger.info(self.now())

					#getting images from albums resp
					self.tasks = []
					for catalog in self.albums:
							for album in self.albums[catalog]:
								self.tasks.append(asyncio.ensure_future(self.async_req(self.albums[catalog][album]['album_link'], self.get_album)))
					logger.info(f"[all_albums] getting images from albums resp: {len(self.tasks)}")
					self.console.print("\n[#6149ab]Pegando as imagens dos álbuns[/]")
					with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
						self.start_time = perf_counter()
						if len(self.tasks) > 0:
							await self._(self.tasks, self.get_album)
					logger.info(self.now())

				else:
					#getting images from albums resp
					categories = []
					self.tasks = []
					for url in self.urls:
						if 'categories' in url or 'collections' in url:
							categories.append(url)
					if len(categories) > 0:
						self.tasks_cat = []
						categories_ = []
						for cat in categories:
							rx = re.findall(r'(?<=\?)(.*?)(?=$)', cat)
							rx = rx[0] if len(rx) > 0 else None
							new_cat = cat
							if rx != None:
								new_cat = ''
								for i, st in enumerate(cat.split(rx)):
									if st.strip() == '':
										continue
									if i != 0:
										new_cat+=f' {st.strip()}'
									else:
										new_cat+=st.strip()
								new_cat = new_cat[:-1]
							categories_.append(new_cat) if new_cat not in categories_ else None
						for cat in categories_:
							self.tasks_cat.append(asyncio.ensure_future(self.get_pages(cat)))
						resp = await self._(self.tasks_cat)
						self.tasks_cat = []
						for category in resp:
							if category == None:
								continue
							name_catalog = re.findall(r'(?<=https:\/\/)(.*?)(?=\.com)', category[0][0])[0]
							name_catalog = re.findall(r'(?<=^)(.*?)(?=\.x)', name_catalog)[0]
							if name_catalog not in self.albums:
								self.albums[name_catalog] = {}
							self.category_title = category[1]
							if 'categories' in category[0][0]:
								self.category_id = re.findall(r'(?<=categories\/)(.*?)(?=\?)', category[0][0])[0]
							elif 'collections' in category[0][0]:
								self.category_id = re.findall(r'(?<=collections\/)(.*?)(?=\?)', category[0][0])[0]
							if self.category_title == "":
								self.category_title = f'blank - {self.category_id}'
							else:
								self.category_title = await self.parse_title(self.category_title, name_catalog, True)
							for page in category[0]:
								self.tasks_cat.append(asyncio.ensure_future(self.async_req(page, self.get_albums, [self.category_title, self.category_id])))
						if len(self.tasks_cat) > 0:
							self.console.print("\n[#6149ab]Pegando álbuns das categorias[/]")
							with alive_bar(len(self.tasks_cat), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
								resp = await self._(self.tasks_cat)
							for catalog in self.albums:
								for album in self.albums[catalog]:
									self.tasks.append(asyncio.ensure_future(self.async_req(self.albums[catalog][album]['album_link'], self.get_album)))
					
					urls = []
					for url in self.urls:
						if 'categories' not in url and 'collections' not in url:
							rx = re.findall(r'(?<=\?)(.*?)(?=$)', url)
							rx = rx[0] if len(rx) > 0 else None
							new_url = url
							if rx != None:
								new_url = ''
								for i, st in enumerate(url.split(rx)):
									if st.strip() == '':
										continue
									if i != 0:
										new_url+=f' {st.strip()}'
									else:
										new_url+=st.strip()
								new_url += 'uid=1'
							urls.append(new_url) if new_url not in urls else None

					for url in urls:
						_ = (await self.find_key(self.albums, url))
						if _ == None:
							self.tasks.append(asyncio.ensure_future(self.async_req(url, self.get_album)))

					self.start_time = perf_counter()
					if len(self.tasks) > 0:
						logger.info(f"[all_albums == False] getting images from albums resp: {len(self.tasks)}")
						self.console.print("\n[#6149ab]Pegando as imagens dos álbuns[/]")
						with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
							await self._(self.tasks, self.get_album)
					logger.info(self.now())
				
				#downloading imgs in albums
				self.tasks=[]	
				self.start_time = perf_counter()
				if self.all_albums:
					for catalog in self.albums:
							for album in self.albums[catalog]:
								name_catalog = catalog
								if 'imgs' in self.albums[catalog][album]:
									for img in self.albums[catalog][album]['imgs']:
										img_link = img
										if img_link == "video": continue
										img_title = re.findall(r'/((?:(?!/).)*)$', img_link)[0].split('.')[0] #/((?:(?!/).)*)$
										path = f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/{album}/{img_title}.jpeg"
										if os.path.exists(path):
											without_category_path = f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/sem categoria/{album}.lnk"
											if os.path.exists(without_category_path):
												os.unlink(without_category_path)
												if len(os.listdir(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/sem categoria/")) == 0:
													os.rmdir(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/sem categoria/")
												album_path = self.albums[catalog][album]
												if 'category_title' in album_path:
													save_path = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/{album_path['category_title']}/")
													target = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/{album}")  # The shortcut target file or folder
													work_dir = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/")  # The parent folder of your file

													shell = Dispatch('WScript.Shell')

													if os.path.exists(save_path) == False:
														os.makedirs(save_path)
													shortcut = shell.CreateShortCut(f"{save_path}\{album}.lnk")
													shortcut.Targetpath = target
													shortcut.WorkingDirectory = work_dir
													shortcut.save()
													
											continue
										self.tasks.append(asyncio.ensure_future(self.async_req(img_link, self.get_imgs)))
					if len(self.tasks) > 0:
						self.console.print('\n[#6149ab]Baixando as imagens dos álbuns[#6149ab]')
						with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
							logger.info(f"[all_albums] downloading imgs in albums: {len(self.tasks)}")
							await self._(self.tasks, self.get_imgs)
				else:
						for catalog in self.albums:
							for album in self.albums[catalog]:
								name_catalog = catalog
								if 'imgs' in self.albums[catalog][album]:
									for img in self.albums[catalog][album]['imgs']:
										if img == "video":
											continue
										img_link = img
										if img_link == "video": continue
										img_title = re.findall(r'/((?:(?!/).)*)$', img_link)[0].split('.')[0] #/((?:(?!/).)*)$
										path = f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/{album}/{img_title}.jpeg"
										if os.path.exists(path):
											without_category_path = f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/sem categoria/{album}.lnk"
											if os.path.exists(without_category_path):
												os.unlink(without_category_path)
												if len(os.listdir(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/sem categoria/")) == 0:
													os.rmdir(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/sem categoria/")
												album_path = self.albums[catalog][album]
												if 'category_title' in album_path:
													save_path = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/{album_path['category_title']}/")
													target = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/{album}")  # The shortcut target file or folder
													work_dir = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/")  # The parent folder of your file

													shell = Dispatch('WScript.Shell')

													if os.path.exists(save_path) == False:
														os.makedirs(save_path)
													shortcut = shell.CreateShortCut(f"{save_path}\{album}.lnk")
													shortcut.Targetpath = target
													shortcut.WorkingDirectory = work_dir
													shortcut.save()
													
											continue
										self.tasks.append(asyncio.ensure_future(self.async_req(img_link, self.get_imgs)))
						self.start_time = perf_counter()
						if len(self.tasks) > 0:
							logger.info(f"[all_albums == False] downloading imgs in albums: {len(self.tasks)}")
							self.console.print('\n[#6149ab]Baixando as imagens dos álbuns[#6149ab]')
							with alive_bar(len(self.tasks), length=35, bar="squares", spinner="classic", elapsed="em {elapsed}") as self.bar:
								await self._(self.tasks, self.get_imgs)
						logger.info(self.now())
								
				logger.info(f"finish: {round(perf_counter() - self.start_time_class, 2)}")

		async def async_req(self, url, function = None, category = None):
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


			
			async with self.sem:
				async def req():
					self.connect_control[0] +=1
					self.read_control[0] +=1
					if self.connect_control[0] // 10 >= 1:
						auto_timeout(self.timeout_connect, self.connect_control, self.connect_errors, 4, 8, "connect")
					if self.read_control[0] // 10 >= 1:
						auto_timeout(self.timeout_read, self.read_control, self.read_errors, 4, 8, "read")
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
										if category != None:
											await function([await resp.text(), resp.status, url, category])
										else:
											await function([await resp.text(), resp.status, url])
										self.bar()
								else:
									await asyncio.sleep(0.5)
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
					except Exception as e:
						if "Timeout on reading data from socket" in str(e):
							self.read_errors[0] += 1
						elif "Connection timeout to host" in str(e):
							self.connect_errors[0] += 1
						elif "Connect call failed" in str(e):
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
						await req()
				await req()

		async def get_pages(self, url_ = None):
			try:
				if self.all_albums:
					url = f"{self.urls}/albums?tab=gallery&page=1"
				else:
					url = f"{url_}?page=1"
					if "?" in url_:
						url = f"{url_}&page=1"
				
				timeout = aiohttp.ClientTimeout(total=15)
				session = aiohttp.ClientSession()
				async with session:
					while True:
						logging.info('getting pages')
						try:
							async with session.get(url, timeout=timeout, ssl=sslcontext) as resp:
								if resp.status == 200:
									logging.info('pages 200')
									text = await resp.text()
									soup = BeautifulSoup(text.encode("ascii", "ignore").decode("utf-8"), "lxml")
									if soup.select_one('div.empty_emptymain') == None:				
										try:
											total_pages = soup.select_one('form.pagination__jumpwrap input[name="page"]').get('max')
										except:
											total_pages = 1
										pages = []
										for page in range(1, int(total_pages)+1):
												pages.append(f"{url[:-1]}{page}")
										if type(pages) == list:
											if None in pages:
												await asyncio.sleep(0.2)
												return await self.get_pages(url_)
											else:
												if url_ != None:
													category_title = soup.select_one('.alert__title').text.replace("'", "").replace('"', '')
													return [pages, category_title]
												return pages
										elif pages == None:
											await asyncio.sleep(0.2)
											return await self.get_pages(url_)
										else:
											await asyncio.sleep(0.2)
											return await self.get_pages(url_)
									else:
										return None
								logger.info("getting pages again")
						except Exception as e:
							logging.info(f"getting pages again 2: {e}")
							pass
			except aiohttp.ClientConnectionError:
				if resp.status == 200:
					pass
				else:
					await asyncio.sleep(0.2)
					logger.info(f"pages exception: {e}")
					return await self.get_pages(url_)
			except Exception as e:
				await asyncio.sleep(0.2)
				logger.info(f"pages exception: {e}")
				return await self.get_pages(url_)

		async def get_albums(self, page):
			soup = BeautifulSoup(page[0].encode("ascii", "ignore").decode("utf-8"), "lxml")
			name_catalog = re.findall(r'(?<=https:\/\/)(.*?)(?=\.com)', page[2])[0]
			name_catalog = re.findall(r'(?<=^)(.*?)(?=\.x)', name_catalog)[0]
			if self.all_albums:
				if name_catalog not in self.albums:
					self.albums[name_catalog] = {}
				
			base_url = re.findall(r'(?<=https:\/\/)(.*?)(?=\.com)', page[2])[0]
			for album in soup.find_all("a", {"class": "album__main"}):
				href = album.get('href')
				rx = re.findall(r'(?<=\?)(.*?)(?=$)', href)
				rx = rx[0] if len(rx) > 0 else None
				new_href = href
				if rx != None:
					new_href = ''
					for i, st in enumerate(href.split(rx)):
						if st.strip() == '':
							continue
						if i != 0:
							new_href+=f' {st.strip()}'
						else:
							new_href+=st.strip()
					new_href += 'uid=1'

				title = (await self.parse_title(album.get('title'), name_catalog))
				if title == '':
					title = (await self.parse_title('blank', name_catalog))

				if self.all_albums:
					self.albums[name_catalog][title] = {"album_link": self.urls+new_href}
				else:
					self.albums[name_catalog][title] = {"album_link": f"https://{base_url}.com{new_href}", "category_title": page[3][0], "category_id": page[3][1]}


		async def get_album(self, r):
			name_catalog = re.findall(r'(?<=https:\/\/)(.*?)(?=\.com)', r[2])[0]
			name_catalog = re.findall(r'(?<=^)(.*?)(?=\.x)', name_catalog)[0]
			keys = (await self.find_key(self.albums, r[2]))
			keys = keys[0] if keys != None else None
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
				if keys == None:
					if name_catalog not in self.albums:
						self.albums[name_catalog] = {}
					title = soup.select_one("span.showalbumheader__gallerytitle").text
					title = await self.parse_title(title, name_catalog)
					if title == '':
						title = await self.parse_title('blank', name_catalog)
				else:
					title = keys[1]
				if title not in self.albums[name_catalog]:
					self.albums[name_catalog][title] = {}
					self.albums[name_catalog][title]["album_link"] = r[2]
				self.albums[name_catalog][title]["imgs"] = album_imgs_links

		async def get_imgs(self, r):
			keys = (await self.find_key(self.albums, r[2]))[0]
			album_path = self.albums[keys[0]][keys[1]]
			album = keys[1]
			try:
				img_title = re.findall(r'/((?:(?!/).)*)$', r[2])[0].split('.')[0] #/((?:(?!/).)*)$
			except:
				return

			name_catalog = keys[0]
			path = f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/{album}"
			if os.path.exists(path) == False:
				os.makedirs(path)
			
			if "category_title" in album_path:
				save_path = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/{album_path['category_title']}/")
				target = self.normpath(path)  # The shortcut target file or folder
				work_dir = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/")  # The parent folder of your file
			else:
				save_path = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/categorias/sem categoria/")
				target = self.normpath(path)  # The shortcut target file or folder
				work_dir = self.normpath(f"{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/")  # The parent folder of your file

			shell = Dispatch('WScript.Shell')

			if os.path.exists(save_path) == False:
				os.makedirs(save_path)
			shortcut = shell.CreateShortCut(f"{save_path}\{album}.lnk")
			shortcut.Targetpath = target
			shortcut.WorkingDirectory = work_dir
			shortcut.save()

			try:
				async with aiofiles.open(f'{OUTPUT_PATH}/fotos_yupoo/{name_catalog}/albuns/{album}/{img_title}.jpeg', mode='wb') as f:
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
							keys = (await self.find_key(self.albums, r[2]))[0]
							key = self.albums[keys[0]][keys[1]]['album_link']
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
				keys = (await self.find_key(self.albums, r[2]))[0]

				key = self.albums[keys[0]][keys[1]]['album_link']
				logger.info(traceback.format_exc())
				logger.info(f'error write file URL: [{key}, {r[2]}]')
				self.error = f'error write file: {e}'
				raise self.FatalException

		async def _(self, tasks, function = None):
			try:
				self.connections_alive = []
				resp = await asyncio.gather(*tasks)
				return resp
			except self.FatalException:
				for task in self.tasks:
					task.cancel()
				raise Exception(self.error)


		async def parse_title(self, title, catalog, category = False):
			title = title.replace('.', '_').replace('/', '_').replace(':', '').replace('"', '').replace("'", '').replace('*','')
			title = title.strip()
			it = 0
			while True:
				it+=1
				if it == 1:
					if title not in self.albums[catalog] and category == False:
						break
					elif category:
						keys_list = await self.find_key(self.albums[catalog], title)
						have_title = False
						if keys_list != None:
							for keys in keys_list:
								if keys[-1] == "category_title":
									have_title = True
						elif have_title == False or keys_list == None:
							break
				else:
					if f"{title} - {str(it)}" not in self.albums[catalog] and category == False:
						title = f"{title} - {str(it)}"
						break
					elif category:
						keys_list = await self.find_key(self.albums[catalog], f"{title} - {str(it)}")
						have_title = False
						if keys_list != None:
							for keys in keys_list:
								if keys[-1] == "category_title":
									have_title = True
						elif have_title == False or keys_list == None:
							title = f"{title} - {str(it)}"
							break
					else:
						continue
			return title

		async def find_key(self, d: dict, value):
			d, value = deepcopy(d), deepcopy(value)
			def _k(d: dict, value):
				for k,v in d.items():
					if isinstance(v, dict):
							p = _k(v, value)
							if p:
								return [k] + p
					elif isinstance(v, list) == True and k == "imgs":
						if value in v:
							v.remove(value)
							return [k]
					elif v == value:
							del d[k]
							return [k]
			keys = []
			while True:
				k = _k(d, value)
				if k != None:
					keys.append(k)
				else:
					break
			if len(keys) == 0:
				return None
			return keys