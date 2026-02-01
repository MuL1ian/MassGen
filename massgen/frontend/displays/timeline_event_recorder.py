# -*- coding: utf-8 -*-
"""Timeline event recorder for events.jsonl parity debugging."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from massgen.events import MassGenEvent

from .content_processor import ContentOutput, ContentProcessor
from .timeline_transcript import render_output

logger = logging.getLogger(__name__)


class TimelineEventRecorder:
    """Record timeline transcript lines from MassGen events.

    Mirrors TimelineEventAdapter parsing so the resulting transcript lines
    match what the TUI would render.
    """

    def __init__(self, line_callback: Callable[[str], None]) -> None:
        self._processor = ContentProcessor()
        self._round_number = 1
        self._line_callback = line_callback

    def reset(self) -> None:
        """Reset internal state for a fresh event stream."""
        self._processor.reset()
        self._round_number = 1

    def handle_event(self, event: MassGenEvent) -> None:
        """Process a single event and emit any resulting transcript lines."""
        if event.event_type == "timeline_entry":
            return
        if event.event_type == "stream_chunk":
            # Legacy stream_chunk events from old log files — skip gracefully
            logger.debug("Skipping legacy stream_chunk event during replay")
            return

        output = self._processor.process_event(event, self._round_number)
        self._record_output(output)

    def flush(self) -> None:
        """Flush pending tool batches."""
        self._record_output(self._processor.flush_pending_batch(self._round_number))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_output(self, output: Optional[ContentOutput] | list[ContentOutput] | None) -> None:
        if output is None:
            return
        outputs = output if isinstance(output, list) else [output]
        for item in outputs:
            if item is None or item.output_type == "skip":
                continue
            if item.output_type == "separator" and item.round_number:
                self._round_number = item.round_number
            for line in render_output(item):
                self._line_callback(line)
