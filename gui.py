import os
import asyncio
from time import sleep
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
import rich.prompt as prompt

from app import YupooDownloader
from edit_rich import make_prompt, render_default

clear = lambda: os.system("cls")
clear()

class App():
	def __init__(self):
		self.console = Console(color_system="auto")
		self.st1np = self.parse_nick()

	def main(self):
		self.default()
		self.console.print("\nPrograma desenvolvido para te ajudar a baixar \nimagens com qualidade para postagem do site da [#66b381]Yupoo[/]!")
		self.console.print("\n[b #6149ab]Opções[/]")
		self.console.print("[b #baa6ff]1.[/] Baixe todas as imagens de todos os álbuns. ([bold u #c7383f]pesado[/])")
		self.console.print("[b #baa6ff]2.[/] Baixar apenas a foto principal de todos álbuns.")
		self.console.print("[b #baa6ff]3.[/] Inserir álbuns para baixar todas as fotos.")
		self.console.print("[b #baa6ff]4.[/] Inserir álbuns para baixar apenas a foto principal.")

		self.edit_rich()
		opt = prompt.Prompt.ask("\n[b #6149ab]>>[/]  Selecione uma opção", choices=["1", "2", "3", "4"], default="4")
		# self.console.print('\nCancele a qualquer momento apertando [b u #c7383f]CTRL C[/]!')
		clear()
		self.default()
		self.execute_answer(opt)

	def execute_answer(self, opt):
		try:
			selected_print = lambda option, text: self.console.print(f"\nOpção [b #6149ab]{option}[/] selecionada: [b #baa6ff]{text}[/]")
			if opt == "1" or opt == "2":
				if opt == "1":
					selected_print_ = lambda: selected_print("1", "Baixando todas as fotos do catálogo!")
					selected_print_()
					self.console.print("\nInsira o link do catálogo.")
					url = prompt.Prompt.ask("[#6149ab b]link[/]")
					clear()
					self.default()
					selected_print_()
					asyncio.run(YupooDownloader(all_albums=True, urls=url, cover=False).main())
				else:
					selected_print_ = lambda: selected_print("2", "Baixando todas as fotos principais do catálogo!")
					selected_print_()
					self.console.print("\nInsira o link do catálogo.")
					url = prompt.Prompt.ask("[#6149ab b]link[/]")
					clear()
					self.default()
					selected_print_()
					asyncio.run(YupooDownloader(all_albums=True, urls=url, cover=True).main())
			elif opt == "3" or opt == "4":
				if opt == "3":
					selected_print_ = lambda: selected_print("3", "Baixando todas as fotos dos álbuns selecionados!")
					selected_print_()
				else:
					selected_print_ = lambda: selected_print("4", "Baixando todas as fotos principais dos álbuns selecionados!")
					selected_print_()
				self.console.print("\nInsira os links dos álbuns para download. ([#baa6ff]digite [u b]ok[/] para executar![/])")
				urls = []
				while True:
					url = prompt.Prompt.ask("[#6149ab b]link[/]")
					if url == "ok":
						break
					urls.append(url)
				if opt == "3":
					clear()
					self.default()
					selected_print_()
					asyncio.run(YupooDownloader(all_albums=False, urls=urls, cover=False).main())
				else:
					clear()
					self.default()
					selected_print_()
					asyncio.run(YupooDownloader(all_albums=False, urls=urls, cover=True).main())
		except Exception as e:
			self.console.print(f"\n[b #c7383f]erro: {e}[/]")

	def default(self):
		self.console.print(self.st1np)
		self.console.print(Panel.fit("[#ffffff]Considere ajudar o [bold #4912ff]PROJETO[/][/]!\n[#ffffff]Chave [bold u #05a62a]PIX[/]: [bold #00ff73]xxxxxxx[/]", title="[blink #4912ff]***[/]", subtitle="[blink #4912ff]***[/]"))

	def edit_rich(self):
		def choices_style(style='prompt.choices'):
			prompt.PromptBase.make_prompt = make_prompt(style=style, DefaultType=prompt.DefaultType, Text=Text)
		def default_style(style='prompt.default', path="Confirm"):
			if path == "Confirm":
				prompt.Confirm.render_default = render_default(path=path, style=style,DefaultType=prompt.DefaultType, Text=Text)
			elif path == "Prompt":
				prompt.PromptBase.render_default = render_default(path=path,style=style,DefaultType=prompt.DefaultType, Text=Text)

		prompt.Confirm.choices = ['s', 'n']
		prompt.Confirm.validate_error_message = 'Digite apenas [bold #0ba162]S[/] e [bold #c7383f]N[/]\n'
		prompt.PromptBase.illegal_choice_message = '[#c7383f]Por favor, selecione uma das opções disponíveis'
		choices_style('bold #baa6ff')
		default_style('bold #baa6ff')
		default_style('bold #6149ab', 'Prompt')

	def parse_nick(self):
		nick = Text('''
       __  ___          
  ___ / /_<  /___   ___ 
 (_-</ __// // _ \ / _ \\
/___/\__//_//_//_// .__/
                 /_/  
		''', style='bold #4912ff')
		def change_color(regex_list, color):
			for regex in regex_list:
				nick.highlight_regex(regex, color)

		regex_1 = [r'  ___    ', r'<  /', r'// //', r'//_//'] # #baa6ff
		regex_2 = [r'/ _ ', r' __/', r'\\__/', r'_//_// \.__/'] # #4912ff
		change_color(regex_1, 'b #baa6ff')
		change_color(regex_2, 'b #4912ff')
		
		return nick

try:
	clear()
	app = App().main()
	sleep(10)
except KeyboardInterrupt:
	clear()
	app = None
	clear()