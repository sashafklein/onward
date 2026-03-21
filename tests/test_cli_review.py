import re
from pathlib import Path

from onward import cli


def _set_executor_command(root: Path, command: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace("  command: builtin", f'  command: "{command}"')
    config_path.write_text(raw, encoding="utf-8")


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0
    _set_executor_command(root, "true")


def _create_plan(root: Path, title: str = "Test Plan") -> None:
    assert cli.main(["new", "--root", str(root), "plan", title]) == 0


def _set_executor_enabled(root: Path, value: str) -> None:
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    pos = text.find("executor:")
    assert pos >= 0
    head, tail = text[:pos], text[pos:]
    tail_new = re.sub(r"(?m)^(\s+enabled:\s*)\S+", rf"\g<1>{value}", tail, count=1)
    config_path.write_text(head + tail_new, encoding="utf-8")


def _replace_review_section(root: Path, new_block: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    start = raw.index("\nreview:")
    # next top-level key after review block
    rest = raw[start + 1 :]
    rel = rest.index("\nwork:")
    old_review = raw[start + 1 : start + 1 + rel]
    config_path.write_text(raw.replace(old_review, new_block), encoding="utf-8")


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
    assert "Running review: reviewer-1" in out
    assert "Running review: reviewer-2" in out
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
    assert "Running review: reviewer-1" in out
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


def test_review_plan_fails_when_executor_disabled(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan(tmp_path)
    _set_executor_enabled(tmp_path, "false")
    capsys.readouterr()

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out

    assert code == 1
    assert "executor.enabled is false" in out


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


def test_review_plan_reviewers_matrix_config(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan(tmp_path)
    _replace_review_section(
        tmp_path,
        """
review:
  double_review: true
  reviewers:
    - label: primary-claude
      model: sonnet-4-6
    - label: secondary-opus
      model: opus-latest

""",
    )
    capsys.readouterr()
    monkeypatch.setenv("TRAIN_REVIEW_RESPONSE", SAMPLE_REVIEW)

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Running review: primary-claude" in out
    assert "Running review: secondary-opus" in out
    assert "slot=primary-claude" in out
    assert "slot=secondary-opus" in out
    review_files = list((tmp_path / ".onward/reviews").glob("PLAN-001-*.md"))
    assert len(review_files) == 2


def test_review_plan_reviewer_filter(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan(tmp_path)
    _replace_review_section(
        tmp_path,
        """
review:
  reviewers:
    - label: only-me
      model: sonnet-4-6
    - label: skipped
      model: opus-latest

""",
    )
    capsys.readouterr()
    monkeypatch.setenv("TRAIN_REVIEW_RESPONSE", SAMPLE_REVIEW)

    code = cli.main(
        ["review-plan", "--root", str(tmp_path), "--reviewer", "only-me", "PLAN-001"]
    )
    out = capsys.readouterr().out

    assert code == 0
    assert "only-me" in out
    assert "skipped" not in out
    review_files = list((tmp_path / ".onward/reviews").glob("PLAN-001-*.md"))
    assert len(review_files) == 1


def test_review_plan_fallback_after_preflight(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.delenv("TRAIN_REVIEW_RESPONSE", raising=False)
    _init_workspace(tmp_path)
    _create_plan(tmp_path)
    _replace_review_section(
        tmp_path,
        """
review:
  reviewers:
    - label: slot-a
      model: sonnet-4-6
      command: no-such-onward-review-fallback-preflight
      args: []
      fallback:
        - model: haiku-latest
          command: true
          args: []

""",
    )
    capsys.readouterr()

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "fallback_reason=preflight_failed" in out
    assert "try=1/2" in out
    assert "try=2/2" in out


def test_review_plan_fallback_after_executor_fail(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.delenv("TRAIN_REVIEW_RESPONSE", raising=False)
    _init_workspace(tmp_path)
    _create_plan(tmp_path)
    _set_executor_command(tmp_path, "true")
    _replace_review_section(
        tmp_path,
        """
review:
  reviewers:
    - label: slot-b
      model: sonnet-4-6
      fallback:
        - haiku-latest

""",
    )
    capsys.readouterr()

    calls = {"n": 0}

    class Bad:
        returncode = 1
        stdout = ""
        stderr = "boom"

    class Good:
        returncode = 0
        stdout = SAMPLE_REVIEW
        stderr = ""

    def fake_run(*_a, **_kw):
        calls["n"] += 1
        return Bad() if calls["n"] == 1 else Good()

    monkeypatch.setattr("onward.execution.subprocess.run", fake_run)

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "fallback_reason=executor_failed" in out
    assert calls["n"] == 2
    review_files = list((tmp_path / ".onward/reviews").glob("PLAN-001-*.md"))
    assert len(review_files) == 1
    assert "Revision Needed" in review_files[0].read_text(encoding="utf-8")
