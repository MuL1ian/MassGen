# -*- coding: utf-8 -*-
"""
Quickstart Wizard for MassGen TUI.

Provides an interactive wizard for creating a MassGen configuration.
This replaces the questionary-based CLI quickstart with a Textual TUI experience.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import (
    Input,
    Label,
    OptionList,
    Select,
    TabbedContent,
    TabPane,
    TextArea,
)
from textual.widgets.option_list import Option

from .wizard_base import StepComponent, WizardModal, WizardState, WizardStep
from .wizard_steps import LaunchOptionsStep, WelcomeStep


def _quickstart_log(msg: str) -> None:
    """Log to TUI debug file."""
    try:
        import logging

        log = logging.getLogger("massgen.tui.debug")
        if not log.handlers:
            handler = logging.FileHandler("/tmp/massgen_tui_debug.log", mode="a")
            handler.setFormatter(logging.Formatter("%(asctime)s [QUICKSTART] %(message)s", datefmt="%H:%M:%S"))
            log.addHandler(handler)
            log.setLevel(logging.DEBUG)
            log.propagate = False
        log.debug(msg)
    except Exception:
        pass


class QuickstartWelcomeStep(WelcomeStep):
    """Welcome step customized for quickstart wizard."""

    def __init__(self, wizard_state: WizardState, **kwargs):
        super().__init__(
            wizard_state,
            title="MassGen Quickstart",
            subtitle="Create a configuration in minutes",
            features=[
                "Select number of agents",
                "Choose AI providers and models",
                "Configure tools and execution mode",
                "Generate ready-to-use YAML config",
            ],
            **kwargs,
        )


class AgentCountStep(StepComponent):
    """Step for selecting number of agents using native OptionList."""

    COUNTS = [
        ("1", "1 Agent", "Single agent mode"),
        ("2", "2 Agents", "Two agents collaborating"),
        ("3", "3 Agents (Recommended)", "Three agents for robust consensus"),
        ("4", "4 Agents", "Four agents for complex tasks"),
        ("5", "5 Agents", "Maximum agents for diverse perspectives"),
    ]

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._selected_count: str = "3"
        self._option_list: Optional[OptionList] = None

    def compose(self) -> ComposeResult:
        yield Label("How many agents should work on your tasks?", classes="text-input-label")

        # Build native options
        textual_options = []
        for value, label, description in self.COUNTS:
            option_text = f"[bold]{label}[/bold]\n[dim]{description}[/dim]"
            textual_options.append(Option(option_text, id=value))

        self._option_list = OptionList(
            *textual_options,
            id="count_list",
            classes="step-option-list",
        )
        yield self._option_list

        # Set default selection (3 agents - index 2)
        if self._option_list:
            self._option_list.highlighted = 2

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Native event handler for option selection."""
        if event.option and event.option.id:
            self._selected_count = str(event.option.id)
            _quickstart_log(f"AgentCountStep: Selected {self._selected_count}")

    def get_value(self) -> int:
        return int(self._selected_count)

    def set_value(self, value: Any) -> None:
        if isinstance(value, int):
            self._selected_count = str(value)
            # Highlight option in OptionList
            idx = next(
                (i for i, (v, _, _) in enumerate(self.COUNTS) if v == str(value)),
                None,
            )
            if idx is not None and self._option_list:
                self._option_list.highlighted = idx


