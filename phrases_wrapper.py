#!/usr/bin/env python3
import urllib.request
import os
from pathlib import Path
import subprocess
import shutil
import time

CONFIG_DIR = "phrases_configs"
APP_NAME = "phrases"

def title():
    _title = f"""
██████╗ ██╗  ██╗██████╗  █████╗ ███████╗███████╗███████╗
██╔══██╗██║  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝
██████╔╝███████║██████╔╝███████║███████╗█████╗  ███████╗
██╔═══╝ ██╔══██║██╔══██╗██╔══██║╚════██║██╔══╝  ╚════██║
██║     ██║  ██║██║  ██║██║  ██║███████║███████╗███████║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
    """
    return _title

def success_text(msg):
    OKGREEN = '\033[92m'
    ENDC = '\033[0m'
    return OKGREEN + msg + ENDC

def download_file(url, filename):
  """Downloads a file from the given URL and saves it as filename."""
  try:
    with urllib.request.urlopen(url) as response, open(filename, 'wb') as out_file:
      data = response.read()
      out_file.write(data)
    #   print(f"File downloaded successfully: {filename}")
  except urllib.error.URLError as e:
    print(f"Error downloading file: {e}")
    
def update_app():
    url = "https://raw.githubusercontent.com/songlinhou/phrases/main/phrases.py"
    config_path = os.path.join(str(Path.home()), CONFIG_DIR)
    app_path = os.path.join(config_path, APP_NAME)
    if os.path.exists(app_path):
        os.remove(app_path)
    download_file(url, app_path)
    subprocess.call(f'chmod +x "{app_path}"', shell=True)
    return app_path


def add_to_path():
    config_path = os.path.join(str(Path.home()), CONFIG_DIR)
    fname = os.path.basename(__file__)
    wrapper_path = os.path.join(config_path, fname)
    if __file__.strip() != wrapper_path.strip(): 
        shutil.copy2(__file__, config_path)
        quick_start = False
    else:
        quick_start = True
    
    bash_rc = os.path.expanduser("~/.bashrc")
    cmd = f"alias {APP_NAME}='python3 \"{wrapper_path}\"'"
    check_cmd = f'cat ~/.bashrc | grep "alias {APP_NAME}="'
    existing_found = True
    try:
        _ = subprocess.check_output(check_cmd, shell=True)
        existing_found = True
    except:
        existing_found = False
    if existing_found:
        # find existing one
        with open(bash_rc, 'r') as f:
            lines = f.readlines()
        target_remove_line_ids = []
        for idx, line in enumerate(lines):
            if line.startswith(f"alias {APP_NAME}="):
                target_remove_line_ids.append(idx)
        
        _ = [lines.remove(lines[id]) for id in target_remove_line_ids]
        lines = [l.rstrip() for l in lines if l.strip() != ""]
        recovered = '\n'.join(lines)
        with open(bash_rc, 'w') as f:
            f.write(recovered)
    run_cmd = f"echo \"\n{cmd}\" >> ~/.bashrc"
    # print("run_cmd=", run_cmd)
    ret = subprocess.call(run_cmd, shell=True)
    if not quick_start:
        print(success_text(f"Open a new terminal and just use command '{APP_NAME}' to start app! Try it!"))
        print(f"Entering in 3 seconds ... Use '{APP_NAME}' to enter app immediately")
        time.sleep(3)
    
                
        
if __name__ == '__main__':
    print(success_text(title()))
    print("Checking for updates ...")
    app_path = update_app()
    add_to_path()
    subprocess.call(f"python3 '{app_path}'", shell=True)