import os

from app import YupooDownloader
import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from config import URLS as urls
clear = lambda: os.system("cls")
clear()
from rich.console import Console

from rich.text import Text

console = Console(color_system="truecolor")


text = Text('''
       __  ___          
  ___ / /_<  /___   ___ 
 (_-</ __// // _ \ / _ \\
/___/\__//_//_//_// .__/
                 /_/  
''', style='bold #4912ff')
text.highlight_regex(r'  ___    ', '#baa6ff')
text.highlight_regex(r'<  /', '#baa6ff')
text.highlight_regex(r'// //', '#baa6ff')
text.highlight_regex(r'/ _ ', '#4912ff')
text.highlight_regex(r' __/', '#4912ff')
text.highlight_regex(r'//_//', '#baa6ff')
text.highlight_regex(r'\\__/', '#4912ff')
text.highlight_regex(r'_//_// .__/', '#4912ff')
def choices_style(style='prompt.choices'):
	prompt.PromptBase.make_prompt = make_prompt(style=style, DefaultType=prompt.DefaultType, Text=Text)

def default_style(style='prompt.default', path="Confirm"):
	if path == "Confirm":
		prompt.Confirm.render_default = render_default(path=path, style=style,DefaultType=prompt.DefaultType, Text=Text)
	else:
		prompt.PromptBase.render_default = render_default(path=path,style=style,DefaultType=prompt.DefaultType, Text=Text)

from rich.panel import Panel
console.print(text)
# console.print(Panel.fit("[#ffffff]Considere ajudar o [bold #4912ff]PROJETO[/][/]!\n[#ffffff]Chave [bold u #05a62a]PIX[/]: [bold #00ff73]xxxxxxx[/]", title="[blink #4912ff]***[/]", subtitle="[blink #4912ff]***[/]"))
console.print("\n[#acabb8]Programa desenvolvido para te ajudar a baixar \nimagens com qualidade para postagem do site da [#66b381]Yupoo[/]![/]")
console.print("\n[b #6149ab]Opções[/]")
console.print("[b #baa6ff]1.[/] [#acabb8]Baixe todas as imagens de todos os álbuns. ([bold u #c7383f]pesado[/][/])")
console.print("[b #baa6ff]2.[/] [#acabb8]Baixar apenas a foto principal de todos álbuns.[/]")
console.print("[b #baa6ff]3.[/] [#acabb8]Inserir álbuns para baixar todas as fotos.[/]")
console.print("[b #baa6ff]4.[/] [#acabb8]Inserir álbuns para baixar apenas a foto principal.[/]")
import rich.prompt as prompt
from edit_rich import	make_prompt, render_default
prompt.Confirm.choices = ['s', 'n']
prompt.Confirm.validate_error_message = 'Digite apenas [bold #0ba162]S[/] e [bold #c7383f]N[/]\n'
choices_style('bold #baa6ff')
default_style('bold #baa6ff')
default_style('bold #6149ab', 'prompt')
prompt.PromptBase.illegal_choice_message = '[#c7383f]Por favor, selecione uma das opções disponíveis\n'

opt = prompt.Prompt.ask("\n[#acabb8]Selecione uma opção[/]", choices=["1", "2", "3", "4"], default="4")
if opt == "3" or opt == "4":
	console.print("[#acabb8]Insira os links dos albuns para download. ([#baa6ff]digite [u b]ok[/] para sair[/][/])")
	print()
	# urls = []
	while True:
		url = prompt.Prompt.ask("[#6149ab b]link[/]")
		if url == "ok":
			break
		else:
			i = 1
			# urls.append(url)
	if opt == "3":
		print('x')
		asyncio.run(YupooDownloader(all_albums=False, urls=urls, cover=False).main())
	else:
		print('c')
		asyncio.run(YupooDownloader(all_albums=False, urls=urls, cover=True).main())
else:
	print(opt)