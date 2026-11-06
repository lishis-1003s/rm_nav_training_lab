"""Local supervisor: the HTTP service survives ROS launch mode changes."""
import errno
import functools
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import yaml
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from ament_index_python.packages import get_package_share_directory

MODES = {'localization': 'localization', 'sim': 'sim_only', 'slam': 'slam_nav2', 'navigation': 'known_map'}

class Supervisor:
    def __init__(self, share):
        self.share = share
        self.defaults = yaml.safe_load((share/'config/experience_defaults.yaml').read_text())
        self.process = None
        self.mode = None
        self.lock = threading.Lock()
        self.log = open(Path.cwd() / 'training_runtime.log', 'a')

    def status(self):
        code = self.process.poll() if self.process else None
        return {'running': self.process is not None and code is None, 'mode': self.mode,
                'exit_code': code, 'default_map': str(self.share/'maps'/self.defaults['map']), 'default_mode': self.defaults['mode'], 'maps': [str(p) for p in sorted((self.share/'maps').glob('*.yaml'))]}

    def stop(self):
        if self.process:
            try:
                os.killpg(self.process.pid, signal.SIGINT)
            except ProcessLookupError:
                return
            try:
                self.process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGTERM)
                try:
                    self.process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait()
            # A failed launch can leave children even after its own exit.
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def start(self, data):
        mode = data.get('mode', self.defaults['mode'])
        if mode not in MODES:
            raise ValueError('Unknown mode')
        map_path = Path(data.get('map') or self.share/'maps'/self.defaults['map']).expanduser().resolve()
        if not map_path.is_file() or map_path.suffix not in ('.yaml', '.yml'):
            raise ValueError('Map YAML does not exist')
        # Validate before stopping the current experiment.
        from .simulator import TrainingSimulator
        TrainingSimulator._load_pgm(map_path)
        radius = float(data.get('radius', .3))
        if not .05 <= radius <= 1:
            raise ValueError('Radius must be 0.05–1.0 m')
        self.stop()
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('127.0.0.1', 9090))
            except OSError as exc:
                raise ValueError('另一个实验已占用 9090。请在原实验终端按 Ctrl+C，再从网页启动；网页不能停止其他终端的实验。') from exc
        self.mode = mode
        self.process = subprocess.Popen(['ros2', 'launch', 'rm_nav_training_lab', MODES[mode]+'.launch.py',
            'serve_web:=false', 'rviz:=false', 'map:='+str(map_path), 'robot_radius:='+str(radius)],
            start_new_session=True, stdout=self.log, stderr=subprocess.STDOUT)

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def reply(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/runtime':
            return self.reply(200, self.server.supervisor.status())
        return super().do_GET()

    def do_POST(self):
        # Local UI only; reject cross-origin browser mutations and DNS rebinding.
        if self.headers.get('Host') not in ('localhost:8080', '127.0.0.1:8080') or self.headers.get('Origin') not in (None, 'http://localhost:8080', 'http://127.0.0.1:8080'):
            return self.reply(403, {'error': 'Local origin required'})
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length > 8192:
                raise ValueError('Request too large')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object')
            with self.server.supervisor.lock:
                if self.path == '/api/start':
                    self.server.supervisor.start(data)
                elif self.path == '/api/stop':
                    self.server.supervisor.stop()
                else:
                    return self.reply(404, {'error': 'Unknown operation'})
            self.reply(200, self.server.supervisor.status())
        except (ValueError, OSError, KeyError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})

def main():
    share = Path(get_package_share_directory('rm_nav_training_lab'))
    try:
        server = ThreadingHTTPServer(('127.0.0.1', 8080), functools.partial(Handler, directory=str(share/'web')))
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        print(
            '无法启动：127.0.0.1:8080 已被占用。\n'
            '若已有本平台网页服务，直接访问 http://localhost:8080，无需重复启动。\n'
            '若要重新启动，请在原服务终端按 Ctrl+C；可用以下命令检查占用进程：\n'
            "  ss -ltnp 'sport = :8080'\n"
            '不要同时运行 training_server 和独立 Launch 的静态网页服务；'
            '使用常驻网页时，实验 Launch 请传入 serve_web:=false。',
            file=sys.stderr, flush=True)
        return 1
    server.supervisor = Supervisor(share)
    print('Training UI: http://localhost:8080', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.supervisor.stop()
        server.server_close()
        server.supervisor.log.close()
