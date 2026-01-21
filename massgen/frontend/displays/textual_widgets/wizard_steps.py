# -*- coding: utf-8 -*-
"""
Reusable Step Components for MassGen TUI Wizards.

Provides pre-built step components for common wizard interactions:
- WelcomeStep: Welcome screen with title and description
- SingleSelectStep: Radio-button style single selection
- MultiSelectStep: Checkbox-style multiple selection
- ToggleStep: Boolean toggle (on/off)
- PasswordInputStep: Masked password input
- TextInputStep: Single-line text input
- TextAreaStep: Multi-line text area
- ModelSelectStep: Model selection with filtering
- PreviewStep: Read-only preview display
- CompleteStep: Completion message with next steps
"""

from typing import Any, Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Checkbox, Input, Label, Select, Switch, TextArea

from .wizard_base import StepComponent, WizardState


def _step_log(msg: str) -> None:
    """Log to TUI debug file."""
    try:
        import logging

        log = logging.getLogger("massgen.tui.debug")
        if not log.handlers:
            handler = logging.FileHandler("/tmp/massgen_tui_debug.log", mode="a")
            handler.setFormatter(logging.Formatter("%(asctime)s [STEP] %(message)s", datefmt="%H:%M:%S"))
            log.addHandler(handler)
            log.setLevel(logging.DEBUG)
            log.propagate = False
        log.debug(msg)
    except Exception:
        pass


