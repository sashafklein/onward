import re
from pathlib import Path

from onward import cli


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def _create_plan(root: Path, title: str = "Test Plan") -> None:
    assert cli.main(["new", "--root", str(root), "plan", title]) == 0


def _set_ralph_enabled(root: Path, value: str) -> None:
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    pos = text.find("ralph:")
    assert pos >= 0
    head, tail = text[:pos], text[pos:]
    tail_new = re.sub(r"(?m)^(\s+enabled:\s*)\S+", rf"\g<1>{value}", tail, count=1)
    config_path.write_text(head + tail_new, encoding="utf-8")


SAMPLE_REVIEW = """## Review: Test Plan

### Overall Assessment: Revision Needed

### Findings

| # | Severity | Category | Finding | Recommendation |
|---|----------|----------|---------|----------------|
| 1 | Important | Security | No auth strategy described | Add auth section |

### Notes

Solid overall direction but needs security consideration.
"""


def test_review_plan_double_review_creates_two_files(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan(tmp_path)
    capsys.readouterr()

    monkeypatch.setenv("TRAIN_REVIEW_RESPONSE", SAMPLE_REVIEW)

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "reviewer-1" in out
    assert "reviewer-2" in out
    assert "2 review(s) written" in out
    assert "judiciously incorporate" in out

    review_files = list((tmp_path / ".onward/reviews").glob("PLAN-001-*.md"))
    assert len(review_files) == 2
    labels = sorted(f.stem.rsplit("-", 1)[-1] for f in review_files)
    assert labels == ["1", "2"]

    for rf in review_files:
        content = rf.read_text(encoding="utf-8")
        assert "Revision Needed" in content


def test_review_plan_single_review_when_double_disabled(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan(tmp_path)

    config_path = tmp_path / ".onward.config.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    config_text = config_text.replace("double_review: true", "double_review: false")
    config_path.write_text(config_text, encoding="utf-8")
    capsys.readouterr()

    monkeypatch.setenv("TRAIN_REVIEW_RESPONSE", SAMPLE_REVIEW)

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "reviewer-1" in out
    assert "reviewer-2" not in out
    assert "1 review(s) written" in out

    review_files = list((tmp_path / ".onward/reviews").glob("PLAN-001-*.md"))
    assert len(review_files) == 1


def test_review_plan_rejects_non_plan(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Some Chunk"]) == 0
    capsys.readouterr()

    code = cli.main(["review-plan", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out

    assert code == 1
    assert "not a plan" in out


def test_review_plan_fails_when_ralph_disabled(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan(tmp_path)
    _set_ralph_enabled(tmp_path, "false")
    capsys.readouterr()

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out

    assert code == 1
    assert "ralph.enabled is false" in out


def test_review_plan_missing_plan_errors(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    capsys.readouterr()

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-999"])
    out = capsys.readouterr().out

    assert code == 1
    assert "not found" in out


def test_review_plan_gitignore_includes_reviews(tmp_path: Path):
    _init_workspace(tmp_path)
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".onward/reviews/" in gitignore


def test_review_plan_writes_review_content(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan(tmp_path, "Auth System")
    capsys.readouterr()

    custom_review = "## Review: Auth System\n\n### Overall Assessment: Approved\n\n### Notes\n\nLooks good.\n"
    monkeypatch.setenv("TRAIN_REVIEW_RESPONSE", custom_review)

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    assert code == 0

    review_files = list((tmp_path / ".onward/reviews").glob("PLAN-001-*.md"))
    assert len(review_files) >= 1
    content = review_files[0].read_text(encoding="utf-8")
    assert "Auth System" in content
    assert "Approved" in content
