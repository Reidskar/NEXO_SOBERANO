import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

base_url = "https://deepwiki.com/Reidskar/NEXO_SOBERANO"
html = requests.get(base_url).text
soup = BeautifulSoup(html, "html.parser")

# Extraer todos los enlaces de secciones
section_links = []
for a in soup.select('nav a[href]'):
    href = a['href']
    if href.startswith('/Reidskar/NEXO_SOBERANO/'):
        section_links.append('https://deepwiki.com' + href)

# Extraer contenido de cada sección
markdown_parts = []
for url in [base_url] + section_links:
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    if main:
        md_content = md(str(main))
        markdown_parts.append(f"\n\n# {url}\n\n" + md_content)

full_markdown = '\n\n'.join(markdown_parts)

with open("nexo_soberano.md","w",encoding="utf-8") as f:
    f.write(full_markdown)
