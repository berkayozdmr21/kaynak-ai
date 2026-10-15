"""User-session launcher: choose a free port, verify readiness, open browser."""
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

root = Path(os.path.abspath(__file__)).parent
os.chdir(root)
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
url = f'http://127.0.0.1:{port}'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
log_path = root / 'baslatma.log'
with log_path.open('w', encoding='utf-8') as log:
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app',
                                '--host', '127.0.0.1', '--port', str(port)],
                               stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError('Sunucu baslatilamadi.')
            try:
                with opener.open(url + '/api/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError('Sunucu zamaninda yanit vermedi.')
        print('\nUygulama hazir: ' + url, flush=True)
        print('Bu pencere acik kalmali. Durdurmak icin Ctrl+C.', flush=True)
        webbrowser.open(url)
        process.wait()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(str(error), flush=True)
        print('Hata kaydi: ' + str(log_path), flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
