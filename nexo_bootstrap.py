import subprocess
import os

def run(cmd):
    log.info(f"Running: {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

log.info("Starting Nexo Bootstrap...")
# Install python and deps
res = run("pkg install python -y")
log.info(res.stdout)
res = run("pip install requests psutil")
log.info(res.stdout)

# Setup .bashrc
bashrc_content = """
export NEXO_BACKEND=http://192.168.100.22:8000
export NEXO_AGENT_ID=xiaomi-mobile-01
"""
with open(os.path.expanduser("~/.bashrc"), "a") as f:
    f.write(bashrc_content)

log.info("Bootstrap complete. Run 'source ~/.bashrc && python nexo_mobile_agent.py --interactivo'")
