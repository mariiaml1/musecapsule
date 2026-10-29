import json
import subprocess
from pathlib import Path

import logging
import re
from time import perf_counter

logger = logging.getLogger(__name__)

_TIMING_PATTERN = re.compile(
    r"MUSECAPSULE_TIMING "
    r"(electron_ready|sdk_import|get_session|sign_in|list_models|generation) "
    r"([0-9]+)"
)

def request_generation(
    text: str,
    devkit_dir: Path,
    *,
    instructions: str,
    model: str,
) -> str:
    """Generate text through the local ChatGPT bridge.

    Return the raw model response for task-specific validation.

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

    started = perf_counter()

    try:
        completed = subprocess.run(
            [str(executable), str(script), str(devkit_dir)],
            input=json.dumps(
                {
                    "text": text,
                    "instructions": instructions,
                    "model": model,
                },
                ensure_ascii=False,
            ),
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
    finally:
        logger.info(
            "llm_bridge total_ms=%.0f",
            (perf_counter() - started) * 1000,
        )

    # Forward only recognized timing records, never arbitrary bridge stderr.
    for line in completed.stderr.splitlines():
        match = _TIMING_PATTERN.fullmatch(line)
        if match:
            logger.info(
                "llm_bridge stage=%s elapsed_ms=%s",
                match.group(1),
                match.group(2),
            )

    if completed.returncode != 0:
        raise RuntimeError(
            "ChatGPT bridge failed. Run it directly to inspect its stderr."
        )

    if not completed.stdout.strip():
        raise RuntimeError("ChatGPT bridge returned an empty response.")

    return completed.stdout
