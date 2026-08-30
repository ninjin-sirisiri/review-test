from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "libwatch-build.yml"


def test_workflow_file_exists() -> None:
    assert WORKFLOW.is_file()


def test_workflow_has_six_hour_cron() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")
    assert "cron:" in body
    assert "0 */6 * * *" in body


def test_workflow_runs_libwatch() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")
    assert "python3 -m libwatch" in body


def test_workflow_uploads_site_artifact() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")
    assert "path: site/" in body or "path: site" in body


def test_workflow_has_no_pages_deploy() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")
    assert "peaceiris/actions-gh-pages" not in body
    assert "github-pages" not in body