class SetupModeStep(StepComponent):
    """Step for choosing same or different backends per agent using native OptionList."""

    OPTIONS = [
        ("same", "Same Backend for All", "Use the same provider and model for all agents"),
        ("different", "Different Backends", "Configure each agent separately"),
    ]

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._selected_mode: str = "different"
        self._option_list: Optional[OptionList] = None

    def compose(self) -> ComposeResult:
        yield Label("How do you want to configure your agents?", classes="text-input-label")

        # Build native options
        textual_options = []
        for value, label, description in self.OPTIONS:
            option_text = f"[bold]{label}[/bold]\n[dim]{description}[/dim]"
            textual_options.append(Option(option_text, id=value))

        self._option_list = OptionList(
            *textual_options,
            id="mode_list",
            classes="step-option-list",
        )
        yield self._option_list

        # Set default selection (different - second item)
        if self._option_list:
            self._option_list.highlighted = 1

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Native event handler for option selection."""
        if event.option and event.option.id:
            self._selected_mode = str(event.option.id)
            _quickstart_log(f"SetupModeStep: Selected {self._selected_mode}")

    def get_value(self) -> str:
        return self._selected_mode

    def set_value(self, value: Any) -> None:
        if isinstance(value, str):
            self._selected_mode = value
            # Highlight option in OptionList
            idx = next(
                (i for i, (v, _, _) in enumerate(self.OPTIONS) if v == value),
                None,
            )
            if idx is not None and self._option_list:
                self._option_list.highlighted = idx


class ProviderModelStep(StepComponent):
    """Combined step for selecting provider and model.

    Shows provider selection first, then model selection for that provider.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        agent_label: str = "all agents",
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._agent_label = agent_label
        self._provider_select: Optional[Select] = None
        self._model_select: Optional[Select] = None
        self._key_input: Optional[Input] = None
        self._key_label: Optional[Label] = None
        self._providers: List[Tuple[str, str]] = []  # (provider_id, display_name)
        self._models_by_provider: Dict[str, List[str]] = {}
        self._provider_has_key: Dict[str, bool] = {}
        self._provider_env_var: Dict[str, str] = {}
        self._current_provider: Optional[str] = None
        self._current_model: Optional[str] = None

    def _load_providers(self) -> None:
        """Load all providers from ConfigBuilder, tracking which have keys."""
        try:
            from massgen.config_builder import ConfigBuilder

            builder = ConfigBuilder()
            api_keys = builder.detect_api_keys()

            for provider_id, provider_info in builder.PROVIDERS.items():
                name = provider_info.get("name", provider_id)
                models = provider_info.get("models", [])
                has_key = api_keys.get(provider_id, False)
                env_var = provider_info.get("env_var", "")

                self._providers.append((provider_id, name))
                self._models_by_provider[provider_id] = models
                self._provider_has_key[provider_id] = has_key
                self._provider_env_var[provider_id] = env_var

            # Default to first provider that has a key, else first overall
            configured = [pid for pid, _ in self._providers if self._provider_has_key.get(pid)]
            first = configured[0] if configured else (self._providers[0][0] if self._providers else None)
            if first:
                self._current_provider = first
                if self._models_by_provider.get(first):
                    self._current_model = self._models_by_provider[first][0]

        except Exception as e:
            _quickstart_log(f"ProviderModelStep._load_providers error: {e}")

    def _provider_options(self) -> list:
        """Build provider select options, marking unconfigured ones."""
        options = []
        for pid, name in self._providers:
            if self._provider_has_key.get(pid):
                options.append((name, pid))
            else:
                options.append((f"{name} (no API key)", pid))
        return options

    def _update_key_input(self) -> None:
        """Show/hide API key input based on current provider."""
        if not self._key_input or not self._key_label:
            return
        pid = self._current_provider
        if pid and not self._provider_has_key.get(pid):
            env_var = self._provider_env_var.get(pid, "")
            self._key_label.update(f"Enter API key ({env_var}):")
            self._key_label.display = True
            self._key_input.display = True
            self._key_input.placeholder = f"Paste your {env_var} here..."
            self._key_input.value = ""
        else:
            self._key_label.display = False
            self._key_input.display = False

    @staticmethod
    def _save_api_key(env_var: str, key: str) -> None:
        """Save API key to .env file."""
        env_path = Path(".env")
        lines = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()
        # Replace or append
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{env_var}="):
                lines[i] = f"{env_var}={key}"
                found = True
                break
        if not found:
            lines.append(f"{env_var}={key}")
        env_path.write_text("\n".join(lines) + "\n")

    def compose(self) -> ComposeResult:
        self._load_providers()

        yield Label(f"Select provider and model for {self._agent_label}:", classes="text-input-label")

        # Provider selection
        yield Label("Provider:", classes="text-input-label")
        provider_options = self._provider_options()
        self._provider_select = Select(
            provider_options,
            value=self._current_provider,
            id="provider_select",
        )
        yield self._provider_select

        # Inline API key input (hidden by default)
        self._key_label = Label("", classes="text-input-label")
        self._key_label.display = False
        yield self._key_label
        self._key_input = Input(
            placeholder="",
            password=True,
            classes="text-input",
            id="api_key_input",
        )
        self._key_input.display = False
        yield self._key_input

        # Model selection
        yield Label("Model:", classes="text-input-label")
        models = self._models_by_provider.get(self._current_provider, [])
        model_options = [(m, m) for m in models] if models else [("", "No models available")]
        self._model_select = Select(
            model_options,
            value=self._current_model,
            id="model_select",
        )
        yield self._model_select

        self._update_key_input()

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle provider selection change to update model list."""
        if event.select.id == "provider_select" and event.value != Select.BLANK:
            self._current_provider = str(event.value)
            _quickstart_log(f"ProviderModelStep: Provider changed to {self._current_provider}")

            self._update_key_input()

            # Update model select
            if self._model_select:
                models = self._models_by_provider.get(self._current_provider, [])
                model_options = [(m, m) for m in models] if models else [("", "No models available")]
                self._model_select.set_options(model_options)
                if models:
                    self._model_select.value = models[0]
                    self._current_model = models[0]

        elif event.select.id == "model_select" and event.value != Select.BLANK:
            self._current_model = str(event.value)

    def get_value(self) -> Dict[str, str]:
        return {
            "provider": self._current_provider or "",
            "model": self._current_model or "",
        }

    def set_value(self, value: Any) -> None:
        if isinstance(value, dict):
            if "provider" in value and self._provider_select:
                self._current_provider = value["provider"]
                self._provider_select.value = value["provider"]
            if "model" in value and self._model_select:
                self._current_model = value["model"]
                self._model_select.value = value["model"]

    def validate(self) -> Optional[str]:
        if not self._current_provider:
            return "Please select a provider"
        pid = self._current_provider
        if not self._provider_has_key.get(pid):
            # Check if user entered a key
            if self._key_input and self._key_input.value.strip():
                env_var = self._provider_env_var.get(pid, "")
                if env_var:
                    self._save_api_key(env_var, self._key_input.value.strip())
                    self._provider_has_key[pid] = True
            else:
                env_var = self._provider_env_var.get(pid, "")
                return f"Please enter your API key for {pid} ({env_var})"
        if not self._current_model:
            return "Please select a model"
        return None


class TabbedProviderModelStep(StepComponent):
    """Single tabbed step for configuring provider/model per agent."""

    def __init__(
        self,
        wizard_state: WizardState,
        agent_count: int = 3,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._agent_count = agent_count
        self._providers: List[Tuple[str, str]] = []
        self._models_by_provider: Dict[str, List[str]] = {}
        self._provider_has_key: Dict[str, bool] = {}
        self._provider_env_var: Dict[str, str] = {}
        self._tab_selections: Dict[int, Dict[str, Optional[str]]] = {}
        self._provider_selects: Dict[int, Select] = {}
        self._model_selects: Dict[int, Select] = {}
        self._key_inputs: Dict[int, Input] = {}
        self._key_labels: Dict[int, Label] = {}

    def _load_providers(self) -> None:
        """Load all providers from ConfigBuilder, tracking which have keys."""
        try:
            from massgen.config_builder import ConfigBuilder

            builder = ConfigBuilder()
            api_keys = builder.detect_api_keys()

            for provider_id, provider_info in builder.PROVIDERS.items():
                name = provider_info.get("name", provider_id)
                models = provider_info.get("models", [])
                has_key = api_keys.get(provider_id, False)
                env_var = provider_info.get("env_var", "")

                self._providers.append((provider_id, name))
                self._models_by_provider[provider_id] = models
                self._provider_has_key[provider_id] = has_key
                self._provider_env_var[provider_id] = env_var

        except Exception as e:
            _quickstart_log(f"TabbedProviderModelStep._load_providers error: {e}")

    def _provider_options(self) -> list:
        options = []
        for pid, name in self._providers:
            if self._provider_has_key.get(pid):
                options.append((name, pid))
            else:
                options.append((f"{name} (no API key)", pid))
        return options

    def _update_key_input(self, agent_num: int, provider_id: str) -> None:
        key_label = self._key_labels.get(agent_num)
        key_input = self._key_inputs.get(agent_num)
        if not key_label or not key_input:
            return
        if not self._provider_has_key.get(provider_id):
            env_var = self._provider_env_var.get(provider_id, "")
            key_label.update(f"Enter API key ({env_var}):")
            key_label.display = True
            key_input.display = True
            key_input.placeholder = f"Paste your {env_var} here..."
            key_input.value = ""
        else:
            key_label.display = False
            key_input.display = False

    def compose(self) -> ComposeResult:
        self._load_providers()

        # Default to first configured provider
        configured = [pid for pid, _ in self._providers if self._provider_has_key.get(pid)]
        default_provider = configured[0] if configured else (self._providers[0][0] if self._providers else None)
        default_model = self._models_by_provider.get(default_provider, [""])[0] if default_provider else None

        yield Label("Configure provider and model for each agent:", classes="text-input-label")

        provider_options = self._provider_options()

        with TabbedContent():
            for i in range(self._agent_count):
                agent_num = i + 1
                self._tab_selections[agent_num] = {
                    "provider": default_provider,
                    "model": default_model,
                }

                with TabPane(f"Agent {agent_num}", id=f"tab_agent_{agent_num}"):
                    with VerticalScroll():
                        yield Label("Provider:", classes="text-input-label")
                        p_select = Select(
                            provider_options,
                            value=default_provider,
                            id=f"provider_{agent_num}",
                        )
                        self._provider_selects[agent_num] = p_select
                        yield p_select

                        # Inline API key input (hidden by default)
                        k_label = Label("", classes="text-input-label")
                        k_label.display = False
                        self._key_labels[agent_num] = k_label
                        yield k_label
                        k_input = Input(
                            placeholder="",
                            password=True,
                            classes="text-input",
                            id=f"apikey_{agent_num}",
                        )
                        k_input.display = False
                        self._key_inputs[agent_num] = k_input
                        yield k_input

                        yield Label("Model:", classes="text-input-label")
                        models = self._models_by_provider.get(default_provider, [])
                        model_options = [(m, m) for m in models] if models else [("", "No models")]
                        m_select = Select(
                            model_options,
                            value=default_model,
                            id=f"model_{agent_num}",
                        )
                        self._model_selects[agent_num] = m_select
                        yield m_select

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle provider/model changes per tab."""
        sel_id = event.select.id or ""
        if not sel_id or event.value == Select.BLANK:
            return

        # Parse agent number from id like "provider_2" or "model_3"
        parts = sel_id.rsplit("_", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            return
        kind, agent_num = parts[0], int(parts[1])

        if kind == "provider":
            provider = str(event.value)
            self._tab_selections[agent_num]["provider"] = provider
            self._update_key_input(agent_num, provider)
            # Update model select for this agent
            m_select = self._model_selects.get(agent_num)
            if m_select:
                models = self._models_by_provider.get(provider, [])
                model_options = [(m, m) for m in models] if models else [("", "No models")]
                m_select.set_options(model_options)
                if models:
                    m_select.value = models[0]
                    self._tab_selections[agent_num]["model"] = models[0]
        elif kind == "model":
            self._tab_selections[agent_num]["model"] = str(event.value)

    def get_value(self) -> Dict[str, Any]:
        # Store per-agent configs in wizard state
        for agent_num, sel in self._tab_selections.items():
            self.wizard_state.set(
                f"agent_{agent_num}_config",
                {
                    "provider": sel.get("provider", ""),
                    "model": sel.get("model", ""),
                },
            )
        return {"agent_configs": dict(self._tab_selections)}

    def set_value(self, value: Any) -> None:
        if isinstance(value, dict) and "agent_configs" in value:
            for agent_num, sel in value["agent_configs"].items():
                agent_num = int(agent_num)
                self._tab_selections[agent_num] = sel
                p_select = self._provider_selects.get(agent_num)
                m_select = self._model_selects.get(agent_num)
                if p_select and sel.get("provider"):
                    p_select.value = sel["provider"]
                if m_select and sel.get("model"):
                    m_select.value = sel["model"]

    def _get_active_tab_agent_num(self) -> int:
        """Return the agent number of the currently active tab."""
        try:
            tc = self.query_one(TabbedContent)
            active_id = tc.active  # e.g. "tab_agent_2"
            if active_id and active_id.startswith("tab_agent_"):
                return int(active_id.split("_")[-1])
        except Exception:
            pass
        return 1

    def _find_next_incomplete_agent(self, after: int) -> Optional[int]:
        """Find next agent (after given num) that hasn't been explicitly configured.

        Returns None if all agents are filled.
        We consider an agent 'needs attention' if it still has the initial defaults
        and hasn't been visited yet, or simply the next agent tab after current.
        """
        # Simple approach: advance to next tab sequentially
        for num in range(after + 1, self._agent_count + 1):
            return num
        return None

    def try_retreat_tab(self) -> bool:
        """Try to move to the previous agent tab. Returns True if moved, False if on first."""
        current = self._get_active_tab_agent_num()
        if current > 1:
            try:
                tc = self.query_one(TabbedContent)
                tc.active = f"tab_agent_{current - 1}"
                return True
            except Exception:
                pass
        return False

    def try_advance_tab(self) -> bool:
        """Try to move to the next agent tab. Returns True if moved, False if all done."""
        current = self._get_active_tab_agent_num()
        next_num = self._find_next_incomplete_agent(current)
        if next_num is not None:
            try:
                tc = self.query_one(TabbedContent)
                tc.active = f"tab_agent_{next_num}"
                return True
            except Exception:
                pass
        return False

    def validate(self) -> Optional[str]:
        for agent_num in range(1, self._agent_count + 1):
            sel = self._tab_selections.get(agent_num, {})
            pid = sel.get("provider")
            if not pid:
                return f"Please select a provider for Agent {agent_num}"
            if not self._provider_has_key.get(pid):
                key_input = self._key_inputs.get(agent_num)
                if key_input and key_input.value.strip():
                    env_var = self._provider_env_var.get(pid, "")
                    if env_var:
                        ProviderModelStep._save_api_key(env_var, key_input.value.strip())
                        self._provider_has_key[pid] = True
                else:
                    env_var = self._provider_env_var.get(pid, "")
                    return f"Please enter your API key for Agent {agent_num} ({env_var})"
            if not sel.get("model"):
                return f"Please select a model for Agent {agent_num}"
        return None


class ExecutionModeStep(StepComponent):
    """Step for selecting Docker or local execution mode using native OptionList."""

    OPTIONS = [
        ("docker", "Docker Mode (Recommended)", "Full code execution in isolated containers - most powerful"),
        ("local", "Local Mode", "File operations only, no code execution - simpler setup"),
    ]

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._selected_mode: str = "docker"
        self._option_list: Optional[OptionList] = None

    def compose(self) -> ComposeResult:
        yield Label("Select execution mode:", classes="text-input-label")

        # Build native options
        textual_options = []
        for value, label, description in self.OPTIONS:
            option_text = f"[bold]{label}[/bold]\n[dim]{description}[/dim]"
            textual_options.append(Option(option_text, id=value))

        self._option_list = OptionList(
            *textual_options,
            id="exec_list",
            classes="step-option-list",
        )
        yield self._option_list

        # Set default selection (docker - first item)
        if self._option_list:
            self._option_list.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Native event handler for option selection."""
        if event.option and event.option.id:
            self._selected_mode = str(event.option.id)
            _quickstart_log(f"ExecutionModeStep: Selected {self._selected_mode}")

    def get_value(self) -> bool:
        return self._selected_mode == "docker"

    def set_value(self, value: Any) -> None:
        if isinstance(value, bool):
            self._selected_mode = "docker" if value else "local"
            # Highlight option in OptionList
            idx = 0 if self._selected_mode == "docker" else 1
            if self._option_list:
                self._option_list.highlighted = idx


class ContextPathStep(StepComponent):
    """Step for entering optional context/workspace path."""

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._input: Optional[Input] = None

    def compose(self) -> ComposeResult:
        yield Label("Context Path (optional):", classes="text-input-label")
        yield Label(
            "Enter a directory path the agents can access. Leave empty to skip.",
            classes="password-hint",
        )

        self._input = Input(
            placeholder="e.g., /path/to/project or . for current directory",
            classes="text-input",
            id="context_path_input",
        )
        yield self._input

        yield Label(
            "This grants agents read/write access to the specified directory.",
            classes="password-hint",
        )

    def get_value(self) -> Optional[str]:
        if self._input and self._input.value.strip():
            return self._input.value.strip()
        return None

    def set_value(self, value: Any) -> None:
        if self._input and isinstance(value, str):
            self._input.value = value


class ConfigLocationStep(StepComponent):
    """Step for choosing where to save the generated config."""

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._selected: str = "project"
        self._option_list: Optional[OptionList] = None
        self._warning_label: Optional[Label] = None
        self._project_path = Path.cwd() / ".massgen" / "config.yaml"
        self._global_path = Path.home() / ".config" / "massgen" / "config.yaml"

    def _path_for(self, location: str) -> Path:
        return self._global_path if location == "global" else self._project_path

    def _build_options(self) -> list:
        options = []
        for value, label, desc, path in [
            ("project", "This Project (Recommended)", ".massgen/config.yaml in current directory", self._project_path),
            ("global", "Global", "~/.config/massgen/config.yaml — available from any directory", self._global_path),
        ]:
            exists_tag = "  [yellow]⚠ exists[/yellow]" if path.exists() else ""
            option_text = f"[bold]{label}{exists_tag}[/bold]\n[dim]{desc}[/dim]"
            options.append(Option(option_text, id=value))
        return options

    def _update_warning(self) -> None:
        if self._warning_label:
            path = self._path_for(self._selected)
            if path.exists():
                self._warning_label.update(
                    f"[yellow]A config already exists at {path}. It will be overwritten.[/yellow]",
                )
                self._warning_label.display = True
            else:
                self._warning_label.display = False

    def compose(self) -> ComposeResult:
        yield Label("Where should the config be saved?", classes="text-input-label")

        self._option_list = OptionList(
            *self._build_options(),
            id="config_location_list",
            classes="step-option-list",
        )
        yield self._option_list

        if self._option_list:
            self._option_list.highlighted = 0

        self._warning_label = Label("", classes="password-hint")
        self._warning_label.display = False
        yield self._warning_label

        self._update_warning()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option and event.option.id:
            self._selected = str(event.option.id)
            self._update_warning()

    def get_value(self) -> str:
        return self._selected

    def set_value(self, value: Any) -> None:
        if isinstance(value, str):
            self._selected = value
            options = [("project", 0), ("global", 1)]
            idx = next((i for v, i in options if v == value), None)
            if idx is not None and self._option_list:
                self._option_list.highlighted = idx
            self._update_warning()


class ConfigPreviewStep(StepComponent):
    """Step for previewing the generated YAML configuration."""

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._textarea: Optional[TextArea] = None

    def _generate_preview(self) -> str:
        """Generate YAML config from wizard state."""
        try:
            from massgen.config_builder import ConfigBuilder

            builder = ConfigBuilder()

            # Get agent count
            agent_count = self.wizard_state.get("agent_count", 3)
            setup_mode = self.wizard_state.get("setup_mode", "same")
            use_docker = self.wizard_state.get("execution_mode", True)
            context_path = self.wizard_state.get("context_path")

            # Build agents config
            agents_config = []

            if setup_mode == "same":
                # Same provider/model for all agents
                provider_model = self.wizard_state.get("provider_model", {})
                provider = provider_model.get("provider", "openai")
                model = provider_model.get("model", "gpt-4o-mini")

                for i in range(agent_count):
                    agents_config.append(
                        {
                            "id": f"agent_{i + 1}",
                            "type": provider,
                            "model": model,
                        },
                    )
            else:
                # Different provider/model per agent
                for i in range(agent_count):
                    agent_config = self.wizard_state.get(f"agent_{i + 1}_config", {})
                    agents_config.append(
                        {
                            "id": f"agent_{i + 1}",
                            "type": agent_config.get("provider", "openai"),
                            "model": agent_config.get("model", "gpt-4o-mini"),
                        },
                    )

            # Build context paths
            context_paths = None
            if context_path:
                context_paths = [{"path": context_path, "permission": "write"}]

            # Generate config
            config = builder._generate_quickstart_config(
                agents_config=agents_config,
                context_paths=context_paths,
                use_docker=use_docker,
            )

            return yaml.dump(config, default_flow_style=False, sort_keys=False)

        except Exception as e:
            _quickstart_log(f"ConfigPreviewStep._generate_preview error: {e}")
            return f"# Error generating preview: {e}"

    def compose(self) -> ComposeResult:
        yield Label("Preview Configuration:", classes="preview-header")

        content = self._generate_preview()
        self._textarea = TextArea(
            content,
            classes="preview-content",
            id="config_preview",
            read_only=True,
        )
        yield self._textarea

    async def on_mount(self) -> None:
        """Refresh preview on mount."""
        if self._textarea:
            content = self._generate_preview()
            self._textarea.text = content

    def get_value(self) -> str:
        return self._textarea.text if self._textarea else ""


class QuickstartCompleteStep(StepComponent):
    """Final step showing completion and launch options."""

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)

    def compose(self) -> ComposeResult:
        with Container(classes="complete-container"):
            yield Label("OK", classes="complete-icon")
            yield Label("Configuration Ready!", classes="complete-title")

            location = self.wizard_state.get("config_location", "project")
            default = "~/.config/massgen/config.yaml" if location == "global" else ".massgen/config.yaml"
            config_path = self.wizard_state.get("config_path", default)
            yield Label(f"Saved to: {config_path}", classes="complete-message")

            launch_option = self.wizard_state.get("launch_option", "terminal")
            if launch_option == "terminal":
                yield Label("Launching MassGen Terminal TUI...", classes="complete-next-steps")
            elif launch_option == "web":
                yield Label("Launching MassGen Web UI...", classes="complete-next-steps")
            else:
                yield Label("Configuration saved. Run with:", classes="complete-next-steps")
                yield Label(f"  massgen --config {config_path}", classes="complete-next-steps")

    def get_value(self) -> bool:
        return True


class QuickstartWizard(WizardModal):
    """Quickstart wizard for creating MassGen configurations.

    Flow:
    1. Welcome
    2. Agent count
    3. Setup mode (same/different) - skipped if 1 agent
    4. Provider/model selection
    5. Execution mode
    6. Context path
    7. Preview
    8. Launch options
    9. Complete
    """

    def __init__(
        self,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._dynamic_steps_added = False
        self._config_path: Optional[str] = None

    def get_steps(self) -> List[WizardStep]:
        """Return the wizard steps."""
        return [
            WizardStep(
                id="welcome",
                title="MassGen Quickstart",
                description="Create a configuration in minutes",
                component_class=QuickstartWelcomeStep,
            ),
            WizardStep(
                id="agent_count",
                title="Agent Count",
                description="How many agents should collaborate?",
                component_class=AgentCountStep,
            ),
            WizardStep(
                id="setup_mode",
                title="Setup Mode",
                description="Same or different backends per agent?",
                component_class=SetupModeStep,
                skip_condition=lambda state: state.get("agent_count", 3) == 1,
            ),
            WizardStep(
                id="provider_model",
                title="Provider & Model",
                description="Choose your AI provider and model",
                component_class=ProviderModelStep,
                skip_condition=lambda state: state.get("setup_mode") == "different",
            ),
            # Dynamic per-agent steps are inserted here when setup_mode == "different"
            WizardStep(
                id="execution_mode",
                title="Execution Mode",
                description="Docker or local execution?",
                component_class=ExecutionModeStep,
            ),
            WizardStep(
                id="context_path",
                title="Context Path",
                description="Optional workspace directory",
                component_class=ContextPathStep,
            ),
            WizardStep(
                id="config_location",
                title="Save Location",
                description="Where to save the config",
                component_class=ConfigLocationStep,
            ),
            WizardStep(
                id="preview",
                title="Preview",
                description="Review your configuration",
                component_class=ConfigPreviewStep,
            ),
            WizardStep(
                id="launch_options",
                title="Launch Options",
                description="How do you want to proceed?",
                component_class=LaunchOptionsStep,
            ),
        ]

    async def action_next_step(self) -> None:
        """Override to insert per-agent model steps when setup_mode is 'different'."""
        if not self._current_component:
            return

        step = self._steps[self.state.current_step_idx]

        # Validate current step
        error = self._current_component.validate()
        if error:
            self._show_error(error)
            self.state.set_error(step.id, error)
            return

        # Save current step data
        value = self._current_component.get_value()
        self.state.step_data[step.id] = value
        self.state.clear_error(step.id)

        # After setup_mode selection, insert per-agent steps if "different"
        if step.id == "setup_mode" and not self._dynamic_steps_added:
            setup_mode = value if isinstance(value, str) else "same"
            agent_count = self.state.get("agent_count", 3)

            if setup_mode == "different" and agent_count > 1:
                # Find insertion point (after provider_model step)
                insert_idx = next(
                    (i for i, s in enumerate(self._steps) if s.id == "provider_model"),
                    None,
                )
                if insert_idx is not None:
                    # Insert a single tabbed step after the (skipped) provider_model step
                    count = agent_count

                    def make_tabbed_step(n):
                        class _TabbedStep(TabbedProviderModelStep):
                            def __init__(self, wizard_state, **kwargs):
                                super().__init__(wizard_state, agent_count=n, **kwargs)

                        return _TabbedStep

                    self._steps.insert(
                        insert_idx + 1,
                        WizardStep(
                            id="tabbed_agent_models",
                            title="Agent Models",
                            description="Configure provider and model for each agent",
                            component_class=make_tabbed_step(count),
                        ),
                    )

            self._dynamic_steps_added = True

        # If on tabbed step, advance to next tab before leaving the step
        if isinstance(self._current_component, TabbedProviderModelStep):
            if self._current_component.try_advance_tab():
                return

        # Find next step
        next_idx = self._find_next_step(self.state.current_step_idx + 1)
        if next_idx >= len(self._steps):
            await self._complete_wizard()
        else:
            await self._show_step(next_idx)

    async def action_previous_step(self) -> None:
        """Override to navigate between tabs before leaving the tabbed step."""
        if self._current_component and isinstance(self._current_component, TabbedProviderModelStep):
            if self._current_component.try_retreat_tab():
                return
        await super().action_previous_step()

    async def on_wizard_complete(self) -> Any:
        """Save the configuration and return launch options."""
        _quickstart_log("QuickstartWizard.on_wizard_complete: Saving configuration")

        try:
            from massgen.config_builder import ConfigBuilder

            builder = ConfigBuilder()

            # Get wizard state values
            agent_count = self.state.get("agent_count", 3)
            setup_mode = self.state.get("setup_mode", "same")
            use_docker = self.state.get("execution_mode", True)
            context_path = self.state.get("context_path")
            launch_option = self.state.get("launch_options", "terminal")

            # Build agents config
            agents_config = []

            if setup_mode == "same" or agent_count == 1:
                provider_model = self.state.get("provider_model", {})
                provider = provider_model.get("provider", "openai")
                model = provider_model.get("model", "gpt-4o-mini")

                for i in range(agent_count):
                    agents_config.append(
                        {
                            "id": f"agent_{i + 1}",
                            "type": provider,
                            "model": model,
                        },
                    )
            else:
                for i in range(agent_count):
                    agent_config = self.state.get(f"agent_{i + 1}_config", {})
                    if not agent_config:
                        # Fallback to shared config
                        provider_model = self.state.get("provider_model", {})
                        agent_config = {
                            "provider": provider_model.get("provider", "openai"),
                            "model": provider_model.get("model", "gpt-4o-mini"),
                        }
                    agents_config.append(
                        {
                            "id": f"agent_{i + 1}",
                            "type": agent_config.get("provider", "openai"),
                            "model": agent_config.get("model", "gpt-4o-mini"),
                        },
                    )

            # Build context paths
            context_paths = None
            if context_path:
                context_paths = [{"path": context_path, "permission": "write"}]

            # Generate config
            config = builder._generate_quickstart_config(
                agents_config=agents_config,
                context_paths=context_paths,
                use_docker=use_docker,
            )

            # Save config to chosen location
            config_location = self.state.get("config_location", "project")
            if config_location == "global":
                config_dir = Path.home() / ".config" / "massgen"
            else:
                config_dir = Path(".massgen")
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "config.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            self._config_path = str(config_path.absolute())
            self.state.set("config_path", self._config_path)

            _quickstart_log(f"QuickstartWizard: Config saved to {self._config_path}")

            return {
                "success": True,
                "config_path": self._config_path,
                "launch_option": launch_option,
            }

        except Exception as e:
            _quickstart_log(f"QuickstartWizard: Failed to save config: {e}")
            return {
                "success": False,
                "error": str(e),
            }
