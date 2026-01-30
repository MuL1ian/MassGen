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
from textual.containers import Container
from textual.widgets import Input, Label, OptionList, Select, TextArea
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
        self._selected_mode: str = "same"
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

        # Set default selection (same - first item)
        if self._option_list:
            self._option_list.highlighted = 0

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
        self._providers: List[Tuple[str, str]] = []  # (provider_id, display_name)
        self._models_by_provider: Dict[str, List[str]] = {}
        self._current_provider: Optional[str] = None
        self._current_model: Optional[str] = None

    def _load_providers(self) -> None:
        """Load available providers from ConfigBuilder."""
        try:
            from massgen.config_builder import ConfigBuilder

            builder = ConfigBuilder()
            api_keys = builder.detect_api_keys()

            for provider_id, provider_info in builder.PROVIDERS.items():
                # Only show providers with configured API keys
                if not api_keys.get(provider_id, False):
                    continue

                name = provider_info.get("name", provider_id)
                models = provider_info.get("models", [])

                self._providers.append((provider_id, name))
                self._models_by_provider[provider_id] = models

            # Set default provider and model
            if self._providers:
                self._current_provider = self._providers[0][0]
                if self._models_by_provider.get(self._current_provider):
                    self._current_model = self._models_by_provider[self._current_provider][0]

        except Exception as e:
            _quickstart_log(f"ProviderModelStep._load_providers error: {e}")

    def compose(self) -> ComposeResult:
        self._load_providers()

        yield Label(f"Select provider and model for {self._agent_label}:", classes="text-input-label")

        # Provider selection
        yield Label("Provider:", classes="text-input-label")
        # Select expects (label, value) tuples, so swap to (name, pid)
        provider_options = [(name, pid) for pid, name in self._providers]
        self._provider_select = Select(
            provider_options,
            value=self._current_provider,
            id="provider_select",
        )
        yield self._provider_select

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

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle provider selection change to update model list."""
        if event.select.id == "provider_select" and event.value != Select.BLANK:
            self._current_provider = str(event.value)
            _quickstart_log(f"ProviderModelStep: Provider changed to {self._current_provider}")

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
        if not self._current_model:
            return "Please select a model"
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

            config_path = self.wizard_state.get("config_path", "quickstart_config.yaml")
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
                    # Insert after the (skipped) provider_model step
                    insert_idx += 1
                    for i in range(agent_count):
                        agent_num = i + 1
                        agent_label = f"Agent {agent_num}"

                        def make_agent_step(label, num):
                            class PerAgentProviderModelStep(ProviderModelStep):
                                def __init__(self, wizard_state, **kwargs):
                                    super().__init__(wizard_state, agent_label=label, **kwargs)

                                def get_value(self):
                                    val = super().get_value()
                                    # Also store in wizard state for on_wizard_complete
                                    self.wizard_state.set(f"agent_{num}_config", val)
                                    return val

                            return PerAgentProviderModelStep

                        self._steps.insert(
                            insert_idx + i,
                            WizardStep(
                                id=f"agent_{agent_num}_model",
                                title=f"Agent {agent_num} Model",
                                description=f"Choose provider and model for Agent {agent_num}",
                                component_class=make_agent_step(agent_label, agent_num),
                            ),
                        )

            self._dynamic_steps_added = True

        # Find next step
        next_idx = self._find_next_step(self.state.current_step_idx + 1)
        if next_idx >= len(self._steps):
            await self._complete_wizard()
        else:
            await self._show_step(next_idx)

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

            # Save config file
            config_path = Path("quickstart_config.yaml")
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
