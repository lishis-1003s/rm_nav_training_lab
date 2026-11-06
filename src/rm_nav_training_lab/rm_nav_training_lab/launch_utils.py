"""Fail before starting nodes when another experiment owns a required port."""
import socket
from launch.substitutions import LaunchConfiguration

def check_ports(context):
    ports = [('ROSBridge', int(LaunchConfiguration('rosbridge_port').perform(context)))]
    if LaunchConfiguration('serve_web').perform(context).lower() in ('true','1'):
        ports.append(('网页', int(LaunchConfiguration('web_port').perform(context))))
    for label, port in ports:
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('127.0.0.1', port))
            except OSError as exc:
                raise RuntimeError(f'{label} 端口 {port} 已占用，实验未启动。先在原实验终端按 Ctrl+C；网页由 training_server 提供时请使用 serve_web:=false。') from exc
    return []
