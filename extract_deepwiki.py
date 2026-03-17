import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

url = "https://deepwiki.com/Reidskar/NEXO_SOBERANO"
html = requests.get(url).text
soup = BeautifulSoup(html, "html.parser")
content = soup.find("main")
markdown = md(str(content))
with open("nexo_soberano.md","w",encoding="utf-8") as f:
    f.write(markdown)
