"""Tests for config validation rules related to root/roots."""

from onward.config import validate_config_contract_issues


def test_root_and_roots_mutually_exclusive():
    """Both root and roots set should be an error."""
    config = {
        "root": "nb",
        "roots": {"a": "./a", "b": "./b"},
    }
    issues = validate_config_contract_issues(config)

    assert any("mutually exclusive" in issue for issue in issues)
    assert any("root" in issue and "roots" in issue for issue in issues)


def test_root_only_valid():
    """Just root set should be valid."""
    config = {"root": "nb"}
    issues = validate_config_contract_issues(config)

    # Should not have mutual exclusivity error
    assert not any("mutually exclusive" in issue for issue in issues)


def test_roots_only_valid():
    """Just roots set should be valid."""
    config = {"roots": {"a": "./a", "b": "./b"}}
    issues = validate_config_contract_issues(config)

    # Should not have mutual exclusivity error
    assert not any("mutually exclusive" in issue for issue in issues)


def test_neither_root_nor_roots_valid():
    """Neither root nor roots set should be valid (uses default)."""
    config = {"version": "1"}
    issues = validate_config_contract_issues(config)

    # Should not have any root/roots related errors
    assert not any("root" in issue.lower() for issue in issues)


def test_default_project_must_match_roots_key():
    """default_project must match a key in roots."""
    config = {
        "roots": {"a": "./a", "b": "./b"},
        "default_project": "nonexistent",
    }
    issues = validate_config_contract_issues(config)

    assert any("default_project" in issue and "nonexistent" in issue for issue in issues)


def test_default_project_valid_when_matches():
    """default_project matching a roots key should be valid."""
    config = {
        "roots": {"a": "./a", "b": "./b"},
        "default_project": "a",
    }
    issues = validate_config_contract_issues(config)

    # Should not have default_project error
    assert not any("default_project" in issue and "does not match" in issue for issue in issues)


def test_default_project_without_roots_warning():
    """default_project without roots should produce a warning."""
    config = {
        "default_project": "whatever",
    }
    issues = validate_config_contract_issues(config)

    # Should warn that default_project is only used with roots
    assert any("default_project" in issue and "roots is not configured" in issue for issue in issues)


def test_path_key_error_message_updated():
    """The old 'path' key should show updated error message."""
    config = {"path": "/some/path"}
    issues = validate_config_contract_issues(config)

    assert any("path" in issue for issue in issues)
    assert any("root" in issue or "roots" in issue for issue in issues)


def test_root_null_not_treated_as_set():
    """root: null should not be treated as 'set' for mutual exclusivity."""
    config = {
        "root": None,
        "roots": {"a": "./a"},
    }
    issues = validate_config_contract_issues(config)

    # Should not have mutual exclusivity error since root is null
    assert not any("mutually exclusive" in issue for issue in issues)


def test_roots_null_not_treated_as_set():
    """roots: null should not be treated as 'set' for mutual exclusivity."""
    config = {
        "root": "nb",
        "roots": None,
    }
    issues = validate_config_contract_issues(config)

    # Should not have mutual exclusivity error since roots is null
    assert not any("mutually exclusive" in issue for issue in issues)


def test_default_project_empty_string_not_validated():
    """default_project as empty string should not cause validation error."""
    config = {
        "roots": {"a": "./a", "b": "./b"},
        "default_project": "",
    }
    issues = validate_config_contract_issues(config)

    # Empty string is stripped and treated as None, so should not error
    assert not any("default_project" in issue and "does not match" in issue for issue in issues)


def test_default_project_whitespace_not_validated():
    """default_project as whitespace should not cause validation error."""
    config = {
        "roots": {"a": "./a", "b": "./b"},
        "default_project": "   ",
    }
    issues = validate_config_contract_issues(config)

    # Whitespace is stripped and treated as empty/None, so should not error
    assert not any("default_project" in issue and "does not match" in issue for issue in issues)


def test_root_empty_string_error():
    """root as empty string should be an error."""
    config = {"root": ""}
    issues = validate_config_contract_issues(config)

    assert any("root" in issue and "non-empty string" in issue for issue in issues)


def test_root_whitespace_string_error():
    """root as whitespace should be an error."""
    config = {"root": "   "}
    issues = validate_config_contract_issues(config)

    assert any("root" in issue and "non-empty string" in issue for issue in issues)


def test_root_non_string_error():
    """root as non-string should be an error."""
    config = {"root": 123}
    issues = validate_config_contract_issues(config)

    assert any("root" in issue and "non-empty string" in issue for issue in issues)


def test_roots_empty_dict_error():
    """roots as empty dict should be an error."""
    config = {"roots": {}}
    issues = validate_config_contract_issues(config)

    assert any("roots" in issue and "non-empty mapping" in issue for issue in issues)


def test_roots_non_dict_error():
    """roots as non-dict should be an error."""
    config = {"roots": "not a dict"}
    issues = validate_config_contract_issues(config)

    assert any("roots" in issue and "non-empty mapping" in issue for issue in issues)


def test_roots_empty_key_error():
    """roots with empty string key should be an error."""
    config = {"roots": {"": "./path"}}
    issues = validate_config_contract_issues(config)

    assert any("roots keys" in issue and "non-empty" in issue for issue in issues)


def test_roots_empty_value_error():
    """roots with empty string value should be an error."""
    config = {"roots": {"project": ""}}
    issues = validate_config_contract_issues(config)

    assert any("roots['project']" in issue and "non-empty string path" in issue for issue in issues)


def test_roots_whitespace_value_error():
    """roots with whitespace value should be an error."""
    config = {"roots": {"project": "   "}}
    issues = validate_config_contract_issues(config)

    assert any("roots['project']" in issue and "non-empty string path" in issue for issue in issues)


def test_roots_non_string_value_error():
    """roots with non-string value should be an error."""
    config = {"roots": {"project": 123}}
    issues = validate_config_contract_issues(config)

    assert any("roots['project']" in issue and "non-empty string path" in issue for issue in issues)
