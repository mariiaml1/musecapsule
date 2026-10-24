import json
import subprocess
from pathlib import Path


def request_image_extraction(text: str, devkit_dir: Path) -> str:
    """Request image extraction through the local ChatGPT bridge.

    Return the raw model response for separate validation.

    Raises:
        ValueError: If the input text is blank.
        RuntimeError: If the bridge cannot complete the request.
    """
    if not text.strip():
        raise ValueError("Request text must not be blank.")

    devkit_dir = devkit_dir.expanduser().resolve()
    executable = devkit_dir / "node_modules" / ".bin" / "electron"

    # Resolve the bridge relative to this source checkout.
    project_dir = Path(__file__).resolve().parents[2]
    script = project_dir / "bridge" / "chatgpt.cjs"
    sdk_entry = devkit_dir / "packages" / "local" / "dist" / "index.js"

    if not all(path.is_file() for path in (executable, script, sdk_entry)):
        raise RuntimeError("ChatGPT bridge installation is incomplete.")

    try:
        completed = subprocess.run(
            [str(executable), str(script), str(devkit_dir)],
            input=json.dumps({"text": text}, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=devkit_dir,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("ChatGPT bridge timed out.") from error
    except OSError as error:
        raise RuntimeError("ChatGPT bridge could not be started.") from error

    if completed.returncode != 0:
        raise RuntimeError(
            "ChatGPT bridge failed. Run it directly to inspect its stderr."
        )

    if not completed.stdout.strip():
        raise RuntimeError("ChatGPT bridge returned an empty response.")

    return completed.stdout
