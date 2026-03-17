import re

path = 'NEXO_CORE/agents/web_ai_supervisor.py'
content = open(path, encoding='utf-8').read()

# Eliminar cualquier snapshot mal pegado
content = re.sub(r'\n\ndef snapshot.*?}\n', '', content, flags=re.DOTALL)
content = re.sub(r'\n    def snapshot.*?}\n', '', content, flags=re.DOTALL)

# Buscar el final de la clase y agregar el método correctamente
method = '''
    def snapshot(self):
        return {
            "status": "running" if self._running else "stopped",
            "poll_seconds": 30
        }
'''

# Insertar antes de la última línea del archivo
content = content.rstrip() + '\n' + method

open(path, 'w', encoding='utf-8').write(content)
log.info('DONE')
