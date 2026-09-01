from io import StringIO

from libwatch.__main__ import main


def test_no_args_runs_build(monkeypatch) -> None:
    called = {"n": 0}

    def fake_build() -> int:
        called["n"] += 1
        return 0

    monkeypatch.setattr("libwatch.__main__.build_main", fake_build)
    assert main([]) == 0
    assert called["n"] == 1


def test_unknown_command_is_error(capsys) -> None:
    assert main(["build"]) == 1
    captured = capsys.readouterr()
    assert "unknown command: build" in captured.err


def test_serve_rejects_bad_port(monkeypatch) -> None:
    from libwatch.serve import serve_main

    stderr = StringIO()
    assert serve_main(["--port", "0"], stderr=stderr) == 1
    assert serve_main(["--port", "foo"], stderr=stderr) == 1
    assert serve_main(["--host", "127.0.0.1"], stderr=stderr) == 1
    assert serve_main(["--port", "8000", "extra"], stderr=stderr) == 1
