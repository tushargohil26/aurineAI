"""
Aurine AI Assistant - CLI Entry Point
Run anywhere with: python -m app <command>
Or after pip install: aurine <command>
"""
import argparse
import os
import sys
import subprocess
import shutil
from pathlib import Path


BANNER = r"""
    ___                     ______          __
   /   |  __  __________ _ / ____/___  ____/ /__
  / /| | / / / / ___/ __ `/ /   / __ \/ __  / _ \
 / ___ |/ /_/ / /  / /_/ / /___/ /_/ / /_/ /  __/
/_/  |_|\__,_/_/   \__,_/\____/\____/\__,_/\___/
"""


def get_project_dir() -> Path:
    return Path(__file__).parent.parent.resolve()


def ensure_venv(project_dir: Path) -> Path:
    venv_python = project_dir / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "python"
    if not venv_python.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(project_dir / ".venv")], check=True)
        pip = project_dir / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "pip"
        subprocess.run([str(pip), "install", "-r", str(project_dir / "requirements.txt")], check=True)
    return venv_python


def ensure_env(project_dir: Path):
    env_file = project_dir / ".env"
    example = project_dir / ".env.example"
    if not env_file.exists():
        if example.exists():
            shutil.copy(example, env_file)
        else:
            env_file.write_text("AI_PROVIDER=aurine\n")


def cmd_run(args):
    project_dir = get_project_dir()
    ensure_env(project_dir)
    venv_python = ensure_venv(project_dir)
    port = args.port
    host = "0.0.0.0" if args.network else "127.0.0.1"
    print(f"Starting Aurine at http://localhost:{port}")
    if args.network:
        import socket
        try:
            ip = socket.gethostbyname(socket.gethostname())
            print(f"Network access: http://{ip}:{port}")
        except Exception:
            pass
    print("Press Ctrl+C to stop.\n")
    cmd = [str(venv_python), "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)]
    if args.reload:
        cmd.append("--reload")
    subprocess.run(cmd, cwd=str(project_dir))


def cmd_setup(args):
    project_dir = get_project_dir()
    print("Setting up Aurine AI Assistant...")
    ensure_venv(project_dir)
    ensure_env(project_dir)
    print("\nSetup complete! Run: aurine run")


def cmd_stop(args):
    import signal
    if os.name == "nt":
        result = subprocess.run("netstat -ano | findstr :8000", shell=True, capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if "LISTENING" in line:
                pid = line.strip().split()[-1]
                try:
                    subprocess.run(f"taskkill /PID {pid} /F", shell=True)
                    print(f"Stopped process {pid}")
                except Exception:
                    pass
    else:
        result = subprocess.run("lsof -ti:8000", shell=True, capture_output=True, text=True)
        for pid in result.stdout.strip().split("\n"):
            if pid:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"Stopped process {pid}")
                except Exception:
                    pass
    print("Aurine stopped.")


def cmd_cli(args):
    project_dir = get_project_dir()
    ensure_env(project_dir)
    venv_python = ensure_venv(project_dir)
    os.execv(str(venv_python), [str(venv_python), str(project_dir / "auracode.py")])


def main():
    parser = argparse.ArgumentParser(description="Aurine AI Assistant", prog="aurine")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Start the web server")
    run_p.add_argument("-p", "--port", type=int, default=8000)
    run_p.add_argument("--network", action="store_true", help="Allow network access")
    run_p.add_argument("--reload", action="store_true", help="Auto-reload on code changes")
    run_p.set_defaults(func=cmd_run)

    sub.add_parser("setup", help="Install dependencies and configure")

    sub.add_parser("stop", help="Stop the running server")

    cli_p = sub.add_parser("cli", help="Start the terminal AI agent (AuraCode)")
    cli_p.set_defaults(func=cmd_cli)

    sub.add_parser("status", help="Check what's installed")

    args = parser.parse_args()
    if not args.command:
        print(BANNER)
        print("Aurine AI Assistant\n")
        print("Commands:")
        print("  aurine run          Start web server")
        print("  aurine run -p 3000  Start on custom port")
        print("  aurine run --network  Allow mobile access")
        print("  aurine cli          Terminal AI agent")
        print("  aurine setup        Install dependencies")
        print("  aurine stop         Stop server")
        print("  aurine status       Check installation")
        return

    if args.command == "status":
        project_dir = get_project_dir()
        print(f"Project: {project_dir}")
        venv = project_dir / ".venv"
        print(f"Venv: {'OK' if venv.exists() else 'NOT FOUND - run: aurine setup'}")
        env = project_dir / ".env"
        print(f"Config: {'OK' if env.exists() else 'NOT FOUND - run: aurine setup'}")
        try:
            import fastapi
            print(f"FastAPI: {fastapi.__version__}")
        except ImportError:
            print("FastAPI: NOT INSTALLED - run: aurine setup")
        return

    args.func(args)


if __name__ == "__main__":
    main()
