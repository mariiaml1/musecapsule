from unittest.mock import patch

from musecapsule.demo import cli


def test_cli_reports_invalid_selection(capsys):
    with patch(
        "musecapsule.demo.main",
        side_effect=ValueError("Selected idea does not exist."),
    ):
        exit_code = cli()

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: Selected idea does not exist.\n"


def test_cli_does_not_expose_generation_error_details(capsys):
    with patch(
        "musecapsule.demo.main",
        side_effect=RuntimeError("Private narrative or provider details"),
    ):
        exit_code = cli()

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Generation could not be completed" in captured.err
    assert "Private narrative" not in captured.err
    assert "Traceback" not in captured.err
