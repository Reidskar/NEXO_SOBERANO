import os
import glob
from pathlib import Path
import re

CSS_INJECT = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-main: #0a0a0f !important;
    --bg-sec: #111118 !important;
    --accent: #6c63ff !important;
    --accent-2: #00d4ff !important;
  }
  body, .dashboard, .main-content {
    background-color: var(--bg-main) !important;
    font-family: 'Inter', sans-serif !important;
  }
  .card, .feat-card, .sys-panel {
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(0,212,255,0.1) !important;
  }
  h1, h2, h3, .brand {
    font-family: 'Inter', sans-serif !important;
  }
  pre, code, .terminal {
    font-family: 'JetBrains Mono', monospace !important;
  }
</style>
</head>
"""

def process_file(file_path):
    try:
        content = Path(file_path).read_text(encoding='utf-8')
        modified = False
        
        # HTML Injection
        if file_path.endswith('.html'):
            if '<link href="https://fonts.googleapis.com/css2?family=Inter' not in content:
                content = content.replace('</head>', CSS_INJECT, 1)
                modified = True
                
        # JSX specific replacements (Tailwind)
        if file_path.endswith('.jsx'):
            new_content = re.sub(r'bg-gray-9\d\d', 'bg-[#0a0a0f]', content)
            new_content = re.sub(r'bg-gray-8\d\d', 'bg-[#111118]/80 backdrop-blur-md border border-[#00d4ff]/10', new_content)
            new_content = re.sub(r'text-blue-\d\d\d', 'text-[#00d4ff]', new_content)
            new_content = re.sub(r'text-indigo-\d\d\d', 'text-[#6c63ff]', new_content)
            if new_content != content:
                content = new_content
                modified = True
                
        if modified:
            Path(file_path).write_text(content, encoding='utf-8')
            return True
            
    except Exception as e:
        pass
    return False

def main():
    root_dir = r"C:\Users\estef\OneDrive\NEXO_SOBERANO"
    modified_files = []
    
    for ext in ["**/*.html", "**/*.jsx"]:
        for file in glob.glob(os.path.join(root_dir, ext), recursive=True):
            if "node_modules" in file or ".venv" in file:
                continue
            if process_file(file):
                modified_files.append(os.path.relpath(file, root_dir))
                
    log.info("ARCHIVOS_MODIFICADOS=" + ",".join(modified_files))

if __name__ == "__main__":
    main()
