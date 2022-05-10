from rich.prompt import Prompt
import json

urls = []
while True:
    url = Prompt.ask("[#6149ab b]link[/]")
    if url == "ok":
        with open('urls.json', 'w') as f:
            json.dump(urls, f)
        break
    else:
        urls.append(url)