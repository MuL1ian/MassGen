# -*- coding: utf-8 -*-
"""Skills installation utility for MassGen.

This module provides cross-platform installation of skills including:
- openskills CLI (npm package)
- Anthropic skills collection
- Crawl4AI skill

Works on Windows, macOS, and Linux.
"""

import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

# Color constants for terminal output
RESET = "\033[0m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_RED = "\033[91m"


def _print_header(message: str) -> None:
    """Print a formatted header message."""
    print(f"\n{BRIGHT_CYAN}{'═' * 60}{RESET}")
    print(f"{BRIGHT_CYAN}{message:^60}{RESET}")
    print(f"{BRIGHT_CYAN}{'═' * 60}{RESET}\n")


def _print_step(step: str, total: int, message: str) -> None:
    """Print a step indicator."""
    print(f"{BRIGHT_CYAN}[{step}/{total}] {message}{RESET}")


def _print_success(message: str) -> None:
    """Print a success message."""
    print(f"{BRIGHT_GREEN}✓ {message}{RESET}")


def _print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{BRIGHT_YELLOW}⚠ {message}{RESET}")


def _print_error(message: str) -> None:
    """Print an error message."""
    print(f"{BRIGHT_RED}✗ {message}{RESET}")


def _print_info(message: str) -> None:
    """Print an info message."""
    print(f"{BRIGHT_CYAN}  {message}{RESET}")


def _check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(command) is not None


def _run_command(
    command: list[str],
    check: bool = True,
    capture_output: bool = False,
) -> Optional[subprocess.CompletedProcess]:
    """Run a shell command.

    Args:
        command: Command and arguments as a list
        check: Whether to raise on non-zero exit
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess if successful, None if failed and check=False
    """
    try:
        return subprocess.run(
            command,
            check=check,
            capture_output=capture_output,
            text=True,
        )
    except subprocess.CalledProcessError:
        if check:
            raise
        return None


def _get_npm_global_package_version(package: str) -> Optional[str]:
    """Get the version of a globally installed npm package.

    Args:
        package: Package name (e.g., 'openskills')

    Returns:
        Version string if installed, None otherwise
    """
    try:
        result = subprocess.run(
            ["npm", "list", "-g", package, "--depth=0"],
            capture_output=True,
            text=True,
            check=False,
        )
        # npm list returns non-zero if package not found, but still outputs info
        if package in result.stdout:
            # Extract version from output like: openskills@1.2.3
            for line in result.stdout.split("\n"):
                if package in line and "@" in line:
                    return line.split("@")[-1].strip()
        return None
    except Exception:
        return None


def install_openskills_cli() -> bool:
    """Install openskills CLI via npm.

    Returns:
        True if successful, False otherwise
    """
    _print_step("1", "3", "Installing openskills CLI...")

    # Check if npm is available
    if not _check_command_exists("npm"):
        _print_error("npm is not installed")
        _print_info("Please install Node.js and npm first:")
        _print_info("  macOS:   brew install node")
        _print_info("  Linux:   sudo apt-get install nodejs npm")
        _print_info("  Windows: Download from https://nodejs.org/")
        return False

    # Check if openskills already installed
    version = _get_npm_global_package_version("openskills")
    if version:
        _print_warning(f"openskills already installed: {version}")
        return True

    # Install openskills
    _print_info("Installing openskills globally...")
    result = _run_command(["npm", "install", "-g", "openskills"], check=False)

    if result and result.returncode == 0:
        _print_success("openskills installed successfully")
        return True
    else:
        _print_error("Failed to install openskills")
        return False


def install_anthropic_skills() -> bool:
    """Install Anthropic skills collection via openskills.

    Returns:
        True if successful, False otherwise
    """
    _print_step("2", "3", "Installing Anthropic skills collection...")

    # Check if openskills is available
    if not _check_command_exists("openskills"):
        _print_error("openskills not found")
        _print_info("Run with --setup-skills again to install openskills first")
        return False

    # Check if skills directory exists
    skills_dir = Path.home() / ".agent" / "skills"
    if skills_dir.exists() and any(skills_dir.iterdir()):
        skill_count = len(list(skills_dir.iterdir()))
        _print_warning(f"Skills directory exists with {skill_count} skills")
        _print_info("Installing/updating Anthropic skills...")
    else:
        _print_info("Installing Anthropic skills (first time)...")

    # Install Anthropic skills
    result = _run_command(
        ["openskills", "install", "anthropics/skills", "--universal", "-y"],
        check=False,
    )

    if result and result.returncode == 0:
        # Count installed skills
        if skills_dir.exists():
            skill_count = len(list(skills_dir.iterdir()))
            _print_success(f"Anthropic skills installed ({skill_count} total skills)")
        else:
            _print_success("Anthropic skills installed")
        return True
    else:
        _print_error("Failed to install Anthropic skills")
        return False


def install_crawl4ai_skill() -> bool:
    """Install Crawl4AI skill from docs.crawl4ai.com.

    Returns:
        True if successful, False otherwise
    """
    _print_step("3", "3", "Installing Crawl4AI skill...")

    skills_dir = Path.home() / ".agent" / "skills"
    crawl4ai_dir = skills_dir / "crawl4ai"

    # Check if already installed
    if crawl4ai_dir.exists():
        _print_warning("Crawl4AI skill directory already exists")
        _print_info(f"Skipping download (delete {crawl4ai_dir} to reinstall)")
        return True

    # Download and install
    _print_info("Downloading Crawl4AI skill...")

    url = "https://docs.crawl4ai.com/assets/crawl4ai-skill.zip"

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / "crawl4ai-skill.zip"

            # Download
            try:
                urllib.request.urlretrieve(url, zip_path)
            except Exception as e:
                _print_error(f"Failed to download Crawl4AI skill: {e}")
                _print_info(f"URL: {url}")
                _print_info(f"You can download and extract manually to: {crawl4ai_dir}")
                return False

            # Extract
            _print_info(f"Extracting to {crawl4ai_dir}...")

            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    # Extract to temp directory first
                    zip_ref.extractall(temp_path)

                # Move extracted content to final location
                skills_dir.mkdir(parents=True, exist_ok=True)

                # Handle different zip structures
                if (temp_path / "crawl4ai").exists():
                    shutil.move(str(temp_path / "crawl4ai"), str(crawl4ai_dir))
                elif (temp_path / "crawl4ai-skill").exists():
                    shutil.move(str(temp_path / "crawl4ai-skill"), str(crawl4ai_dir))
                else:
                    # If zip extracts to multiple files, create dir and move all
                    crawl4ai_dir.mkdir(parents=True, exist_ok=True)
                    for item in temp_path.iterdir():
                        if item.name != "crawl4ai-skill.zip":
                            dest = crawl4ai_dir / item.name
                            if item.is_dir():
                                shutil.copytree(item, dest)
                            else:
                                shutil.copy2(item, dest)

                _print_success("Crawl4AI skill installed successfully")
                return True

            except Exception as e:
                _print_error(f"Failed to extract Crawl4AI skill: {e}")
                return False

    except Exception as e:
        _print_error(f"Unexpected error: {e}")
        return False


def list_available_skills() -> dict:
    """List all available skills grouped by location.

    Scans for skills in three locations (matching WebUI /api/skills):
    - Built-in: massgen/skills/
    - User: ~/.agent/skills/ (home directory - where openskills installs)
    - Project: .agent/skills/ (current working directory)

    Returns:
        Dict with 'builtin', 'user', and 'project' keys, each containing list of skill dicts.
        Each skill dict has 'name', 'description', and 'location' keys.
    """
    from massgen.filesystem_manager.skills_manager import scan_skills

    all_skills = []
    seen_names = set()

    # Scan user skills (~/.agent/skills/)
    user_dir = Path.home() / ".agent" / "skills"
    user_skills = scan_skills(user_dir)
    for skill in user_skills:
        if skill["location"] == "project":  # scan_skills marks these as "project"
            skill["location"] = "user"  # Re-label as "user" for home directory
        if skill["name"] not in seen_names:
            all_skills.append(skill)
            seen_names.add(skill["name"])

    # Scan project skills (.agent/skills/ in cwd)
    project_dir = Path.cwd() / ".agent" / "skills"
    if project_dir.exists():
        project_skills = scan_skills(project_dir)
        for skill in project_skills:
            if skill["name"] not in seen_names:
                all_skills.append(skill)
                seen_names.add(skill["name"])

    # Builtin skills are already included from scan_skills

    # Group by location
    return {
        "builtin": [s for s in all_skills if s["location"] == "builtin"],
        "user": [s for s in all_skills if s["location"] == "user"],
        "project": [s for s in all_skills if s["location"] == "project"],
    }


def check_skill_packages_installed() -> dict:
    """Check installation status of skill packages.

    Returns:
        Dict with package info including installation status.
    """
    skills = list_available_skills()
    # Installed skills = user + project (excluding builtin)
    installed_skills = skills["user"] + skills["project"]

    # Check for Anthropic skills (installed via openskills, not crawl4ai)
    anthropic_skills = [s for s in installed_skills if not s["name"].lower().startswith("crawl4ai")]
    has_anthropic = len(anthropic_skills) > 0

    # Check for Crawl4AI
    has_crawl4ai = any(s["name"].lower().startswith("crawl4ai") for s in installed_skills)

    return {
        "anthropic": {
            "name": "Anthropic Skills Collection",
            "description": "Official Anthropic skills including code analysis, research, and more",
            "installed": has_anthropic,
            "skill_count": len(anthropic_skills) if has_anthropic else 0,
        },
        "crawl4ai": {
            "name": "Crawl4AI",
            "description": "Web crawling and scraping skill for extracting content from websites",
            "installed": has_crawl4ai,
        },
    }


def display_skills_summary() -> None:
    """Display skills summary in terminal - matches WebUI structure."""
    skills = list_available_skills()
    builtin = skills["builtin"]
    user = skills["user"]
    project = skills["project"]
    packages = check_skill_packages_installed()

    installed_count = len(user) + len(project)
    total = len(builtin) + installed_count

    print(f"\n{BRIGHT_CYAN}{'═' * 60}{RESET}")
    print(f"{BRIGHT_CYAN}{'Skills':^60}{RESET}")
    print(f"{BRIGHT_CYAN}{'═' * 60}{RESET}\n")

    # Summary
    print(f"{BRIGHT_GREEN}{total} Skill(s) Available{RESET}")
    print(f"  {len(builtin)} built-in, {installed_count} installed\n")

    # Skill Packages section (matches WebUI)
    print(f"{BRIGHT_CYAN}Skill Packages:{RESET}")
    print(f"{BRIGHT_YELLOW}Install skill packages to add new capabilities.{RESET}\n")

    for pkg_id, pkg in packages.items():
        if pkg["installed"]:
            count_info = f" ({pkg['skill_count']} skills)" if pkg.get("skill_count") else ""
            print(f"  {BRIGHT_GREEN}✓{RESET} {pkg['name']} [installed{count_info}]")
        else:
            print(f"  {BRIGHT_RED}✗{RESET} {pkg['name']} [not installed]")
        print(f"      {pkg['description']}")

    print()


def install_skills() -> None:
    """Main entry point for skills installation.

    Installs:
    1. openskills CLI (npm package)
    2. Anthropic skills collection
    3. Crawl4AI skill

    This function is called by `massgen --setup-skills` command.
    """
    _print_header("MassGen Skills Installation")

    print(f"{BRIGHT_CYAN}Platform: {platform.system()}{RESET}\n")

    # Track success
    results = []

    # 1. Install openskills CLI
    results.append(("openskills CLI", install_openskills_cli()))
    print()

    # 2. Install Anthropic skills (only if openskills succeeded)
    if results[0][1]:
        results.append(("Anthropic skills", install_anthropic_skills()))
    else:
        _print_warning("Skipping Anthropic skills (openskills required)")
        results.append(("Anthropic skills", False))
    print()

    # 3. Install Crawl4AI skill
    results.append(("Crawl4AI skill", install_crawl4ai_skill()))
    print()

    # Summary
    _print_header("Installation Summary")

    all_success = all(success for _, success in results)

    for component, success in results:
        if success:
            _print_success(f"{component}")
        else:
            _print_error(f"{component}")

    print()

    if all_success:
        _print_success("All skills installed successfully!")
        print()

        # Show skills directory
        skills_dir = Path.home() / ".agent" / "skills"
        if skills_dir.exists():
            skill_count = len(list(skills_dir.iterdir()))
            print(f"{BRIGHT_CYAN}Total skills available: {skill_count}{RESET}")
            print(f"{BRIGHT_CYAN}Skills directory: {skills_dir}{RESET}")
            print()

        print(f"{BRIGHT_CYAN}Next steps:{RESET}")
        print("  • Skills are now available in Claude Code and Gemini CLI")
        print("  • Run 'massgen' to start using MassGen with skills")
        print("  • See documentation: https://docs.massgen.ai")
        print()
    else:
        _print_warning("Some installations failed - see errors above")
        print()
        print(f"{BRIGHT_CYAN}Troubleshooting:{RESET}")
        print("  • Ensure Node.js and npm are installed")
        print("  • Check your internet connection")
        print("  • Run 'massgen --setup-skills' again to retry")
        print()
        sys.exit(1)


if __name__ == "__main__":
    # Allow running directly for testing
    install_skills()
