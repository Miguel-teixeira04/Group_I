import subprocess
import sys
from pathlib import Path


def _check_and_install_requirements() -> None:
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    

    missing_packages = []
    
    for package in requirements_file.read_text().splitlines():
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}")
        
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                check=True,
                capture_output=True,
                text=True,
            )
            print("Requirements Installed")
        except subprocess.CalledProcessError as e:
            print(f"Could not install requirements: {e.stderr}")
            sys.exit(1)


def _is_running_in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__":
    _check_and_install_requirements()
    
    if _is_running_in_streamlit():
        from app.app import run

        run()
    else:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve())],
            check=False,
        )