class WelcomeStep(StepComponent):
    """Welcome screen step with feature list.

    The title and subtitle are shown in the wizard header.
    This component displays additional features/info.

    Attributes:
        title: Ignored (shown in header).
        subtitle: Ignored (shown in header).
        features: List of features/benefits to display.
    """

    DEFAULT_CSS = """
    WelcomeStep {
        width: 100%;
        height: auto;
        padding: 1 2;
    }

    WelcomeStep .wizard-welcome {
        width: 100%;
        height: auto;
        padding: 1 0;
    }

    WelcomeStep .wizard-welcome-intro {
        color: #8b949e;
        width: 100%;
        margin-bottom: 1;
    }

    WelcomeStep .wizard-welcome-feature {
        color: #3fb950;
        width: 100%;
        margin-bottom: 0;
    }

    WelcomeStep .wizard-welcome-hint {
        color: #6e7681;
        text-style: italic;
        width: 100%;
        margin-top: 2;
    }
    """

    def __init__(
        self,
        wizard_state: WizardState,
        title: str = "Welcome",
        subtitle: str = "",
        features: Optional[List[str]] = None,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._title = title
        self._subtitle = subtitle
        self._features = features or []

    def compose(self) -> ComposeResult:
        with Vertical(classes="wizard-welcome"):
            if self._features:
                yield Label("This wizard will help you:", classes="wizard-welcome-intro")
                for feature in self._features:
                    yield Label(f"  ✓ {feature}", classes="wizard-welcome-feature")
            yield Label("Press [Next] to continue or [Escape] to cancel", classes="wizard-welcome-hint")

    def get_value(self) -> Any:
        return True  # Welcome step always "completes"


class SingleSelectStep(StepComponent):
    """Single selection step with radio-button style options.

    Displays a list of options, only one can be selected at a time.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        options: List[Tuple[str, str, str]],  # (value, label, description)
        default_value: Optional[str] = None,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize single select step.

        Args:
            wizard_state: The wizard state.
            options: List of (value, label, description) tuples.
            default_value: Optional default selection.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._options = options
        self._default_value = default_value
        self._selected_value: Optional[str] = default_value
        self._option_widgets: Dict[str, Container] = {}

    def compose(self) -> ComposeResult:
        with ScrollableContainer(classes="option-list"):
            for value, label, description in self._options:
                option_classes = "option-item"
                if value == self._selected_value:
                    option_classes += " selected"

                with Container(classes=option_classes, id=f"option_{value}") as container:
                    yield Label(label, classes="option-label")
                    if description:
                        yield Label(description, classes="option-description")
                    self._option_widgets[value] = container

    async def on_click(self, event) -> None:
        """Handle clicks on option items."""
        # Find which option was clicked
        target = event.target
        while target and not (hasattr(target, "id") and target.id and target.id.startswith("option_")):
            target = target.parent

        if target and hasattr(target, "id") and target.id:
            value = target.id.replace("option_", "")
            await self._select_option(value)

    async def _select_option(self, value: str) -> None:
        """Select an option."""
        _step_log(f"SingleSelectStep._select_option: {value}")

        # Update UI
        for opt_value, widget in self._option_widgets.items():
            if opt_value == value:
                widget.add_class("selected")
            else:
                widget.remove_class("selected")

        self._selected_value = value

    def get_value(self) -> Any:
        return self._selected_value

    def set_value(self, value: Any) -> None:
        if value:
            self._selected_value = value
            # Update UI if mounted
            for opt_value, widget in self._option_widgets.items():
                if opt_value == value:
                    widget.add_class("selected")
                else:
                    widget.remove_class("selected")

    def validate(self) -> Optional[str]:
        if not self._selected_value:
            return "Please select an option"
        return None


class MultiSelectStep(StepComponent):
    """Multi-selection step with checkbox-style options.

    Displays a list of options, multiple can be selected.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        options: List[Tuple[str, str, str]],  # (value, label, description)
        default_values: Optional[List[str]] = None,
        min_selections: int = 0,
        max_selections: Optional[int] = None,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize multi-select step.

        Args:
            wizard_state: The wizard state.
            options: List of (value, label, description) tuples.
            default_values: Optional list of default selections.
            min_selections: Minimum number of required selections.
            max_selections: Maximum number of allowed selections.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._options = options
        self._default_values = default_values or []
        self._min_selections = min_selections
        self._max_selections = max_selections
        self._checkboxes: Dict[str, Checkbox] = {}

    def compose(self) -> ComposeResult:
        with ScrollableContainer(classes="provider-list"):
            for value, label, description in self._options:
                checkbox = Checkbox(
                    f"{label} - {description}" if description else label,
                    value=value in self._default_values,
                    id=f"checkbox_{value}",
                )
                self._checkboxes[value] = checkbox
                yield checkbox

    def get_value(self) -> List[str]:
        return [value for value, checkbox in self._checkboxes.items() if checkbox.value]

    def set_value(self, value: Any) -> None:
        if isinstance(value, list):
            for opt_value, checkbox in self._checkboxes.items():
                checkbox.value = opt_value in value

    def validate(self) -> Optional[str]:
        selected = self.get_value()
        if len(selected) < self._min_selections:
            return f"Please select at least {self._min_selections} option(s)"
        if self._max_selections and len(selected) > self._max_selections:
            return f"Please select at most {self._max_selections} option(s)"
        return None


class ProviderSelectStep(StepComponent):
    """Provider selection step with API key status indicators.

    Shows providers with visual indicators for configured/unconfigured status.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        providers: List[Tuple[str, str, bool]],  # (provider_id, display_name, is_configured)
        allow_multiple: bool = False,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize provider select step.

        Args:
            wizard_state: The wizard state.
            providers: List of (provider_id, display_name, is_configured) tuples.
            allow_multiple: If True, allow multiple selections.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._providers = providers
        self._allow_multiple = allow_multiple
        self._selected: List[str] = []
        self._provider_widgets: Dict[str, Container] = {}

    def compose(self) -> ComposeResult:
        with ScrollableContainer(classes="provider-list"):
            for provider_id, display_name, is_configured in self._providers:
                status_icon = "[green]|[/green]" if is_configured else "[dim]|[/dim]"
                status_text = "(configured)" if is_configured else "(not configured)"

                item_classes = "provider-item"
                if is_configured:
                    item_classes += " configured"
                else:
                    item_classes += " unconfigured"

                with Container(classes=item_classes, id=f"provider_{provider_id}") as container:
                    yield Label(f"{status_icon} {display_name} {status_text}")
                    self._provider_widgets[provider_id] = container

    async def on_click(self, event) -> None:
        """Handle clicks on provider items."""
        target = event.target
        while target and not (hasattr(target, "id") and target.id and target.id.startswith("provider_")):
            target = target.parent

        if target and hasattr(target, "id") and target.id:
            provider_id = target.id.replace("provider_", "")
            await self._toggle_provider(provider_id)

    async def _toggle_provider(self, provider_id: str) -> None:
        """Toggle provider selection."""
        _step_log(f"ProviderSelectStep._toggle_provider: {provider_id}")

        if provider_id in self._selected:
            self._selected.remove(provider_id)
            self._provider_widgets[provider_id].remove_class("selected")
        else:
            if not self._allow_multiple:
                # Clear other selections
                for pid in self._selected:
                    self._provider_widgets[pid].remove_class("selected")
                self._selected.clear()

            self._selected.append(provider_id)
            self._provider_widgets[provider_id].add_class("selected")

    def get_value(self) -> List[str]:
        return self._selected.copy()

    def set_value(self, value: Any) -> None:
        if isinstance(value, list):
            self._selected = value.copy()
            for pid, widget in self._provider_widgets.items():
                if pid in self._selected:
                    widget.add_class("selected")
                else:
                    widget.remove_class("selected")

    def validate(self) -> Optional[str]:
        if not self._selected:
            return "Please select at least one provider"
        return None


class ToggleStep(StepComponent):
    """Boolean toggle step with label and description.

    Shows a toggle switch for yes/no decisions.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        label: str,
        description: str = "",
        default_value: bool = False,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize toggle step.

        Args:
            wizard_state: The wizard state.
            label: Label for the toggle.
            description: Description of what the toggle does.
            default_value: Initial toggle state.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._label = label
        self._description = description
        self._default_value = default_value
        self._switch: Optional[Switch] = None

    def compose(self) -> ComposeResult:
        with Container(classes="toggle-container"):
            yield Label(self._label, classes="toggle-label")
            self._switch = Switch(value=self._default_value, id="toggle_switch")
            yield self._switch
            if self._description:
                yield Label(self._description, classes="toggle-description")

    def get_value(self) -> bool:
        return self._switch.value if self._switch else self._default_value

    def set_value(self, value: Any) -> None:
        if self._switch and isinstance(value, bool):
            self._switch.value = value


class PasswordInputStep(StepComponent):
    """Password input step with masked input.

    Shows a labeled password field for entering secrets like API keys.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        label: str,
        hint: str = "",
        placeholder: str = "",
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize password input step.

        Args:
            wizard_state: The wizard state.
            label: Label for the input field.
            hint: Hint text shown below the input.
            placeholder: Placeholder text in the input.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._label = label
        self._hint = hint
        self._placeholder = placeholder
        self._input: Optional[Input] = None

    def compose(self) -> ComposeResult:
        with Container(classes="password-container"):
            yield Label(self._label, classes="password-label")
            self._input = Input(
                placeholder=self._placeholder,
                password=True,
                classes="password-input",
                id="password_input",
            )
            yield self._input
            if self._hint:
                yield Label(self._hint, classes="password-hint")

    def get_value(self) -> str:
        return self._input.value if self._input else ""

    def set_value(self, value: Any) -> None:
        if self._input and isinstance(value, str):
            self._input.value = value

    def validate(self) -> Optional[str]:
        value = self.get_value()
        if not value or not value.strip():
            return "Please enter a value"
        return None


class TextInputStep(StepComponent):
    """Single-line text input step.

    Shows a labeled text input field.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        label: str,
        hint: str = "",
        placeholder: str = "",
        required: bool = False,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize text input step.

        Args:
            wizard_state: The wizard state.
            label: Label for the input field.
            hint: Hint text shown below the input.
            placeholder: Placeholder text in the input.
            required: If True, value is required for validation.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._label = label
        self._hint = hint
        self._placeholder = placeholder
        self._required = required
        self._input: Optional[Input] = None

    def compose(self) -> ComposeResult:
        with Container(classes="text-input-container"):
            yield Label(self._label, classes="text-input-label")
            self._input = Input(
                placeholder=self._placeholder,
                classes="text-input",
                id="text_input",
            )
            yield self._input
            if self._hint:
                yield Label(self._hint, classes="password-hint")

    def get_value(self) -> str:
        return self._input.value if self._input else ""

    def set_value(self, value: Any) -> None:
        if self._input and isinstance(value, str):
            self._input.value = value

    def validate(self) -> Optional[str]:
        if self._required:
            value = self.get_value()
            if not value or not value.strip():
                return "This field is required"
        return None


class TextAreaStep(StepComponent):
    """Multi-line text area step.

    Shows a labeled text area for longer input.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        label: str,
        hint: str = "",
        default_value: str = "",
        required: bool = False,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize text area step.

        Args:
            wizard_state: The wizard state.
            label: Label for the text area.
            hint: Hint text shown below.
            default_value: Initial text content.
            required: If True, value is required.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._label = label
        self._hint = hint
        self._default_value = default_value
        self._required = required
        self._textarea: Optional[TextArea] = None

    def compose(self) -> ComposeResult:
        with Container(classes="text-input-container"):
            yield Label(self._label, classes="text-input-label")
            self._textarea = TextArea(
                self._default_value,
                classes="text-area-input",
                id="text_area",
            )
            yield self._textarea
            if self._hint:
                yield Label(self._hint, classes="password-hint")

    def get_value(self) -> str:
        return self._textarea.text if self._textarea else ""

    def set_value(self, value: Any) -> None:
        if self._textarea and isinstance(value, str):
            self._textarea.text = value

    def validate(self) -> Optional[str]:
        if self._required:
            value = self.get_value()
            if not value or not value.strip():
                return "This field is required"
        return None


class ModelSelectStep(StepComponent):
    """Model selection step with search/filter.

    Shows a searchable list of models from a provider.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        models: List[str],
        label: str = "Select Model",
        default_model: Optional[str] = None,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize model select step.

        Args:
            wizard_state: The wizard state.
            models: List of model names/IDs.
            label: Label for the selection.
            default_model: Optional default model.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._models = models
        self._label = label
        self._default_model = default_model
        self._select: Optional[Select] = None

    def compose(self) -> ComposeResult:
        with Container(classes="model-select-container"):
            yield Label(self._label, classes="model-select-label")

            # Use Select widget for model selection
            options = [(model, model) for model in self._models]
            default = self._default_model if self._default_model in self._models else None
            if not default and self._models:
                default = self._models[0]

            self._select = Select(
                options,
                value=default,
                id="model_select",
            )
            yield self._select

    def get_value(self) -> Optional[str]:
        if self._select and self._select.value != Select.BLANK:
            return str(self._select.value)
        return None

    def set_value(self, value: Any) -> None:
        if self._select and isinstance(value, str) and value in self._models:
            self._select.value = value

    def validate(self) -> Optional[str]:
        if not self.get_value():
            return "Please select a model"
        return None


class PreviewStep(StepComponent):
    """Read-only preview step for displaying content.

    Shows generated content (like YAML config) for review.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        title: str = "Preview",
        content_callback=None,  # Callable[[WizardState], str]
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize preview step.

        Args:
            wizard_state: The wizard state.
            title: Header title for the preview.
            content_callback: Function to generate preview content from wizard state.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._title = title
        self._content_callback = content_callback
        self._textarea: Optional[TextArea] = None

    def compose(self) -> ComposeResult:
        with Container(classes="preview-container"):
            yield Label(self._title, classes="preview-header")
            content = ""
            if self._content_callback:
                try:
                    content = self._content_callback(self.wizard_state)
                except Exception as e:
                    content = f"Error generating preview: {e}"

            self._textarea = TextArea(
                content,
                classes="preview-content",
                id="preview_content",
                read_only=True,
            )
            yield self._textarea

    async def on_mount(self) -> None:
        """Refresh preview content on mount."""
        if self._content_callback and self._textarea:
            try:
                content = self._content_callback(self.wizard_state)
                self._textarea.text = content
            except Exception as e:
                self._textarea.text = f"Error generating preview: {e}"

    def get_value(self) -> str:
        return self._textarea.text if self._textarea else ""


class CompleteStep(StepComponent):
    """Completion step showing success and next actions.

    Shows a success message with optional next steps.
    """

    def __init__(
        self,
        wizard_state: WizardState,
        title: str = "Complete!",
        message: str = "",
        next_steps: Optional[List[str]] = None,
        icon: str = "OK",
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize complete step.

        Args:
            wizard_state: The wizard state.
            title: Success title.
            message: Success message.
            next_steps: Optional list of suggested next actions.
            icon: Icon/emoji to display.
        """
        super().__init__(wizard_state, id=id, classes=classes)
        self._title = title
        self._message = message
        self._next_steps = next_steps or []
        self._icon = icon

    def compose(self) -> ComposeResult:
        with Container(classes="complete-container"):
            yield Label(self._icon, classes="complete-icon")
            yield Label(self._title, classes="complete-title")
            if self._message:
                yield Label(self._message, classes="complete-message")
            for step in self._next_steps:
                yield Label(f"  {step}", classes="complete-next-steps")

    def get_value(self) -> bool:
        return True  # Complete step always "completes"


class SaveLocationStep(StepComponent):
    """Step for selecting where to save configuration files.

    Shows options for .env file locations.
    """

    LOCATIONS = [
        (".env", ".env (current directory)", "Highest priority, project-specific"),
        ("configs/.env", "configs/.env", "Project configs directory"),
        ("~/.massgen/.env", "~/.massgen/.env", "Global user config"),
        ("~/.config/massgen/.env", "~/.config/massgen/.env", "XDG config directory"),
    ]

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._selected_location: Optional[str] = ".env"
        self._location_widgets: Dict[str, Container] = {}

    def _sanitize_id(self, value: str) -> str:
        """Sanitize a value to be a valid DOM ID."""
        import re

        # Replace invalid characters with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", value)
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"loc_{sanitized}"
        return sanitized

    def compose(self) -> ComposeResult:
        with ScrollableContainer(classes="option-list"):
            for value, label, description in self.LOCATIONS:
                option_classes = "option-item"
                if value == self._selected_location:
                    option_classes += " selected"

                safe_id = f"location_{self._sanitize_id(value)}"
                with Container(classes=option_classes, id=safe_id) as container:
                    yield Label(label, classes="option-label")
                    yield Label(description, classes="option-description")
                    self._location_widgets[value] = container

    async def on_click(self, event) -> None:
        """Handle clicks on location items."""
        target = event.target
        while target and not (hasattr(target, "id") and target.id and target.id.startswith("location_")):
            target = target.parent

        if target and hasattr(target, "id") and target.id:
            # Reverse the ID transformation to get the original value
            location_id = target.id.replace("location_", "")
            for value, _, _ in self.LOCATIONS:
                if self._sanitize_id(value) == location_id:
                    await self._select_location(value)
                    break

    async def _select_location(self, value: str) -> None:
        """Select a location."""
        _step_log(f"SaveLocationStep._select_location: {value}")

        for loc_value, widget in self._location_widgets.items():
            if loc_value == value:
                widget.add_class("selected")
            else:
                widget.remove_class("selected")

        self._selected_location = value

    def get_value(self) -> str:
        return self._selected_location or ".env"

    def set_value(self, value: Any) -> None:
        if isinstance(value, str):
            self._selected_location = value
            for loc_value, widget in self._location_widgets.items():
                if loc_value == value:
                    widget.add_class("selected")
                else:
                    widget.remove_class("selected")


class LaunchOptionsStep(StepComponent):
    """Step for selecting launch options after quickstart.

    Options: Terminal TUI, Web UI, Save only.
    """

    OPTIONS = [
        ("terminal", "Launch Terminal TUI", "Start MassGen in the terminal interface"),
        ("web", "Launch Web UI", "Start MassGen with the web interface"),
        ("save", "Save Config Only", "Save the configuration file without launching"),
    ]

    def __init__(
        self,
        wizard_state: WizardState,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(wizard_state, id=id, classes=classes)
        self._selected_option: str = "terminal"
        self._option_widgets: Dict[str, Container] = {}

    def compose(self) -> ComposeResult:
        with ScrollableContainer(classes="option-list"):
            for value, label, description in self.OPTIONS:
                option_classes = "option-item"
                if value == self._selected_option:
                    option_classes += " selected"

                with Container(classes=option_classes, id=f"launch_{value}") as container:
                    yield Label(label, classes="option-label")
                    yield Label(description, classes="option-description")
                    self._option_widgets[value] = container

    async def on_click(self, event) -> None:
        """Handle clicks on option items."""
        target = event.target
        while target and not (hasattr(target, "id") and target.id and target.id.startswith("launch_")):
            target = target.parent

        if target and hasattr(target, "id") and target.id:
            value = target.id.replace("launch_", "")
            await self._select_option(value)

    async def _select_option(self, value: str) -> None:
        """Select an option."""
        for opt_value, widget in self._option_widgets.items():
            if opt_value == value:
                widget.add_class("selected")
            else:
                widget.remove_class("selected")

        self._selected_option = value

    def get_value(self) -> str:
        return self._selected_option

    def set_value(self, value: Any) -> None:
        if isinstance(value, str) and value in [o[0] for o in self.OPTIONS]:
            self._selected_option = value
            for opt_value, widget in self._option_widgets.items():
                if opt_value == value:
                    widget.add_class("selected")
                else:
                    widget.remove_class("selected")
