# -*- coding: utf-8 -*-
"""
Textual Terminal Display for MassGen Coordination

"""

import os
import re
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from massgen.logger_config import get_log_session_dir, logger

from .terminal_display import TerminalDisplay

try:
    from rich.text import Text
    from textual import events
    from textual.app import App, ComposeResult
    from textual.containers import Container, ScrollableContainer, Vertical
    from textual.screen import ModalScreen
    from textual.widgets import Footer, Label, RichLog, Static, TextArea

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


# Emoji fallback mapping for terminals without Unicode support
EMOJI_FALLBACKS = {
    "🚀": ">>",  # Launch
    "💡": "(!)",  # Question
    "🤖": "[A]",  # Agent
    "✅": "[✓]",  # Success
    "❌": "[X]",  # Error
    "🔄": "[↻]",  # Processing
    "📊": "[=]",  # Stats
    "🎯": "[>]",  # Target
    "⚡": "[!]",  # Fast
    "🎤": "[M]",  # Presentation
    "🔍": "[?]",  # Search/Evaluation
    "⚠️": "[!]",  # Warning
    "📋": "[□]",  # Summary
    "🧠": "[B]",  # Brain/Reasoning
}

CRITICAL_PATTERNS = {
    "vote": "✅ Vote recorded",
    "status": ["📊 Status changed", "Status: "],
    "tool": "🔧",
    "presentation": "🎤 Final Presentation",
}

CRITICAL_CONTENT_TYPES = {"status", "presentation", "tool", "vote", "error"}


