# -*- coding: utf-8 -*-
"""
Plan Options Popover Widget for MassGen TUI.

Provides a dropdown popover for plan mode configuration:
- Plan selection (choose existing plans)
- Plan details preview (tasks, status, created date)
- Depth selector (shallow/medium/deep) - shown only in "plan" mode
- Broadcast toggle (human/agents/off) - shown only in "plan" mode
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Select, Static

if TYPE_CHECKING:
    from massgen.frontend.displays.tui_modes import PlanDepth
    from massgen.plan_storage import PlanSession


class PlanSelected(Message):
    """Message emitted when a plan is selected."""

    def __init__(self, plan_id: Optional[str], is_new: bool = False) -> None:
        """Initialize the message.

        Args:
            plan_id: The selected plan ID, or None if creating new.
            is_new: True if user selected "Create new plan".
        """
        self.plan_id = plan_id
        self.is_new = is_new
        super().__init__()


class PlanDepthChanged(Message):
    """Message emitted when plan depth is changed."""

    def __init__(self, depth: "PlanDepth") -> None:
        """Initialize the message.

        Args:
            depth: The new depth value ("shallow", "medium", or "deep").
        """
        self.depth = depth
        super().__init__()


class BroadcastModeChanged(Message):
    """Message emitted when broadcast mode is changed."""

    def __init__(self, broadcast: Any) -> None:
        """Initialize the message.

        Args:
            broadcast: The new broadcast value ("human", "agents", or False).
        """
        self.broadcast = broadcast
        super().__init__()


class ViewPlanRequested(Message):
    """Message emitted when user wants to view the full plan."""

    def __init__(self, plan_id: str, tasks: List[Any]) -> None:
        """Initialize the message.

        Args:
            plan_id: The plan ID to view.
            tasks: List of task dictionaries from the plan.
        """
        self.plan_id = plan_id
        self.tasks = tasks
        super().__init__()


def _popover_log(msg: str) -> None:
    """Log to TUI debug file."""
    try:
        import logging

        log = logging.getLogger("massgen.tui.popover")
        if not log.handlers:
            handler = logging.FileHandler("/tmp/massgen_tui_debug.log", mode="a")
            handler.setFormatter(logging.Formatter("%(asctime)s [POPOVER] %(message)s", datefmt="%H:%M:%S"))
            log.addHandler(handler)
            log.setLevel(logging.DEBUG)
            log.propagate = False
        log.debug(msg)
    except Exception:
        pass


class PlanOptionsPopover(Widget):
    """Popover widget for plan mode configuration.

    Shows:
    - Plan selector (in execute mode) - choose from existing plans
    - Plan details preview - shows selected plan info
    - Depth selector (in plan mode) - shallow/medium/deep
    - Broadcast toggle (in plan mode) - human/agents/off
    """

    DEFAULT_CSS = """
    PlanOptionsPopover {
        layer: overlay;
        dock: bottom;
        width: 70;
        height: auto;
        max-height: 35;
        background: $surface;
        border: solid $primary;
        padding: 1;
        margin-bottom: 3;
        display: none;
    }

    PlanOptionsPopover.visible {
        display: block;
    }

    PlanOptionsPopover #popover_title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    PlanOptionsPopover .section-label {
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 0;
    }

    PlanOptionsPopover Select {
        width: 100%;
        margin-bottom: 1;
    }

    PlanOptionsPopover #plan_details {
        background: $surface-darken-1;
        border: solid $primary-darken-2;
        padding: 1;
        margin: 1 0;
        height: auto;
        max-height: 8;
    }

    PlanOptionsPopover #plan_details.hidden {
        display: none;
    }

    PlanOptionsPopover .detail-line {
        color: $text-muted;
        height: 1;
    }

    PlanOptionsPopover .detail-value {
        color: $text;
    }

    PlanOptionsPopover .task-preview {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }

    PlanOptionsPopover #close_btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def __init__(
        self,
        *,
        plan_mode: str = "normal",
        available_plans: Optional[List["PlanSession"]] = None,
        current_plan_id: Optional[str] = None,
        current_depth: "PlanDepth" = "medium",
        current_broadcast: Any = "human",
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the plan options popover.

        Args:
            plan_mode: Current plan mode ("normal", "plan", "execute").
            available_plans: List of available plan sessions.
            current_plan_id: Currently selected plan ID.
            current_depth: Current plan depth setting.
            current_broadcast: Current broadcast setting.
            id: Optional DOM ID.
            classes: Optional CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._plan_mode = plan_mode
        self._available_plans = available_plans or []
        self._current_plan_id = current_plan_id
        self._current_depth = current_depth
        self._current_broadcast = current_broadcast
        self._plan_details_widget: Optional[Static] = None
        self._initialized = False  # Track if popover has been shown (to ignore events during recompose)

    def compose(self) -> ComposeResult:
        """Create the popover contents.

        Content differs by mode:
        - "plan" mode: Shows depth and human feedback options only
        - "execute" mode: Shows plan selector and plan details only
        """
        # Title changes based on mode
        if self._plan_mode == "plan":
            yield Label("Planning Options", id="popover_title")
        else:
            yield Label("Select Plan", id="popover_title")

        with Vertical(id="popover_content"):
            # Execute mode: Show plan selector and details
            if self._plan_mode == "execute" and self._available_plans:
                yield Label("Select Plan:", classes="section-label")

                # Build plan options
                plan_options = [("Latest (auto)", "latest")]
                for plan in self._available_plans[:5]:  # Limit to 5 most recent
                    try:
                        metadata = plan.load_metadata()
                        # Format: plan_id (status)
                        label = f"{plan.plan_id[:15]}... ({metadata.status})"
                        plan_options.append((label, plan.plan_id))
                    except Exception:
                        plan_options.append((plan.plan_id[:20], plan.plan_id))

                yield Select(
                    plan_options,
                    value=self._current_plan_id or "latest",
                    id="plan_selector",
                )

                # Plan details section - shows info about selected plan
                self._plan_details_widget = Static("", id="plan_details")
                yield self._plan_details_widget

                # Load initial plan details
                self._update_plan_details(self._current_plan_id or "latest")

                # View Plan button - opens full task list modal
                yield Button("View Full Plan", id="view_plan_btn", variant="primary")

            # Plan mode: Show depth and human feedback options
            if self._plan_mode == "plan":
                yield Label("Plan Depth:", classes="section-label")
                depth_options = [
                    ("Shallow (5-10 tasks)", "shallow"),
                    ("Medium (20-50 tasks)", "medium"),
                    ("Deep (100-200+ tasks)", "deep"),
                ]
                yield Select(
                    depth_options,
                    value=self._current_depth,
                    id="depth_selector",
                )

                yield Label("Human Feedback:", classes="section-label")
                broadcast_options = [
                    ("Enabled (agents ask human)", "human"),
                    ("Agents only (no human)", "agents"),
                    ("Disabled (autonomous)", "off"),
                ]
                # Convert False to "off" for display
                broadcast_value = self._current_broadcast if self._current_broadcast else "off"
                if broadcast_value is True:
                    broadcast_value = "human"
                yield Select(
                    broadcast_options,
                    value=broadcast_value,
                    id="broadcast_selector",
                )

            yield Button("Close", id="close_btn", variant="default")

    def _get_plan_by_id(self, plan_id: str) -> Optional["PlanSession"]:
        """Find a plan by ID from available plans."""
        for plan in self._available_plans:
            if plan.plan_id == plan_id:
                return plan
        return None

    def _update_plan_details(self, plan_id: str) -> None:
        """Update the plan details display for the selected plan."""
        if not self._plan_details_widget:
            return

        if plan_id == "new":
            self._plan_details_widget.update("[dim]Will create a new plan[/]")
            return

        if plan_id == "latest":
            # Use the first (latest) plan
            if self._available_plans:
                plan = self._available_plans[0]
            else:
                self._plan_details_widget.update("[dim]No plans available[/]")
                return
        else:
            plan = self._get_plan_by_id(plan_id)
            if not plan:
                self._plan_details_widget.update("[dim]Plan not found[/]")
                return

        # Build details text
        try:
            metadata = plan.load_metadata()

            # Parse created date
            try:
                created_dt = datetime.fromisoformat(metadata.created_at)
                created_str = created_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                created_str = metadata.created_at[:16]

            # Get task count and preview
            task_count = 0
            task_preview = ""
            plan_file = plan.workspace_dir / "plan.json"
            if plan_file.exists():
                try:
                    data = json.loads(plan_file.read_text())
                    tasks = data.get("tasks", [])
                    task_count = len(tasks)

                    # Get first 2-3 task descriptions as preview
                    if tasks:
                        previews = []
                        for t in tasks[:3]:
                            desc = t.get("description", "")[:40]
                            if len(t.get("description", "")) > 40:
                                desc += "..."
                            previews.append(f"  • {desc}")
                        task_preview = "\n".join(previews)
                except Exception:
                    pass

            # Format status with color
            status = metadata.status
            status_color = {
                "planning": "yellow",
                "ready": "green",
                "executing": "blue",
                "completed": "green",
                "failed": "red",
            }.get(status, "white")

            details = f"[bold]Status:[/] [{status_color}]{status}[/]\n"
            details += f"[bold]Created:[/] {created_str}\n"
            details += f"[bold]Tasks:[/] {task_count}"

            # Show the original planning prompt if available (most useful info)
            planning_prompt = getattr(metadata, "planning_prompt", None)
            planning_turn = getattr(metadata, "planning_turn", None)
            if planning_prompt:
                # Truncate long prompts
                prompt_preview = planning_prompt[:100]
                if len(planning_prompt) > 100:
                    prompt_preview += "..."
                # Show turn info if available
                turn_info = f" [dim](turn {planning_turn})[/]" if planning_turn else ""
                details += f"\n[dim]Query{turn_info}:[/]\n[italic]{prompt_preview}[/]"
            elif task_preview:
                # Fall back to task preview if no prompt stored
                details += f"\n[dim]Preview:[/]\n{task_preview}"

            self._plan_details_widget.update(details)

        except Exception as e:
            self._plan_details_widget.update(f"[red]Error loading plan: {e}[/]")

    def show(self) -> None:
        """Show the popover positioned on the right side."""
        _popover_log(f"show() called, current classes: {list(self.classes)}")

        # Calculate right-side position based on screen width
        if self.app and self.app.size:
            screen_width = self.app.size.width
            popover_width = 70  # Match CSS width
            right_margin = 10
            # Clamp to non-negative to prevent popover from rendering off left edge
            offset_x = max(0, screen_width - popover_width - right_margin)
            self.styles.offset = (offset_x, 0)
            _popover_log(f"  Positioned at offset_x={offset_x} (screen={screen_width})")

        self.add_class("visible")
        _popover_log(f"show() after add_class, classes: {list(self.classes)}")
        self._initialized = True
        _popover_log("show() set _initialized=True")

        # Refresh plan details when showing
        if self._plan_details_widget and self._available_plans:
            self._update_plan_details(self._current_plan_id or "latest")

    def hide(self) -> None:
        """Hide the popover."""
        _popover_log(f"hide() called, current classes: {list(self.classes)}")
        self.remove_class("visible")
        # Reset initialized so next show will work correctly
        self._initialized = False
        _popover_log("hide() set _initialized=False")

    def toggle(self) -> None:
        """Toggle popover visibility."""
        _popover_log(f"toggle() called, visible={'visible' in self.classes}")
        if "visible" in self.classes:
            self.hide()
        else:
            self.show()

    def on_blur(self, event) -> None:
        """Handle blur - log but don't hide."""
        _popover_log("on_blur() called")
        # Don't hide on blur - let user click elsewhere

    def on_focus(self, event) -> None:
        """Handle focus."""
        _popover_log("on_focus() called")

    def _validate_plan_for_execution(self, plan_id: str) -> tuple[bool, str]:
        """Validate a plan exists and is ready for execution.

        Args:
            plan_id: The plan ID to validate.

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        plan = self._get_plan_by_id(plan_id)
        if not plan:
            return False, f"Plan '{plan_id}' not found"

        # Check metadata exists and has valid status
        try:
            metadata = plan.load_metadata()
            status = metadata.status
            if status not in ("ready", "completed"):
                return False, f"Plan status is '{status}' (expected 'ready' or 'completed')"
        except FileNotFoundError:
            return False, "Plan metadata file not found"
        except Exception as e:
            return False, f"Error loading plan metadata: {e}"

        # Check plan.json exists and has tasks
        plan_file = plan.workspace_dir / "plan.json"
        if not plan_file.exists():
            return False, "Plan file (plan.json) not found in workspace"

        try:
            plan_data = json.loads(plan_file.read_text())
            tasks = plan_data.get("tasks", [])
            if not tasks:
                return False, "Plan has no tasks"
        except json.JSONDecodeError as e:
            return False, f"Plan file is corrupted: {e}"
        except Exception as e:
            return False, f"Error reading plan file: {e}"

        return True, ""

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        _popover_log(f"on_select_changed: selector={event.select.id}, value={event.value}, initialized={self._initialized}")

        # Ignore events during recompose (before show() is called)
        if not self._initialized:
            _popover_log("  -> ignoring, not initialized")
            return

        selector_id = event.select.id

        if selector_id == "plan_selector":
            value = str(event.value)

            # Update plan details display
            self._update_plan_details(value)

            if value == "new":
                self.post_message(PlanSelected(None, is_new=True))
            elif value == "latest":
                # Validate latest plan if one exists
                if self._available_plans:
                    is_valid, error_msg = self._validate_plan_for_execution(
                        self._available_plans[0].plan_id,
                    )
                    if not is_valid:
                        _popover_log(f"  -> latest plan validation failed: {error_msg}")
                        self.app.notify(f"Latest plan invalid: {error_msg}", severity="warning")
                        return
                self.post_message(PlanSelected(None, is_new=False))
            else:
                # Validate specific plan before accepting selection
                is_valid, error_msg = self._validate_plan_for_execution(value)
                if not is_valid:
                    _popover_log(f"  -> plan validation failed: {error_msg}")
                    self.app.notify(f"Plan invalid: {error_msg}", severity="warning")
                    return
                self.post_message(PlanSelected(value, is_new=False))

        elif selector_id == "depth_selector":
            self.post_message(PlanDepthChanged(str(event.value)))

        elif selector_id == "broadcast_selector":
            value = str(event.value)
            # Convert "off" back to False
            broadcast = False if value == "off" else value
            self.post_message(BroadcastModeChanged(broadcast))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close_btn":
            self.hide()
            event.stop()
        elif event.button.id == "view_plan_btn":
            self._handle_view_plan()
            event.stop()

    def _handle_view_plan(self) -> None:
        """Handle View Plan button click - emit ViewPlanRequested message."""
        _popover_log("_handle_view_plan called")

        # Get the currently selected plan
        plan_id = self._current_plan_id or "latest"

        if plan_id == "new":
            # Can't view a plan that doesn't exist yet
            return

        if plan_id == "latest" and self._available_plans:
            plan = self._available_plans[0]
        else:
            plan = self._get_plan_by_id(plan_id)

        if not plan:
            _popover_log(f"  -> plan not found: {plan_id}")
            return

        # Load tasks from plan.json
        plan_file = plan.workspace_dir / "plan.json"
        if not plan_file.exists():
            _popover_log(f"  -> plan file not found: {plan_file}")
            return

        try:
            data = json.loads(plan_file.read_text())
            tasks = data.get("tasks", [])
            _popover_log(f"  -> loaded {len(tasks)} tasks from {plan.plan_id}")

            # Emit message to open the modal
            self.post_message(ViewPlanRequested(plan.plan_id, tasks))

            # Hide the popover after opening the modal
            self.hide()

        except Exception as e:
            _popover_log(f"  -> error loading plan: {e}")
