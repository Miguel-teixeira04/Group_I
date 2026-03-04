import subprocess
import sys
from pathlib import Path

def _is_running_in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__":    
    if _is_running_in_streamlit():
        from app.app import run

        run()
    else:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve())],
            check=False,
        )