class TextualTerminalDisplay(TerminalDisplay):
    """Textual-based terminal display with feature parity to Rich."""

    def __init__(self, agent_ids: List[str], **kwargs: Any):
        super().__init__(agent_ids, **kwargs)
        # Validate agent IDs
        self._validate_agent_ids()
        self._dom_id_mapping: Dict[str, str] = {}

        # Configuration (same pattern as RichTerminalDisplay)
        self.theme = kwargs.get("theme", "dark")
        self.refresh_rate = kwargs.get("refresh_rate")
        self.enable_syntax_highlighting = kwargs.get("enable_syntax_highlighting", True)
        self.show_timestamps = kwargs.get("show_timestamps", True)
        self.max_line_length = kwargs.get("max_line_length", 100)
        self.max_web_search_lines = kwargs.get("max_web_search_lines", 4)
        self.truncate_web_on_status_change = kwargs.get("truncate_web_on_status_change", True)
        self.max_web_lines_on_status_change = kwargs.get("max_web_lines_on_status_change", 3)
        # Runtime toggle to ignore hotkeys/key handling when enabled
        self.safe_keyboard_mode = kwargs.get("safe_keyboard_mode", False)
        self.max_buffer_batch = kwargs.get("max_buffer_batch", 50)
        # Startup flag to disable all keyboard bindings at app init
        self._keyboard_interactive_mode = kwargs.get("keyboard_interactive_mode", True)

        # File output
        default_output_dir = kwargs.get("output_dir")
        if default_output_dir is None:
            try:
                default_output_dir = get_log_session_dir() / "agent_outputs"
            except Exception:
                default_output_dir = Path("output") / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(default_output_dir)
        self.agent_files = {}
        self.system_status_file = None
        self.final_presentation_file = None
        self.final_presentation_latest = None

        # Textual app
        self._app = None

        # Display state
        self.question = ""
        self.log_filename = None
        self.restart_reason = None
        self.restart_instructions = None
        self._final_answer_cache: Optional[str] = None
        self._final_answer_metadata: Dict[str, Any] = {}
        self._post_evaluation_lines: Deque[str] = deque(maxlen=20)
        self._final_stream_active = False
        self._final_stream_buffer: str = ""
        self._final_presentation_agent: Optional[str] = None

        # Emoji support detection
        self.emoji_support = self._detect_emoji_support()
        self._terminal_type = self._detect_terminal_type()

        if self.refresh_rate is None:
            self.refresh_rate = self._get_adaptive_refresh_rate(self._terminal_type)
        else:
            self.refresh_rate = int(self.refresh_rate)

        if self.enable_syntax_highlighting is None:
            self.enable_syntax_highlighting = True

        # Buffering - derive default from refresh rate unless explicitly set
        default_buffer_flush = kwargs.get("buffer_flush_interval")
        if default_buffer_flush is None:
            if self._terminal_type in ("vscode", "windows_terminal"):
                default_buffer_flush = 0.3  # 300ms for smoother Windows/VSCode rendering
            else:
                adaptive_flush = max(0.1, 1 / max(self.refresh_rate, 1))
                default_buffer_flush = min(adaptive_flush, 0.15)
        self.buffer_flush_interval = default_buffer_flush
        self._buffers = {agent_id: [] for agent_id in self.agent_ids}
        self._buffer_lock = threading.Lock()

        # Web-search filtering helpers
        self._recent_web_chunks: Dict[str, Deque[str]] = {agent_id: deque(maxlen=self.max_web_search_lines) for agent_id in self.agent_ids}

    def _validate_agent_ids(self):
        """Validate agent IDs for security and robustness."""
        if not self.agent_ids:
            raise ValueError("At least one agent ID is required")

        MAX_AGENT_ID_LENGTH = 100

        for agent_id in self.agent_ids:
            # Check length
            if len(agent_id) > MAX_AGENT_ID_LENGTH:
                truncated_preview = agent_id[:50] + "..."
                raise ValueError(f"Agent ID exceeds maximum length of {MAX_AGENT_ID_LENGTH} characters: {truncated_preview}")

            # Check if empty or whitespace-only
            if not agent_id or not agent_id.strip():
                raise ValueError("Agent ID cannot be empty or whitespace-only")

        # Check for duplicates
        if len(self.agent_ids) != len(set(self.agent_ids)):
            raise ValueError("Duplicate agent IDs detected")

    def _detect_emoji_support(self) -> bool:
        """Detect if terminal supports emoji."""
        import locale

        term_program = os.environ.get("TERM_PROGRAM", "")
        if term_program in ["vscode", "iTerm.app", "Apple_Terminal"]:
            return True

        if os.environ.get("WT_SESSION"):
            return True

        if os.environ.get("WT_PROFILE_ID"):
            return True

        try:
            encoding = locale.getpreferredencoding()
            if encoding.lower() in ["utf-8", "utf8"]:
                return True
        except Exception:
            pass

        lang = os.environ.get("LANG", "")
        if "UTF-8" in lang or "utf8" in lang:
            return True

        return False

    def _get_icon(self, emoji: str) -> str:
        """Get emoji or fallback based on terminal support."""
        if self.emoji_support:
            return emoji
        return EMOJI_FALLBACKS.get(emoji, emoji)

    def _is_critical_content(self, content: str, content_type: str) -> bool:
        """Identify content that should flush immediately (prefer type, keep legacy patterns)."""
        if content_type in CRITICAL_CONTENT_TYPES:
            return True

        lowered = content.lower()
        if "vote recorded" in lowered:
            return True

        for value in CRITICAL_PATTERNS.values():
            if isinstance(value, list):
                if any(pattern in content for pattern in value):
                    return True
            else:
                if value in content:
                    return True
        return False

    def _detect_terminal_type(self) -> str:
        """Detect terminal type and capabilities."""
        if os.environ.get("TERM_PROGRAM") == "vscode":
            return "vscode"

        if os.environ.get("TERM_PROGRAM") == "iTerm.app":
            return "iterm"

        if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"):
            return "ssh"

        if os.environ.get("WT_SESSION"):
            return "windows_terminal"

        return "unknown"

    def _get_adaptive_refresh_rate(self, terminal_type: str) -> int:
        """Get optimal refresh rate based on terminal."""
        rates = {
            "ssh": 4,
            "vscode": 4,
            "iterm": 10,
            "windows_terminal": 4,
            "unknown": 6,
        }
        return rates.get(terminal_type, 6)

    def _write_to_agent_file(self, agent_id: str, content: str):
        """Write content to agent's output file."""
        if agent_id not in self.agent_files:
            return

        file_path = self.agent_files[agent_id]
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                suffix = "" if content.endswith("\n") else "\n"
                f.write(content + suffix)
                f.flush()
        except OSError as exc:
            logger.warning(f"Failed to append to agent log {file_path} for {agent_id}: {exc}")

    def _write_to_system_file(self, content: str):
        """Write content to system status file."""
        if not self.system_status_file:
            return

        try:
            with open(self.system_status_file, "a", encoding="utf-8") as f:
                if self.show_timestamps:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    f.write(f"[{timestamp}] {content}\n")
                else:
                    f.write(f"{content}\n")
                f.flush()
        except OSError as exc:
            logger.warning(f"Failed to append to system status log {self.system_status_file}: {exc}")

    def _call_app_method(self, method_name: str, *args: Any, **kwargs: Any):
        """Invoke a Textual app method safely regardless of calling thread."""
        if not self._app:
            return

        callback = getattr(self._app, method_name, None)
        if not callback:
            return

        app_thread_id = getattr(self._app, "_thread_id", None)
        if app_thread_id is not None and app_thread_id == threading.get_ident():
            callback(*args, **kwargs)
        else:
            self._app.call_from_thread(callback, *args, **kwargs)

    def initialize(self, question: str, log_filename: Optional[str] = None):
        """Initialize display with file output."""
        self.question = question
        self.log_filename = log_filename

        # Create output directory
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create agent output files
        for agent_id in self.agent_ids:
            file_path = self.output_dir / f"{agent_id}.txt"
            self.agent_files[agent_id] = file_path
            # Initialize file with header
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"=== {agent_id.upper()} OUTPUT LOG ===\n\n")

        # Create system status file
        self.system_status_file = self.output_dir / "system_status.txt"
        with open(self.system_status_file, "w", encoding="utf-8") as f:
            f.write("=== SYSTEM STATUS LOG ===\n")
            f.write(f"Question: {question}\n\n")

        # Final presentation paths (agent-specific path will be set when persisting)
        self.final_presentation_file = None
        self.final_presentation_latest = None

        # Create Textual app
        if TEXTUAL_AVAILABLE:
            self._app = TextualApp(
                self,
                question,
                buffers=self._buffers,
                buffer_lock=self._buffer_lock,
                buffer_flush_interval=self.buffer_flush_interval,
            )

    def update_agent_content(self, agent_id: str, content: str, content_type: str = "thinking"):
        """Update agent content with appropriate formatting.

        Args:
            agent_id: Agent identifier
            content: Content to display
            content_type: Type of content - "thinking", "tool", "status", "presentation"
        """
        if not content:
            return

        display_type = "status" if content_type == "thinking" and self._is_critical_content(content, content_type) else content_type

        prepared = self._prepare_agent_content(agent_id, content, display_type)

        # Store in memory for retrieval
        self.agent_outputs[agent_id].append(content)

        # Write to file immediately
        self._write_to_agent_file(agent_id, content)

        if not prepared:
            return

        is_critical = self._is_critical_content(content, display_type)

        with self._buffer_lock:
            self._buffers[agent_id].append(
                {
                    "content": prepared,
                    "type": display_type,
                    "timestamp": datetime.now(),
                    "force_jump": False,
                },
            )
            buffered_len = len(self._buffers[agent_id])

        if self._app and (is_critical or buffered_len >= self.max_buffer_batch):
            self._app.request_flush()

    def update_agent_status(self, agent_id: str, status: str):
        """Update status for a specific agent."""
        self.agent_status[agent_id] = status
        self._reset_web_cache(agent_id, truncate_history=self.truncate_web_on_status_change)

        # Clear buffered noisy content and jump to latest status for this agent
        if self._app:
            self._app.request_flush()
        with self._buffer_lock:
            existing = self._buffers.get(agent_id, [])
            preserved: List[Dict[str, Any]] = []
            for entry in existing:
                entry_content = entry.get("content", "")
                entry_type = entry.get("type", "thinking")
                if self._is_critical_content(entry_content, entry_type):
                    preserved.append(entry)
            self._buffers[agent_id] = preserved
            self._buffers[agent_id].append(
                {
                    "content": f"📊 Status changed to {status}",
                    "type": "status",
                    "timestamp": datetime.now(),
                    "force_jump": True,
                },
            )

        # Update status in app if running
        if self._app:
            self._call_app_method("update_agent_status", agent_id, status)

        # Write to agent file
        status_msg = f"\n[Status Changed: {status.upper()}]\n"
        self._write_to_agent_file(agent_id, status_msg)

    def add_orchestrator_event(self, event: str):
        """Add an orchestrator coordination event."""
        self.orchestrator_events.append(event)

        # Write to system file
        self._write_to_system_file(event)

        if self._app:
            self._app.request_flush()

        # Update app if running
        if self._app:
            self._call_app_method("add_orchestrator_event", event)

    def show_final_answer(self, answer: str, vote_results=None, selected_agent=None):
        """Show final answer with flush effect."""
        stream_buffer = self._final_stream_buffer.strip() if hasattr(self, "_final_stream_buffer") else ""
        display_answer = answer or stream_buffer
        if self._final_stream_active:
            self._end_final_answer_stream()
        elif not stream_buffer and self._app:
            # Fallback: show the final content in the streaming panel even if chunks never arrived
            self._final_stream_active = True
            self._final_stream_buffer = display_answer
            self._call_app_method(
                "begin_final_stream",
                selected_agent or "Unknown",
                vote_results or {},
            )
            self._call_app_method("update_final_stream", display_answer)
        self._final_answer_metadata = {
            "selected_agent": selected_agent,
            "vote_results": vote_results or {},
        }
        self._final_presentation_agent = selected_agent

        # Write to final presentation file(s)
        persist_needed = self._final_answer_cache is None or self._final_answer_cache != display_answer
        if persist_needed:
            self._persist_final_presentation(display_answer, selected_agent, vote_results)
            self._final_answer_cache = display_answer

        self._write_to_system_file("Final presentation ready.")

        # Trigger modal
        if self._app:
            self._call_app_method(
                "show_final_presentation",
                display_answer,
                vote_results,
                selected_agent,
            )

    def show_post_evaluation_content(self, content: str, agent_id: str):
        """Display post-evaluation streaming content."""
        # Write to agent file
        eval_msg = f"\n[POST-EVALUATION]\n{content}"
        self._write_to_agent_file(agent_id, eval_msg)
        for line in content.splitlines() or [content]:
            clean = line.strip()
            if clean:
                self._post_evaluation_lines.append(clean)

        # Update app if running
        if self._app:
            self._app.call_from_thread(
                self._app.show_post_evaluation,
                content,
                agent_id,
            )

    def show_restart_banner(self, reason: str, instructions: str, attempt: int, max_attempts: int):
        """Display restart decision banner."""
        banner_msg = f"\n{'=' * 60}\n" f"RESTART TRIGGERED (Attempt {attempt}/{max_attempts})\n" f"Reason: {reason}\n" f"Instructions: {instructions}\n" f"{'=' * 60}\n"

        # Write to system file
        self._write_to_system_file(banner_msg)

        # Update app if running
        if self._app:
            self._app.call_from_thread(
                self._app.show_restart_banner,
                reason,
                instructions,
                attempt,
                max_attempts,
            )

    def show_restart_context_panel(self, reason: str, instructions: str):
        """Display restart context panel at top of UI (for attempt 2+)."""
        self.restart_reason = reason
        self.restart_instructions = instructions

        # Update app if running
        if self._app:
            self._app.call_from_thread(
                self._app.show_restart_context,
                reason,
                instructions,
            )

    def cleanup(self):
        """Cleanup and exit Textual app."""
        if self._app:
            self._app.exit()
            self._app = None
        self._post_evaluation_lines.clear()
        self._final_stream_active = False
        self._final_stream_buffer = ""
        self._final_answer_cache = None
        self._final_answer_metadata = {}
        self._final_presentation_agent = None

    def run(self):
        """Run Textual app in main thread."""
        if self._app and TEXTUAL_AVAILABLE:
            self._app.run()

    async def run_async(self):
        """Run Textual app within an existing asyncio event loop."""
        if self._app and TEXTUAL_AVAILABLE:
            await self._app.run_async()

    # Rich parity methods (not in BaseDisplay, but needed for feature parity)
    def display_vote_results(self, vote_results: Dict[str, Any]):
        """Display vote results in formatted table."""
        formatted = self._format_vote_results(vote_results)
        self._call_app_method("display_vote_results", formatted)

        # Write to system file
        self._write_to_system_file(f"Vote Results: {vote_results}")

    def display_coordination_table(self):
        """Display coordination table using existing builder."""
        table_text = self._format_coordination_table_from_orchestrator()
        self._call_app_method("display_coordination_table", table_text)

    def _format_coordination_table_from_orchestrator(self) -> str:
        """Build coordination table text with best effort."""
        table_text = "Coordination data is not available yet."
        try:
            from massgen.frontend.displays.create_coordination_table import (
                CoordinationTableBuilder,
            )

            tracker = getattr(self.orchestrator, "coordination_tracker", None)
            if tracker:
                events_data = [event.to_dict() for event in getattr(tracker, "events", [])]
                session_data = {
                    "session_metadata": {
                        "user_prompt": getattr(tracker, "user_prompt", ""),
                        "agent_ids": getattr(tracker, "agent_ids", []),
                        "start_time": getattr(tracker, "start_time", None),
                        "end_time": getattr(tracker, "end_time", None),
                        "final_winner": getattr(tracker, "final_winner", None),
                    },
                    "events": events_data,
                }
                builder = CoordinationTableBuilder(session_data)
                table_text = self._format_coordination_table(builder)
        except Exception as exc:
            table_text = f"Unable to build coordination table: {exc}"

        return table_text

    def show_agent_selector(self):
        """Show interactive agent selector modal."""
        self._call_app_method("show_agent_selector")

    def stream_final_answer_chunk(self, chunk: str, selected_agent: Optional[str], vote_results: Optional[Dict[str, Any]] = None):
        """Stream incoming final presentation content into the Textual UI."""
        if not chunk:
            return

        if not self._final_stream_active:
            # Speed up flushing during final presentation
            try:
                if self._app:
                    self._app.buffer_flush_interval = min(self._app.buffer_flush_interval, 0.05)
            except Exception:
                pass
            self._final_stream_active = True
            self._final_stream_buffer = ""
            self._final_answer_metadata = {
                "selected_agent": selected_agent,
                "vote_results": vote_results or {},
            }
            self._final_presentation_agent = selected_agent
            if self._app:
                self._call_app_method(
                    "begin_final_stream",
                    selected_agent or "Unknown",
                    vote_results or {},
                )

        # Preserve natural spacing; avoid forcing newlines between streamed chunks
        spacer = ""
        if self._final_stream_buffer:
            prev = self._final_stream_buffer[-1]
            next_char = chunk[0] if chunk else ""
            if not prev.isspace() and next_char and not next_char.isspace():
                spacer = " "
        self._final_stream_buffer += f"{spacer}{chunk}"

        if self._app:
            self._call_app_method("update_final_stream", chunk)

    def _end_final_answer_stream(self):
        """Hide streaming panel when final presentation completes."""
        if not self._final_stream_active:
            return
        self._final_stream_active = False
        if self._app:
            self._call_app_method("end_final_stream")
        # Persist any buffered stream even if show_final_answer wasn't called immediately
        if self._final_stream_buffer and not self._final_answer_cache:
            final_content = self._final_stream_buffer.strip()
            self._persist_final_presentation(
                final_content,
                self._final_presentation_agent,
                self._final_answer_metadata.get("vote_results"),
            )
            self._final_answer_cache = final_content

    # Formatting helpers --------------------------------------------------
    def _prepare_agent_content(self, agent_id: str, content: str, content_type: str) -> Optional[str]:
        """Normalize agent content, apply filters, and truncate noisy sections."""
        if not content:
            return None

        if agent_id not in self._recent_web_chunks:
            self._recent_web_chunks[agent_id] = deque(maxlen=self.max_web_search_lines)

        if self._should_filter_content(content, content_type):
            return None

        if content_type in {"status", "presentation", "tool"}:
            self._reset_web_cache(agent_id)

        if self._is_web_search_content(content):
            truncated = self._truncate_web_content(content)
            history = self._recent_web_chunks.get(agent_id)
            if history is not None:
                history.append(truncated)
            return truncated

        # Don't wrap here - let AgentPanel handle it with RichLog
        return content

    def _truncate_web_content(self, content: str) -> str:
        """Trim verbose web search snippets while keeping the useful prefix."""
        max_len = min(60, self.max_line_length // 2)
        if len(content) <= max_len:
            return content

        truncated = content[:max_len]
        for token in [". ", "! ", "? ", ", "]:
            idx = truncated.rfind(token)
            if idx > max_len // 2:
                truncated = truncated[: idx + 1]
                break
        return truncated.rstrip() + "..."

    def _should_filter_content(self, content: str, content_type: str) -> bool:
        """Drop metadata-only lines and ultra-long noise blocks."""
        if content_type in {"status", "presentation", "error", "tool"}:
            return False

        stripped = content.strip()
        if stripped.startswith("...") and stripped.endswith("..."):
            return True

        if len(stripped) > 1500 and self._is_web_search_content(stripped):
            return True

        return False

    def _is_web_search_content(self, content: str) -> bool:
        """Heuristic detection for web-search/tool snippets."""
        lowered = content.lower()
        markers = [
            "search query",
            "search result",
            "web search",
            "url:",
            "source:",
        ]
        return any(marker in lowered for marker in markers) or lowered.startswith("http")

    def _reset_web_cache(self, agent_id: str, truncate_history: bool = False):
        """Reset stored web search snippets after a status change."""
        if agent_id in self._recent_web_chunks:
            self._recent_web_chunks[agent_id].clear()

        if truncate_history:
            # Trim buffered web content to reduce noise after status transitions
            with self._buffer_lock:
                buf = self._buffers.get(agent_id, [])
                if buf:
                    trimmed: List[Dict[str, Any]] = []
                    web_count = 0
                    for entry in reversed(buf):
                        if self._is_web_search_content(entry.get("content", "")):
                            web_count += 1
                            if web_count > self.max_web_lines_on_status_change:
                                continue
                        trimmed.append(entry)
                    trimmed.reverse()
                    self._buffers[agent_id] = trimmed

    def _format_vote_results(self, vote_results: Dict[str, Any]) -> str:
        """Turn vote results dict into a readable multiline string for Textual modal."""
        if not vote_results:
            return "No vote data is available yet."

        lines = ["🗳️ Vote Results", "=" * 40]
        vote_counts = vote_results.get("vote_counts", {})
        winner = vote_results.get("winner")
        is_tie = vote_results.get("is_tie", False)

        if vote_counts:
            lines.append("\n📊 Vote Count:")
            for agent_id, count in sorted(vote_counts.items(), key=lambda item: item[1], reverse=True):
                prefix = "🏆 " if agent_id == winner else "   "
                tie_note = " (tie-broken)" if is_tie and agent_id == winner else ""
                lines.append(f"{prefix}{agent_id}: {count} vote{'s' if count != 1 else ''}{tie_note}")

        voter_details = vote_results.get("voter_details", {})
        if voter_details:
            lines.append("\n🔍 Rationale:")
            for voted_for, voters in voter_details.items():
                lines.append(f"→ {voted_for}")
                for detail in voters:
                    reason = detail.get("reason", "").strip()
                    voter = detail.get("voter", "unknown")
                    lines.append(f'   • {voter}: "{reason}"')

        total_votes = vote_results.get("total_votes", 0)
        agents_voted = vote_results.get("agents_voted", 0)
        lines.append(f"\n📈 Participation: {agents_voted}/{total_votes} agents voted")
        if is_tie:
            lines.append("⚖️  Tie broken by coordinator ordering")

        mapping = vote_results.get("agent_mapping", {})
        if mapping:
            lines.append("\n🔀 Agent Mapping:")
            for anon_id, real_id in mapping.items():
                lines.append(f"   {anon_id} → {real_id}")

        return "\n".join(lines)

    def _format_coordination_table(self, builder: Any) -> str:
        """Compose summary metadata plus plain-text table for Textual modal."""
        table_text = builder.generate_event_table()
        metadata = builder.session_metadata if hasattr(builder, "session_metadata") else {}
        lines = ["📋 Coordination Session", "=" * 40]
        if metadata:
            question = metadata.get("user_prompt") or ""
            if question:
                lines.append(f"💡 Question: {question}")
            final_winner = metadata.get("final_winner")
            if final_winner:
                lines.append(f"🏆 Winner: {final_winner}")
            start = metadata.get("start_time")
            end = metadata.get("end_time")
            if start and end:
                lines.append(f"⏱️  Duration: {start} → {end}")
        lines.append("\n" + table_text)
        lines.append("\nTip: Use the mouse wheel or drag the scrollbar to explore this view.")
        return "\n".join(lines)

    def _persist_final_presentation(self, content: str, selected_agent: Optional[str], vote_results: Optional[Dict[str, Any]]):
        """Persist final presentation to files with latest pointer."""
        header = ["=== FINAL PRESENTATION ==="]
        if selected_agent:
            header.append(f"Selected Agent: {selected_agent}")
        if vote_results:
            header.append(f"Vote Results: {vote_results}")
        header.append("")  # blank line
        final_text = "\n".join(header) + f"{content}\n"

        targets: List[Path] = []
        if selected_agent:
            agent_file = self.output_dir / f"final_presentation_{selected_agent}.txt"
            self.final_presentation_file = agent_file  # Keep selector/modals pointing at the agent-scoped file
            self.final_presentation_latest = self.output_dir / f"final_presentation_{selected_agent}_latest.txt"
            targets.append(agent_file)
        else:
            if self.final_presentation_file is None:
                self.final_presentation_file = self.output_dir / "final_presentation.txt"
            if self.final_presentation_latest is None:
                self.final_presentation_latest = self.output_dir / "final_presentation_latest.txt"
            targets.append(self.final_presentation_file)

        for path in targets:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(final_text)
            except OSError as exc:
                logger.error(f"Failed to persist final presentation to {path}: {exc}")

        # Maintain a "latest" pointer for quick reopen
        if self.final_presentation_latest:
            try:
                if self.final_presentation_latest.exists() or self.final_presentation_latest.is_symlink():
                    self.final_presentation_latest.unlink()
                self.final_presentation_latest.symlink_to(targets[-1].name)
            except (OSError, NotImplementedError) as exc:
                logger.warning(f"Failed to create final presentation symlink at {self.final_presentation_latest}: {exc}")


# Textual App Implementation
if TEXTUAL_AVAILABLE:
    from textual.binding import Binding
    from textual.css.query import NoMatches
    from textual.widgets import Button, ListItem, ListView

    class TextualApp(App):
        """Main Textual application for MassGen coordination."""

        THEMES_DIR = Path(__file__).parent / "textual_themes"
        CSS_PATH = str(THEMES_DIR / "dark.tcss")

        BINDINGS = [
            Binding("tab", "next_agent", "Next Agent"),
            Binding("shift+tab", "prev_agent", "Prev Agent"),
            Binding("s", "open_system_status", "System Log"),
            Binding("o", "open_orchestrator", "Events"),
            Binding("i", "agent_selector", "Agent Selector"),
            Binding("c", "coordination_table", "Coordination Table"),
            Binding("v", "open_vote_results", "Vote Results"),
            Binding("ctrl+k", "toggle_safe_keyboard", "Safe Keys"),
            Binding("q", "quit", "Quit"),
        ]

        def __init__(
            self,
            display: TextualTerminalDisplay,
            question: str,
            buffers: Dict[str, List],
            buffer_lock: threading.Lock,
            buffer_flush_interval: float,
        ):
            css_path = self.THEMES_DIR / ("light.tcss" if display.theme == "light" else "dark.tcss")
            super().__init__(css_path=str(css_path))
            self.coordination_display = display
            self.question = question
            self._buffers = buffers
            self._buffer_lock = buffer_lock
            self.buffer_flush_interval = buffer_flush_interval
            self._keyboard_interactive_mode = display._keyboard_interactive_mode

            # Widget references
            self.agent_widgets = {}
            self.header_widget = None
            self.footer_widget = None
            self.post_eval_panel = None
            self.final_stream_panel = None
            self.safe_indicator = None

            # State
            self.current_agent_index = 0
            self._pending_flush = False
            self._resize_debounce_handle = None
            self._thread_id: Optional[int] = None
            # Orchestrator event tracking
            self._orchestrator_events: List[str] = []

            if not self._keyboard_interactive_mode:
                self.BINDINGS = []

        def _keyboard_locked(self) -> bool:
            """Return True when keyboard input should be ignored (startup flag or runtime safe mode)."""
            return self.coordination_display.safe_keyboard_mode or not self._keyboard_interactive_mode

        def compose(self) -> ComposeResult:
            """Compose the UI layout with adaptive agent arrangement."""
            num_agents = len(self.coordination_display.agent_ids)
            # Header
            self.header_widget = HeaderWidget(self.question)
            yield self.header_widget

            # Main container with adaptive agent layout
            layout_class = self._get_layout_class(num_agents)
            with Container(id="main_container", classes=layout_class):
                # Agent columns with adaptive layout
                with Container(id="agents_container", classes=layout_class):
                    for idx, agent_id in enumerate(self.coordination_display.agent_ids):
                        agent_widget = AgentPanel(agent_id, self.coordination_display, idx + 1)
                        self.agent_widgets[agent_id] = agent_widget
                        yield agent_widget

            # Post-evaluation panel (hidden until content arrives)
            self.post_eval_panel = PostEvaluationPanel()
            yield self.post_eval_panel

            # Final presentation streaming panel
            self.final_stream_panel = FinalStreamPanel()
            yield self.final_stream_panel

            # Safe mode indicator
            self.safe_indicator = Label("", id="safe_indicator")
            yield self.safe_indicator

            # Footer
            self.footer_widget = Footer()
            yield self.footer_widget

        def _get_layout_class(self, num_agents: int) -> str:
            """Return CSS class for adaptive layout based on agent count."""
            if num_agents == 1:
                return "single-agent"
            elif num_agents == 2:
                return "two-agents"
            elif num_agents == 3:
                return "three-agents"
            else:
                return "many-agents"

        async def on_mount(self):
            """Set up periodic buffer flushing when app starts."""
            # Record the app's thread id so synchronous calls can short-circuit call_from_thread
            self._thread_id = threading.get_ident()
            # Set up periodic buffer flushing
            self.set_interval(self.buffer_flush_interval, self._flush_buffers)
            # Render restart context if present
            if self.coordination_display.restart_reason and self.header_widget:
                self.header_widget.show_restart_context(
                    self.coordination_display.restart_reason,
                    self.coordination_display.restart_instructions or "",
                )
            # Render safe indicator if starting in safe mode or bindings disabled
            self._update_safe_indicator()

        def _update_safe_indicator(self):
            """Show/hide safe keyboard status in footer area."""
            if not self.safe_indicator:
                return
            if self.coordination_display.safe_keyboard_mode:
                self.safe_indicator.update("🔒 Safe keys: ON")
                self.safe_indicator.styles.display = "block"
            elif not self._keyboard_interactive_mode:
                self.safe_indicator.update("⌨ Keyboard input disabled")
                self.safe_indicator.styles.display = "block"
            else:
                self.safe_indicator.update("")
                self.safe_indicator.styles.display = "none"

        async def _flush_buffers(self):
            """Flush buffered content to widgets (runs in asyncio event loop)."""
            self._pending_flush = False
            # Collect all updates first, then apply in batch to reduce redraws
            all_updates = []
            for agent_id in self.coordination_display.agent_ids:
                with self._buffer_lock:
                    if not self._buffers[agent_id]:
                        continue
                    buffer_copy = self._buffers[agent_id].copy()
                    self._buffers[agent_id].clear()

                if buffer_copy and agent_id in self.agent_widgets:
                    all_updates.append((agent_id, buffer_copy))

            # Apply all updates with refresh suppressed until done
            if all_updates:
                with self.batch_update():
                    for agent_id, buffer_copy in all_updates:
                        for item in buffer_copy:
                            await self.update_agent_widget(
                                agent_id,
                                item["content"],
                                item.get("type", "thinking"),
                            )
                            # Scroll to latest if status jump requested
                            if item.get("force_jump"):
                                widget = self.agent_widgets.get(agent_id)
                                if widget:
                                    widget.jump_to_latest()

        def request_flush(self):
            """Request a near-immediate flush (debounced)."""
            if self._pending_flush:
                return
            self._pending_flush = True
            try:
                if threading.get_ident() == getattr(self, "_thread_id", None):
                    self.call_later(self._flush_buffers)
                else:
                    self.call_from_thread(self._flush_buffers)
            except Exception:
                self._pending_flush = False

        async def update_agent_widget(self, agent_id: str, content: str, content_type: str):
            """Update agent widget with content."""
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].add_content(content, content_type)

        def update_agent_status(self, agent_id: str, status: str):
            """Update agent status."""
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].update_status(status)
                self.agent_widgets[agent_id].jump_to_latest()

        def add_orchestrator_event(self, event: str):
            """Add orchestrator event to internal tracking."""
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._orchestrator_events.append(f"{timestamp} {event}")

        def show_final_presentation(
            self,
            answer: str,
            vote_results=None,
            selected_agent=None,
        ):
            """Display final answer modal with flush effect."""
            if self.final_stream_panel:
                agent_label = selected_agent or "Unknown"
                self.final_stream_panel.begin(agent_label, vote_results or {})
                if answer:
                    self.final_stream_panel.append_chunk(answer)
                self.final_stream_panel.end()

        def show_post_evaluation(self, content: str, agent_id: str):
            """Show post-evaluation content."""
            if self.post_eval_panel:
                lines = list(self.coordination_display._post_evaluation_lines)
                self.post_eval_panel.update_lines(agent_id, lines)
            self.add_orchestrator_event(f"[POST-EVALUATION] {agent_id}: {content}")
            if self.final_stream_panel:
                self.final_stream_panel.end()

        def begin_final_stream(self, agent_id: str, vote_results: Dict[str, Any]):
            """Show streaming panel when the final agent starts presenting."""
            if self.final_stream_panel:
                self.final_stream_panel.begin(agent_id, vote_results)

        def update_final_stream(self, chunk: str):
            """Append streaming chunks to the panel."""
            if self.final_stream_panel:
                self.final_stream_panel.append_chunk(chunk)

        def end_final_stream(self):
            """Hide streaming panel after presentation ends."""
            if self.final_stream_panel:
                self.final_stream_panel.end()
            if self.post_eval_panel and not self.coordination_display._post_evaluation_lines:
                self.post_eval_panel.hide()

        def show_restart_banner(
            self,
            reason: str,
            instructions: str,
            attempt: int,
            max_attempts: int,
        ):
            """Show restart banner."""
            if self.header_widget:
                self.header_widget.show_restart_banner(
                    reason,
                    instructions,
                    attempt,
                    max_attempts,
                )

        def show_restart_context(self, reason: str, instructions: str):
            """Show restart context."""
            if self.header_widget:
                self.header_widget.show_restart_context(reason, instructions)

        def display_vote_results(self, formatted_results: str):
            """Display vote results."""
            self.add_orchestrator_event("🗳️ Voting complete. Press 'v' to inspect details.")
            self._latest_vote_results_text = formatted_results

            async def _show_modal():
                modal = VoteResultsModal(formatted_results)
                await self.push_screen(modal)

            self.call_later(lambda: self.run_worker(_show_modal()))

        def display_coordination_table(self, table_text: str):
            """Display coordination table."""

            async def _show_modal():
                modal = CoordinationTableModal(table_text)
                await self.push_screen(modal)

            self.call_later(lambda: self.run_worker(_show_modal()))

        def show_agent_selector(self):
            """Show agent selector modal."""
            modal = AgentSelectorModal(
                self.coordination_display.agent_ids,
                self.coordination_display,
                self,
            )
            self.push_screen(modal)

        def action_next_agent(self):
            """Move focus to next agent."""
            if self._keyboard_locked():
                return
            self.current_agent_index = (self.current_agent_index + 1) % len(self.coordination_display.agent_ids)
            agent_id = self.coordination_display.agent_ids[self.current_agent_index]
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].focus()

        def action_prev_agent(self):
            """Move focus to previous agent."""
            if self._keyboard_locked():
                return
            self.current_agent_index = (self.current_agent_index - 1) % len(self.coordination_display.agent_ids)
            agent_id = self.coordination_display.agent_ids[self.current_agent_index]
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].focus()

        def action_toggle_safe_keyboard(self):
            """Toggle safe keyboard mode to ignore hotkeys."""
            self.coordination_display.safe_keyboard_mode = not self.coordination_display.safe_keyboard_mode
            status = "ON" if self.coordination_display.safe_keyboard_mode else "OFF"
            self.add_orchestrator_event(f"Keyboard safe mode {status}")
            self._update_safe_indicator()

        def action_agent_selector(self):
            """Show agent selector."""
            if self._keyboard_locked():
                return
            self.show_agent_selector()

        def action_coordination_table(self):
            """Show coordination table."""
            if self._keyboard_locked():
                return
            self._show_coordination_table_modal()

        def action_quit(self):
            """Quit the application."""
            if self._keyboard_locked():
                return
            self.exit()

        def action_open_vote_results(self):
            """Open vote results modal."""
            if self._keyboard_locked():
                return
            # If we already have a formatted vote panel, reuse it; otherwise fall back
            text = getattr(self, "_latest_vote_results_text", "")
            if not text:
                status = getattr(self.coordination_display, "_final_answer_metadata", {}) or {}
                text = self.coordination_display._format_vote_results(status.get("vote_results", {})) if hasattr(self.coordination_display, "_format_vote_results") else ""
            if not text.strip():
                text = "Vote results unavailable."

            async def _show_modal():
                modal = VoteResultsModal(text)
                await self.push_screen(modal)

            self.call_later(lambda: self.run_worker(_show_modal()))

        def action_open_system_status(self):
            """Open system status log."""
            if self._keyboard_locked():
                return
            self._show_system_status_modal()

        def action_open_orchestrator(self):
            """Open orchestrator events modal."""
            if self._keyboard_locked():
                return
            self._show_orchestrator_modal()

        def _show_orchestrator_modal(self):
            """Display orchestrator events in a modal."""
            events_text = "\n".join(self._orchestrator_events) if self._orchestrator_events else "No events yet."

            async def _show_modal():
                modal = OrchestratorEventsModal(events_text)
                await self.push_screen(modal)

            self.call_later(lambda: self.run_worker(_show_modal()))

        def on_key(self, event: events.Key):
            """Map number keys directly to agent inspection, mirroring Rich UI."""
            if self._keyboard_locked():
                return

            key = event.character
            if not key:
                return

            if key.isdigit() and key != "0":
                idx = int(key) - 1
                if 0 <= idx < len(self.coordination_display.agent_ids):
                    agent_id = self.coordination_display.agent_ids[idx]
                    self.current_agent_index = idx
                    if agent_id in self.agent_widgets:
                        self.agent_widgets[agent_id].focus()
                        event.stop()
                    return

            if key.lower() == "s":
                self.action_open_system_status()
                event.stop()
                return

            if key.lower() == "o":
                self.action_open_orchestrator()
                event.stop()
                return

        def _show_coordination_table_modal(self):
            """Display coordination table in a modal."""
            table_text = self.coordination_display._format_coordination_table_from_orchestrator()

            async def _show_modal():
                modal = CoordinationTableModal(table_text)
                await self.push_screen(modal)

            self.call_later(lambda: self.run_worker(_show_modal()))

        def _show_text_modal(self, path: Path, title: str):
            """Display file content in a modal."""
            content = ""
            try:
                if path.exists():
                    content = path.read_text(encoding="utf-8")
            except Exception:
                content = ""
            if not content:
                content = "Content unavailable."

            async def _show_modal():
                modal = TextContentModal(title, content)
                await self.push_screen(modal)

            self.call_later(lambda: self.run_worker(_show_modal()))

        def _show_system_status_modal(self):
            """Display system status log in a modal instead of opening editor."""
            content = ""
            status_path = self.coordination_display.system_status_file
            if status_path and Path(status_path).exists():
                try:
                    content = Path(status_path).read_text(encoding="utf-8")
                except Exception:
                    content = ""
            if not content:
                content = "System status log is empty or unavailable."

            async def _show_modal():
                modal = SystemStatusModal(content)
                await self.push_screen(modal)

            self.call_later(lambda: self.run_worker(_show_modal()))

        def on_resize(self, event: events.Resize) -> None:
            """Refresh widgets when the terminal window is resized with debounce."""
            if self._resize_debounce_handle:
                try:
                    self._resize_debounce_handle.cancel()
                except Exception:
                    pass

            # Use longer debounce on Windows/VSCode to reduce flicker on resize
            debounce_time = 0.15 if self.coordination_display._terminal_type in ("vscode", "windows_terminal") else 0.05
            try:
                self._resize_debounce_handle = self.set_timer(debounce_time, lambda: self.refresh(layout=True))
            except Exception:
                self.call_later(lambda: self.refresh(layout=True))

    # Widget implementations
    class HeaderWidget(Static):
        """Header widget showing question and restart context."""

        def __init__(self, question: str):
            super().__init__()
            self.question = question
            self.restart_banner = None

        def compose(self) -> ComposeResult:
            yield Label(f"💡 Question: {self.question}", id="question_label")

        def show_restart_banner(
            self,
            reason: str,
            instructions: str,
            attempt: int,
            max_attempts: int,
        ):
            """Show restart banner."""
            banner_text = f"⚠️ RESTART (Attempt {attempt}/{max_attempts}): {reason}"
            try:
                banner_label = self.query_one("#restart_banner")
                banner_label.update(banner_text)
            except NoMatches:
                # Create banner if it doesn't exist
                banner = Label(banner_text, id="restart_banner")
                self.mount(banner, before=0)

        def show_restart_context(self, reason: str, instructions: str):
            """Show restart context."""
            context_text = f"📋 Previous attempt: {reason}"
            try:
                context_label = self.query_one("#restart_context")
                context_label.update(context_text)
            except NoMatches:
                # Create context if it doesn't exist
                context = Label(context_text, id="restart_context")
                self.mount(context)

    class AgentPanel(ScrollableContainer):
        """Panel for individual agent output."""

        def __init__(self, agent_id: str, display: TextualTerminalDisplay, key_index: int = 0):
            self.agent_id = agent_id
            self.coordination_display = display
            self.key_index = key_index
            self._dom_safe_id = self._make_dom_safe_id(agent_id)
            super().__init__(id=f"agent_{self._dom_safe_id}")
            self.status = "waiting"
            self._start_time: Optional[datetime] = None
            self.content_log = RichLog(
                id=f"log_{self._dom_safe_id}",
                highlight=self.coordination_display.enable_syntax_highlighting,
                markup=True,
                wrap=True,
            )
            self._line_buffer = ""
            self.current_line_label = Label("", classes="streaming_label")
            self._header_dom_id = f"header_{self._dom_safe_id}"

        def compose(self) -> ComposeResult:
            with Vertical():
                # Agent header with status
                yield Label(
                    self._header_text(),
                    id=self._header_dom_id,
                )
                # Content area
                yield self.content_log
                # Streaming line indicator
                yield self.current_line_label

        def add_content(self, content: str, content_type: str):
            """Add content to agent panel."""
            # Apply formatting based on content type using Text to avoid markup parsing
            if content_type == "tool":
                self.content_log.write(Text(f"🔧 {content}", style="cyan"))
                self._line_buffer = ""
                self.current_line_label.update(Text(""))
            elif content_type == "status":
                self.content_log.write(Text(f"📊 {content}", style="yellow"))
                self._line_buffer = ""
                self.current_line_label.update(Text(""))
            elif content_type == "presentation":
                self.content_log.write(Text(f"🎤 {content}", style="magenta"))
                self._line_buffer = ""
                self.current_line_label.update(Text(""))
            else:
                # Handle thinking content with buffering
                self._line_buffer += content
                if "\n" in self._line_buffer:
                    lines = self._line_buffer.split("\n")
                    # Write all complete lines
                    for line in lines[:-1]:
                        if line.strip():
                            self.content_log.write(Text(line))
                    # Keep the last partial line in buffer
                    self._line_buffer = lines[-1]

                # Update the streaming label with current partial line
                self.current_line_label.update(Text(self._line_buffer))

        def update_status(self, status: str):
            """Update agent status."""
            # Flush any remaining buffer when status changes
            if self._line_buffer.strip():
                self.content_log.write(Text(self._line_buffer))
                self._line_buffer = ""
                self.current_line_label.update(Text(""))

            if status == "working" and self.status != "working":
                self._start_time = datetime.now()
            elif status in ("completed", "error", "waiting"):
                self._start_time = None

            self.status = status
            self.remove_class("status-waiting", "status-working", "status-streaming", "status-completed", "status-error")
            self.add_class(f"status-{status}")

            header = self.query_one(f"#{self._header_dom_id}")
            header.update(self._header_text())

        def jump_to_latest(self):
            """Scroll to latest entry if supported."""
            try:
                self.content_log.scroll_end(animate=False)
            except Exception:
                try:
                    self.content_log.scroll_end()
                except Exception:
                    pass

        def _header_text(self) -> str:
            """Compose header text with backend metadata, keyboard hint, and elapsed time."""
            backend = self.coordination_display._get_agent_backend_name(self.agent_id)
            status_icon = self._status_icon(self.status)

            parts = [f"{status_icon} {self.agent_id}"]
            if backend and backend != "Unknown":
                parts.append(f"({backend})")
            if self.key_index and 1 <= self.key_index <= 9:
                parts.append(f"[{self.key_index}]")
            if self._start_time and self.status in ("working", "streaming"):
                elapsed = datetime.now() - self._start_time
                elapsed_str = self._format_elapsed(elapsed.total_seconds())
                parts.append(f"⏱{elapsed_str}")
            parts.append(f"[{self.status}]")

            return " ".join(parts)

        def _format_elapsed(self, seconds: float) -> str:
            """Format elapsed seconds into human-readable string."""
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                mins = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{mins}m{secs}s"
            else:
                hours = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                return f"{hours}h{mins}m"

        def _status_icon(self, status: str) -> str:
            """Return emoji (or fallback) for the given status."""
            icon_map = {
                "waiting": "⏳",
                "working": "🔄",
                "streaming": "📝",
                "completed": "✅",
                "error": "❌",
            }
            return self.coordination_display._get_icon(icon_map.get(status, "🤖"))

        def _make_dom_safe_id(self, raw_id: str) -> str:
            """Convert arbitrary agent IDs into Textual-safe DOM identifiers."""
            MAX_DOM_ID_LENGTH = 80

            # Truncate if too long
            truncated = raw_id[:MAX_DOM_ID_LENGTH] if len(raw_id) > MAX_DOM_ID_LENGTH else raw_id

            # Apply regex substitution
            safe = re.sub(r"[^0-9a-zA-Z_-]", "_", truncated)

            # Handle empty result
            if not safe:
                safe = "agent_default"

            # Handle digit-first
            if safe[0].isdigit():
                safe = f"agent_{safe}"

            # Collision-safe: append __N suffix if needed
            base_safe = safe
            counter = 1
            used_ids = set(self.coordination_display._dom_id_mapping.values())

            while safe in used_ids:
                suffix = f"__{counter}"
                # Ensure total length doesn't exceed MAX_DOM_ID_LENGTH
                max_base_len = MAX_DOM_ID_LENGTH - len(suffix)
                safe = base_safe[:max_base_len] + suffix
                counter += 1

            # Log collision resolution for debugging
            if safe != base_safe:
                logger.debug(
                    f"DOM ID collision resolved for agent '{raw_id}': " f"'{base_safe}' -> '{safe}' (suffix added to avoid duplicate)",
                )

            # Store mapping for debugging and future collision checks
            self.coordination_display._dom_id_mapping[raw_id] = safe

            return safe

    class OrchestratorEventsModal(ModalScreen):
        """Modal to display orchestrator events."""

        def __init__(self, events_text: str):
            super().__init__()
            self.events_text = events_text

        def compose(self) -> ComposeResult:
            with Container(id="orchestrator_modal_container"):
                yield Label("📋 Orchestrator Events", id="orchestrator_modal_header")
                yield Label("Press 'o' anytime to view events", id="orchestrator_hint")
                yield TextArea(self.events_text, id="orchestrator_events_content", read_only=True)
                yield Button("Close (ESC)", id="close_orchestrator_button")

        def on_button_pressed(self, event: Button.Pressed):
            if event.button.id == "close_orchestrator_button":
                self.dismiss()

        def on_key(self, event: events.Key):
            if event.key == "escape":
                self.dismiss()
                event.stop()

    class AgentSelectorModal(ModalScreen):
        """Interactive agent selection menu."""

        def __init__(self, agent_ids: List[str], display: TextualTerminalDisplay, app: "TextualApp"):
            super().__init__()
            self.agent_ids = agent_ids
            self.coordination_display = display
            self.app_ref = app

        def compose(self) -> ComposeResult:
            with Container(id="selector_container"):
                yield Label("Select an agent to view:", id="selector_header")

                items = [ListItem(Label(f"📄 View {agent_id}")) for agent_id in self.agent_ids]
                items.append(ListItem(Label("🎤 View Final Presentation Transcript")))
                items.append(ListItem(Label("📊 View System Status")))
                items.append(ListItem(Label("📋 View Coordination Table")))

                yield ListView(*items, id="agent_list")
                yield Button("Cancel (ESC)", id="cancel_button")

        def on_list_view_selected(self, event: ListView.Selected):
            """Handle selection from list."""
            index = event.list_view.index
            if index < len(self.agent_ids):
                agent_id = self.agent_ids[index]
                path = self.coordination_display.agent_files.get(agent_id)
                if path:
                    self.app_ref._show_text_modal(Path(path), f"{agent_id} Output")
            elif index == len(self.agent_ids):
                # Final presentation
                path = self.coordination_display.final_presentation_file
                if path:
                    self.app_ref._show_text_modal(Path(path), "Final Presentation")
            elif index == len(self.agent_ids) + 1:
                # View system status
                self.app_ref._show_system_status_modal()
            elif index == len(self.agent_ids) + 2:
                # View coordination table
                self.app_ref._show_coordination_table_modal()

            self.dismiss()

        def on_button_pressed(self, event: Button.Pressed):
            """Handle button press."""
            if event.button.id == "cancel_button":
                self.dismiss()

    class CoordinationTableModal(ModalScreen):
        """Modal to display coordination table."""

        def __init__(self, table_content: str):
            super().__init__()
            self.table_content = table_content

        def compose(self) -> ComposeResult:
            with Container(id="table_container"):
                yield Label("📋 Coordination Table", id="table_header")
                yield Label("Use the mouse wheel or scrollbar to navigate", id="table_hint")
                yield TextArea(
                    self.table_content,
                    id="table_content",
                    read_only=True,
                )
                yield Button("Close (ESC)", id="close_button")

        def on_button_pressed(self, event: Button.Pressed):
            """Handle button press."""
            if event.button.id == "close_button":
                self.dismiss()

    class VoteResultsModal(ModalScreen):
        """Modal for detailed vote results."""

        def __init__(self, results_text: str):
            super().__init__()
            self.results_text = results_text

        def compose(self) -> ComposeResult:
            with Container(id="vote_results_container"):
                yield Label("🗳️ Voting Breakdown", id="vote_header")
                yield TextArea(self.results_text, id="vote_results", read_only=True)
                yield Button("Close (ESC)", id="close_vote_button")

        def on_button_pressed(self, event: Button.Pressed):
            if event.button.id == "close_vote_button":
                self.dismiss()

    class SystemStatusModal(ModalScreen):
        """Modal to display system status log."""

        def __init__(self, content: str):
            super().__init__()
            self.content = content

        def compose(self) -> ComposeResult:
            with Container(id="system_status_container"):
                yield Label("📋 System Status Log", id="system_status_header")
                yield TextArea(self.content, id="system_status_content", read_only=True)
                yield Button("Close (ESC)", id="close_system_status_button")

        def on_button_pressed(self, event: Button.Pressed):
            if event.button.id == "close_system_status_button":
                self.dismiss()

    class TextContentModal(ModalScreen):
        """Generic modal to display text content from a file or buffer."""

        def __init__(self, title: str, content: str):
            super().__init__()
            self.title = title
            self.content = content

        def compose(self) -> ComposeResult:
            with Container(id="text_content_container"):
                yield Label(self.title, id="text_content_header")
                yield TextArea(self.content, id="text_content_body", read_only=True)
                yield Button("Close (ESC)", id="close_text_content_button")

        def on_button_pressed(self, event: Button.Pressed):
            if event.button.id == "close_text_content_button":
                self.dismiss()

    class PostEvaluationPanel(Static):
        """Displays the most recent post-evaluation snippets."""

        def __init__(self):
            super().__init__(id="post_eval_container")
            self.agent_label = Label("", id="post_eval_label")
            self.log_view = RichLog(id="post_eval_log", highlight=True, markup=True, wrap=True)
            self.styles.display = "none"

        def compose(self) -> ComposeResult:
            yield self.agent_label
            yield self.log_view

        def update_lines(self, agent_id: str, lines: List[str]):
            """Show the last few post-evaluation lines."""
            self.styles.display = "block"
            self.agent_label.update(f"🔍 Post-Evaluation — {agent_id}")
            self.log_view.clear()
            if not lines:
                self.log_view.write("Evaluating answer...")
                return
            for entry in lines[-5:]:
                self.log_view.write(entry)

        def hide(self):
            """Hide the post-evaluation panel."""
            self.styles.display = "none"

    class FinalStreamPanel(Static):
        """Live view of the winning agent's presentation stream."""

        def __init__(self):
            super().__init__(id="final_stream_container")
            self.agent_label = Label("", id="final_stream_label")
            self.log_view = RichLog(id="final_stream_log", highlight=True, markup=True, wrap=True)
            self.current_line_label = Label("", classes="streaming_label")
            self._line_buffer = ""
            self._header_base = ""
            self._vote_summary = ""
            self._is_streaming = False
            self.styles.display = "none"

        def compose(self) -> ComposeResult:
            yield self.agent_label
            yield self.log_view
            yield self.current_line_label

        def begin(self, agent_id: str, vote_results: Dict[str, Any]):
            """Reset panel with agent metadata."""
            self.styles.display = "block"
            self._is_streaming = True
            self.add_class("streaming-active")
            self._header_base = f"🎤 Final Presentation — {agent_id}"
            self._vote_summary = self._format_vote_summary(vote_results or {})
            header = self._header_base
            if self._vote_summary:
                header = f"{header} | {self._vote_summary} | 🔴 LIVE"
            else:
                header = f"{header} | 🔴 LIVE"
            self.agent_label.update(header)
            self.log_view.clear()
            self._line_buffer = ""
            self.current_line_label.update("")

        def append_chunk(self, chunk: str):
            """Append streaming text with buffering."""
            if not chunk:
                return

            # Buffer content
            self._line_buffer += chunk

            if "\n" in self._line_buffer:
                lines = self._line_buffer.split("\n")
                # Write complete lines
                for line in lines[:-1]:
                    if line.strip():
                        self.log_view.write(line)
                # Keep partial line
                self._line_buffer = lines[-1]

            # Update streaming label
            self.current_line_label.update(self._line_buffer)

        def end(self):
            """Mark presentation as complete but keep visible."""
            # Flush remaining buffer
            if self._line_buffer.strip():
                self.log_view.write(self._line_buffer)
            self._line_buffer = ""
            self.current_line_label.update("")
            self._is_streaming = False
            self.remove_class("streaming-active")

            # Keep visible so user can read it with a strong completion marker
            header = self._header_base or str(self.agent_label.renderable)
            if self._vote_summary:
                header = f"{header} | {self._vote_summary}"
            self.agent_label.update(f"{header} | ✅ Completed")

        def _format_vote_summary(self, vote_results: Dict[str, Any]) -> str:
            """Condensed vote summary for header."""
            if not vote_results:
                return ""
            mapping = vote_results.get("vote_counts") or {}
            if not mapping:
                return ""
            # Prefer winner info if available
            winner = vote_results.get("winner")
            is_tie = vote_results.get("is_tie", False)
            summary_pairs = ", ".join(f"{aid}:{count}" for aid, count in mapping.items())
            if winner:
                tie_note = " (tie)" if is_tie else ""
                return f"Votes — {summary_pairs}; Winner: {winner}{tie_note}"
            return f"Votes — {summary_pairs}"


def is_textual_available() -> bool:
    """Check if Textual is available."""
    return TEXTUAL_AVAILABLE


def create_textual_display(agent_ids: List[str], **kwargs) -> Optional[TextualTerminalDisplay]:
    """Factory function to create Textual display if available."""
    if not TEXTUAL_AVAILABLE:
        return None
    return TextualTerminalDisplay(agent_ids, **kwargs)
