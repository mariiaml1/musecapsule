import subprocess
from unittest.mock import patch

import pytest

from musecapsule.llm import request_image_extraction


def test_request_image_extraction_reports_timeout(tmp_path):
    executable = tmp_path / "node_modules" / ".bin" / "electron"
    executable.parent.mkdir(parents=True)
    executable.touch()

    sdk_entry = tmp_path / "packages" / "local" / "dist" / "index.js"
    sdk_entry.parent.mkdir(parents=True)
    sdk_entry.touch()

    with patch(
        "musecapsule.llm.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd=["electron"],
            timeout=120,
        ),
    ), pytest.raises(RuntimeError, match="ChatGPT bridge timed out"):
        request_image_extraction(
            text="A golden note floats inside a capsule.",
            devkit_dir=tmp_path,
            instructions="Extract images.",
            model="test-model",
        )

def test_request_image_extraction_reports_process_failure(tmp_path):
    executable = tmp_path / "node_modules" / ".bin" / "electron"
    executable.parent.mkdir(parents=True)
    executable.touch()

    sdk_entry = tmp_path / "packages" / "local" / "dist" / "index.js"
    sdk_entry.parent.mkdir(parents=True)
    sdk_entry.touch()

    with patch(
        "musecapsule.llm.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["electron"],
            returncode=1,
            stdout="",
            stderr="Provider request failed.",
        ),
    ), pytest.raises(RuntimeError, match="ChatGPT bridge failed"):
        request_image_extraction(
            text="A golden note floats inside a capsule.",
            devkit_dir=tmp_path,
            instructions="Extract images.",
            model="test-model",
        )
