# skills/scripts/server_utils.py
import os
import socket
import subprocess
import sys
import time

import httpx

SERVER_PORT = int(os.environ.get("GIRLFRIEND_AGENT_PORT", "18012"))
SERVER_HOST = os.environ.get("GIRLFRIEND_AGENT_HOST", "localhost")
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"


def is_server_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((SERVER_HOST, SERVER_PORT))
            return True
        except (ConnectionRefusedError, OSError):
            return False


def wait_for_server(timeout: int = 10) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"{SERVER_URL}/health", timeout=1)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def ensure_server_running() -> bool:
    if is_server_running():
        return True

    project_root = _find_project_root()
    if project_root is None:
        print("Error: Cannot find girlfriend-agent project root", file=sys.stderr)
        return False

    cmd = [sys.executable, "-m", "src.engine_server"]
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW on Windows

    proc = subprocess.Popen(
        cmd,
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )

    if wait_for_server(timeout=10):
        return True

    print("Error: Server failed to start within 10 seconds", file=sys.stderr)
    return False


def _find_project_root() -> str | None:
    import os
    current = os.path.abspath(__file__)
    # skills/scripts/server_utils.py -> project root (3 levels up)
    return os.path.dirname(os.path.dirname(os.path.dirname(current)))