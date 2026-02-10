# -*- coding: utf-8 -*-
"""Tests for quickstart skill setup helpers."""

import yaml

import massgen.cli as cli
import massgen.utils.skills_installer as skills_installer


def _package_status(
    *,
    anthropic_installed: bool,
    openai_installed: bool,
    vercel_installed: bool,
    agent_browser_installed: bool,
    crawl4ai_installed: bool,
) -> dict:
    """Build package status payload matching check_skill_packages_installed()."""
    return {
        "anthropic": {
            "name": "Anthropic Skills Collection",
            "description": "Anthropic skills",
            "installed": anthropic_installed,
            "skill_count": 1 if anthropic_installed else 0,
        },
        "openai": {
            "name": "OpenAI Skills Collection",
            "description": "OpenAI skills",
            "installed": openai_installed,
        },
        "vercel": {
            "name": "Vercel Agent Skills",
            "description": "Vercel skills",
            "installed": vercel_installed,
        },
        "agent_browser": {
            "name": "Vercel Agent Browser Skill",
            "description": "Agent browser skill",
            "installed": agent_browser_installed,
        },
        "crawl4ai": {
            "name": "Crawl4AI",
            "description": "Crawl4AI skill",
            "installed": crawl4ai_installed,
        },
    }


def test_install_quickstart_skills_skips_when_packages_already_installed(monkeypatch):
    """Quickstart installer should no-op when required packages are already present."""
    calls = []

    monkeypatch.setattr(
        skills_installer,
        "check_skill_packages_installed",
        lambda: _package_status(
            anthropic_installed=True,
            openai_installed=True,
            vercel_installed=True,
            agent_browser_installed=True,
            crawl4ai_installed=True,
        ),
    )
    monkeypatch.setattr(
        skills_installer,
        "_check_command_exists",
        lambda _: True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_openskills_cli",
        lambda: calls.append("openskills") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_anthropic_skills",
        lambda: calls.append("anthropic") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_openai_skills",
        lambda: calls.append("openai") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_vercel_skills",
        lambda: calls.append("vercel") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_agent_browser_skill",
        lambda: calls.append("agent_browser") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_crawl4ai_skill",
        lambda: calls.append("crawl4ai") or True,
    )

    assert skills_installer.install_quickstart_skills() is True
    assert calls == []


def test_install_quickstart_skills_installs_only_missing_packages(monkeypatch):
    """Quickstart installer should install all missing quickstart skill packages."""
    calls = []

    monkeypatch.setattr(
        skills_installer,
        "check_skill_packages_installed",
        lambda: _package_status(
            anthropic_installed=False,
            openai_installed=False,
            vercel_installed=False,
            agent_browser_installed=False,
            crawl4ai_installed=False,
        ),
    )
    monkeypatch.setattr(
        skills_installer,
        "_check_command_exists",
        lambda _: False,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_openskills_cli",
        lambda: calls.append("openskills") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_anthropic_skills",
        lambda: calls.append("anthropic") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_openai_skills",
        lambda: calls.append("openai") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_vercel_skills",
        lambda: calls.append("vercel") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_agent_browser_skill",
        lambda: calls.append("agent_browser") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_crawl4ai_skill",
        lambda: calls.append("crawl4ai") or True,
    )

    assert skills_installer.install_quickstart_skills() is True
    assert calls == ["openskills", "anthropic", "openai", "vercel", "agent_browser", "crawl4ai"]


def test_install_quickstart_skills_handles_partial_failures(monkeypatch):
    """Quickstart installer should continue and report failure when some installs fail."""
    calls = []

    monkeypatch.setattr(
        skills_installer,
        "check_skill_packages_installed",
        lambda: _package_status(
            anthropic_installed=False,
            openai_installed=False,
            vercel_installed=False,
            agent_browser_installed=False,
            crawl4ai_installed=False,
        ),
    )
    monkeypatch.setattr(
        skills_installer,
        "_check_command_exists",
        lambda _: False,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_openskills_cli",
        lambda: calls.append("openskills") or False,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_anthropic_skills",
        lambda: calls.append("anthropic") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_openai_skills",
        lambda: calls.append("openai") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_vercel_skills",
        lambda: calls.append("vercel") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_agent_browser_skill",
        lambda: calls.append("agent_browser") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_crawl4ai_skill",
        lambda: calls.append("crawl4ai") or True,
    )

    assert skills_installer.install_quickstart_skills() is False
    assert calls == ["openskills", "crawl4ai"]


def test_install_quickstart_skills_installs_openskills_when_missing(monkeypatch):
    """Quickstart installer should install openskills even if skill folders already exist."""
    calls = []

    monkeypatch.setattr(
        skills_installer,
        "check_skill_packages_installed",
        lambda: _package_status(
            anthropic_installed=True,
            openai_installed=True,
            vercel_installed=True,
            agent_browser_installed=True,
            crawl4ai_installed=True,
        ),
    )
    monkeypatch.setattr(
        skills_installer,
        "_check_command_exists",
        lambda _: False,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_openskills_cli",
        lambda: calls.append("openskills") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_anthropic_skills",
        lambda: calls.append("anthropic") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_openai_skills",
        lambda: calls.append("openai") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_vercel_skills",
        lambda: calls.append("vercel") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_agent_browser_skill",
        lambda: calls.append("agent_browser") or True,
    )
    monkeypatch.setattr(
        skills_installer,
        "install_crawl4ai_skill",
        lambda: calls.append("crawl4ai") or True,
    )

    assert skills_installer.install_quickstart_skills() is True
    assert calls == ["openskills"]


def test_quickstart_config_uses_skills_detects_enabled_flag(tmp_path):
    """CLI helper should detect use_skills=true in generated config."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"orchestrator": {"coordination": {"use_skills": True}}}),
        encoding="utf-8",
    )

    assert cli._quickstart_config_uses_skills(str(config_path)) is True


def test_quickstart_config_uses_skills_returns_false_when_disabled(tmp_path):
    """CLI helper should return False when skills are disabled."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"orchestrator": {"coordination": {"use_skills": False}}}),
        encoding="utf-8",
    )

    assert cli._quickstart_config_uses_skills(str(config_path)) is False


def test_ensure_quickstart_skills_ready_runs_installer_when_needed(monkeypatch):
    """CLI should run quickstart installer when config enables skills."""
    calls = []

    monkeypatch.setattr(cli, "_quickstart_config_uses_skills", lambda _: True)
    monkeypatch.setattr(
        skills_installer,
        "install_quickstart_skills",
        lambda: calls.append("install") or True,
    )

    assert cli._ensure_quickstart_skills_ready("config.yaml") is True
    assert calls == ["install"]


def test_ensure_quickstart_skills_ready_skips_installer_when_not_needed(monkeypatch):
    """CLI should skip quickstart installer when config does not enable skills."""
    calls = []

    monkeypatch.setattr(cli, "_quickstart_config_uses_skills", lambda _: False)
    monkeypatch.setattr(
        skills_installer,
        "install_quickstart_skills",
        lambda: calls.append("install") or True,
    )

    assert cli._ensure_quickstart_skills_ready("config.yaml") is True
    assert calls == []


def test_ensure_quickstart_skills_ready_skips_when_user_declines(monkeypatch):
    """CLI should skip quickstart installer when user opts out in wizard."""
    calls = []

    monkeypatch.setattr(cli, "_quickstart_config_uses_skills", lambda _: True)
    monkeypatch.setattr(
        skills_installer,
        "install_quickstart_skills",
        lambda: calls.append("install") or True,
    )

    assert cli._ensure_quickstart_skills_ready("config.yaml", install_requested=False) is True
    assert calls == []
