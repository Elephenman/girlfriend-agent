# skills/scripts/server_utils.py
import socket
import subprocess
import sys
import time

import httpx

SERVER_PORT = 18012
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"


def is_server_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect(("127.0.0.1", SERVER_PORT))
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
    CREATE_NO_WINDOW = 0x08000000  # Windows only
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = CREATE_NO_WINDOW

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