#!/usr/bin/env python3
import os
import subprocess
import sys

def main():
    # 仮想環境のアクティベート (もしあれば)
    venv_path = os.path.join(os.path.dirname(__file__), 'venv')
    if os.path.exists(os.path.join(venv_path, 'bin', 'activate')):
        activate_script = os.path.join(venv_path, 'bin', 'activate')
        command = f'. {activate_script} && python app.py'
    elif os.path.exists(os.path.join(venv_path, 'Scripts', 'activate')):
        activate_script = os.path.join(venv_path, 'Scripts', 'activate')
        command = f'call {activate_script} && python app.py'
    else:
        command = 'python app.py'

    print(f"Starting Flask app with command: {command}")
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting Flask app: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
