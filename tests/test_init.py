"""Tests for integration setup helpers."""

from custom_components.dotnl_chargers.const import DOMAIN, PLATFORMS, VERSION


def test_domain_and_version():
    assert DOMAIN == "dotnl_chargers"
    assert VERSION.count('.') == 2
    assert len(PLATFORMS) == 3


def test_manifest_urls():
    import json
    from pathlib import Path

    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "custom_components"
            / "dotnl_chargers"
            / "manifest.json"
        ).read_text()
    )
    assert (
        manifest["documentation"]
        == "https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant"
    )
    assert (
        manifest["issue_tracker"]
        == "https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/issues"
    )
    assert manifest["config_flow"] is True
    assert manifest["version"] == VERSION
