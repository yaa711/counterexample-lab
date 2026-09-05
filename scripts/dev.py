"""Start both local development servers; terminate children when either exits."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    npm = shutil.which('npm')
    if not npm or not (ROOT / 'frontend/node_modules').exists():
        sys.exit('Install Node.js and run: npm --prefix frontend ci')
    children = []
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        for command, cwd in [([sys.executable, '-m', 'backend.server'], ROOT),
                             ([npm, 'run', 'dev'], ROOT / 'frontend')]:
            children.append(subprocess.Popen(command, cwd=cwd, start_new_session=os.name != 'nt'))
        print('Workbench: http://127.0.0.1:5173 — Ctrl+C stops both servers', flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(.2)
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                if os.name == 'nt':
                    child.terminate()
                else:
                    os.killpg(child.pid, signal.SIGTERM)
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    child.kill()
                else:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == '__main__':
    main()
