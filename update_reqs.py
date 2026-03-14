import re

with open('requirements.txt', 'r') as f:
    lines = f.readlines()

remove_packages = {'chromadb', 'moviepy', 'APScheduler', 'secure-smtplib', 'google-generativeai'}
pin_packages = {
    'fastapi': 'fastapi==0.115.5',
    'uvicorn': 'uvicorn[standard]==0.32.1',
    'pydantic': 'pydantic==2.10.2',
    'sqlalchemy': 'SQLAlchemy==2.0.36',
    'celery': 'celery==5.4.0',
    'redis': 'redis==5.2.0',
    'anthropic': 'anthropic==0.40.0',
    'openai': 'openai==1.58.1',
    'google-genai': 'google-genai==1.0.0',
    'psutil': 'psutil==6.1.0',
    'qdrant-client': 'qdrant-client==1.12.0',
    'faster-whisper': 'faster-whisper',
    'gTTS': 'gTTS',
    'pydub': 'pydub'
}

new_lines = []
existing_packages = set()

for line in lines:
    line_clean = line.strip()
    if not line_clean or line_clean.startswith('#'):
        new_lines.append(line)
        continue
    
    pkg_name = re.split(r'[=><~\[]', line_clean)[0].strip()
    
    if pkg_name in remove_packages:
        continue
        
    for p_key, p_val in pin_packages.items():
        if pkg_name.lower() == p_key.lower():
            new_lines.append(p_val + '\n')
            existing_packages.add(p_key.lower())
            break
    else:
        new_lines.append(line)
        existing_packages.add(pkg_name.lower())

for p_key, p_val in pin_packages.items():
    if p_key.lower() not in existing_packages:
        new_lines.append(p_val + '\n')

with open('requirements.txt', 'w') as f:
    f.writelines(new_lines)

print("requirements.txt updated successfully")
