#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for AgentDrivenCompressor.

Tests the state machine logic for agent-driven context compression
without requiring external services.
"""

import tempfile
import time
from pathlib import Path

import pytest

from massgen.memory._compression import AgentDrivenCompressor


class TestAgentDrivenCompressorInit:
    """Test initialization of AgentDrivenCompressor."""

    def test_basic_initialization(self):
        """Test basic initialization with defaults."""
        compressor = AgentDrivenCompressor()

        assert compressor.state == AgentDrivenCompressor.STATE_IDLE
        assert compressor.current_attempt == 0
        assert compressor.max_attempts == 2
        assert compressor.pending_usage_info is None
        assert compressor.workspace_path is None

    def test_initialization_with_workspace(self):
        """Test initialization with workspace path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            compressor = AgentDrivenCompressor(workspace_path=Path(tmpdir))

            assert compressor.workspace_path == Path(tmpdir)
            assert compressor.state == AgentDrivenCompressor.STATE_IDLE

    def test_initialization_with_custom_max_attempts(self):
        """Test initialization with custom max attempts."""
        compressor = AgentDrivenCompressor(max_attempts=5)

        assert compressor.max_attempts == 5

    def test_initialization_with_custom_paths(self):
        """Test initialization with custom memory paths."""
        compressor = AgentDrivenCompressor(
            short_term_path="custom/short",
            long_term_path="custom/long",
        )

        assert compressor.short_term_path == "custom/short"
        assert compressor.long_term_path == "custom/long"


class TestShouldRequestCompression:
    """Test should_request_compression() method."""

    def test_returns_true_when_should_compress(self):
        """Test returns True when usage info indicates compression needed."""
        compressor = AgentDrivenCompressor()
        usage_info = {"should_compress": True}

        assert compressor.should_request_compression(usage_info) is True

    def test_returns_false_when_not_needed(self):
        """Test returns False when compression not needed."""
        compressor = AgentDrivenCompressor()
        usage_info = {"should_compress": False}

        assert compressor.should_request_compression(usage_info) is False

    def test_returns_false_when_not_idle(self):
        """Test returns False when not in idle state."""
        compressor = AgentDrivenCompressor()
        compressor.state = AgentDrivenCompressor.STATE_REQUESTING
        usage_info = {"should_compress": True}

        assert compressor.should_request_compression(usage_info) is False

    def test_returns_false_when_missing_key(self):
        """Test returns False when should_compress key missing."""
        compressor = AgentDrivenCompressor()
        usage_info = {}

        assert compressor.should_request_compression(usage_info) is False


class TestBuildCompressionRequest:
    """Test build_compression_request() method."""

    def test_builds_correct_message_structure(self):
        """Test that compression request has correct structure."""
        compressor = AgentDrivenCompressor()
        usage_info = {
            "usage_percent": 0.80,
            "current_tokens": 80000,
            "max_tokens": 100000,
        }

        message = compressor.build_compression_request(usage_info)

        assert message["role"] == "user"
        assert "_is_compression_request" in message
        assert message["_is_compression_request"] is True
        assert "content" in message
        assert "80%" in message["content"] or "80" in message["content"]

    def test_transitions_to_requesting_state(self):
        """Test that calling build_compression_request transitions state."""
        compressor = AgentDrivenCompressor()
        usage_info = {"usage_percent": 0.80, "current_tokens": 80000, "max_tokens": 100000}

        assert compressor.state == AgentDrivenCompressor.STATE_IDLE

        compressor.build_compression_request(usage_info)

        assert compressor.state == AgentDrivenCompressor.STATE_REQUESTING

    def test_increments_attempt_counter(self):
        """Test that build_compression_request increments attempt counter."""
        compressor = AgentDrivenCompressor()
        usage_info = {"usage_percent": 0.80, "current_tokens": 80000, "max_tokens": 100000}

        assert compressor.current_attempt == 0

        compressor.build_compression_request(usage_info)

        assert compressor.current_attempt == 1

    def test_stores_pending_usage_info(self):
        """Test that usage info is stored for later use."""
        compressor = AgentDrivenCompressor()
        usage_info = {"usage_percent": 0.80, "current_tokens": 80000, "max_tokens": 100000}

        compressor.build_compression_request(usage_info)

        assert compressor.pending_usage_info == usage_info

    def test_updates_total_attempts_stat(self):
        """Test that total_attempts stat is updated."""
        compressor = AgentDrivenCompressor()
        usage_info = {"usage_percent": 0.80, "current_tokens": 80000, "max_tokens": 100000}

        assert compressor.total_attempts == 0

        compressor.build_compression_request(usage_info)

        assert compressor.total_attempts == 1


class TestBuildRetryRequest:
    """Test build_retry_request() method."""

    def test_builds_retry_message(self):
        """Test that retry request is built correctly."""
        compressor = AgentDrivenCompressor()
        compressor.state = AgentDrivenCompressor.STATE_REQUESTING
        compressor.current_attempt = 1

        message = compressor.build_retry_request()

        assert message["role"] == "user"
        assert message["_is_compression_request"] is True
        assert "content" in message

    def test_increments_attempt_on_retry(self):
        """Test that retry increments attempt counter."""
        compressor = AgentDrivenCompressor()
        compressor.current_attempt = 1

        compressor.build_retry_request()

        assert compressor.current_attempt == 2


class TestValidateMemoryWritten:
    """Test validate_memory_written() method."""

    def test_returns_true_when_no_workspace(self):
        """Test returns True when no workspace configured (can't validate)."""
        compressor = AgentDrivenCompressor(workspace_path=None)

        success, files = compressor.validate_memory_written()

        assert success is True
        assert files == []

    def test_returns_false_when_file_missing(self):
        """Test returns False when recent.md is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            compressor = AgentDrivenCompressor(workspace_path=Path(tmpdir))

            success, files = compressor.validate_memory_written()

            assert success is False
            assert files == []

    def test_returns_true_when_recent_file_exists(self):
        """Test returns True when recent.md exists and is recent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace)

            # Create the short_term directory and recent.md file
            short_term_dir = workspace / "memory" / "short_term"
            short_term_dir.mkdir(parents=True)
            recent_file = short_term_dir / "recent.md"
            recent_file.write_text("# Recent Summary\n\nTest content")

            success, files = compressor.validate_memory_written()

            assert success is True
            assert str(recent_file) in files

    def test_ignores_old_files(self):
        """Test that old files (>60s) are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace)

            # Create an old file
            short_term_dir = workspace / "memory" / "short_term"
            short_term_dir.mkdir(parents=True)
            recent_file = short_term_dir / "recent.md"
            recent_file.write_text("Old content")

            # Make the file appear old
            import os

            old_time = time.time() - 120  # 2 minutes ago
            os.utime(recent_file, (old_time, old_time))

            success, files = compressor.validate_memory_written()

            # File exists but wasn't recently modified
            assert success is True  # File exists
            assert len(files) == 0  # But not in recently written list

    def test_detects_long_term_memories(self):
        """Test that newly written long-term memories are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace)

            # Create both short and long term files
            short_term_dir = workspace / "memory" / "short_term"
            short_term_dir.mkdir(parents=True)
            recent_file = short_term_dir / "recent.md"
            recent_file.write_text("# Recent")

            long_term_dir = workspace / "memory" / "long_term"
            long_term_dir.mkdir(parents=True)
            long_term_file = long_term_dir / "important_fact.md"
            long_term_file.write_text("# Important Fact")

            success, files = compressor.validate_memory_written()

            assert success is True
            assert len(files) == 2
            assert str(recent_file) in files
            assert str(long_term_file) in files


class TestOnCompressionCompleteToolCalled:
    """Test on_compression_complete_tool_called() method."""

    def test_returns_false_when_not_requesting(self):
        """Test returns False when called in wrong state."""
        compressor = AgentDrivenCompressor()
        assert compressor.state == AgentDrivenCompressor.STATE_IDLE

        result = compressor.on_compression_complete_tool_called()

        assert result is False

    def test_returns_true_and_resets_on_success(self):
        """Test returns True and resets state on validation success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace)

            # Set up state
            compressor.state = AgentDrivenCompressor.STATE_REQUESTING
            compressor.current_attempt = 1

            # Create the required file
            short_term_dir = workspace / "memory" / "short_term"
            short_term_dir.mkdir(parents=True)
            (short_term_dir / "recent.md").write_text("# Summary")

            result = compressor.on_compression_complete_tool_called()

            assert result is True
            assert compressor.state == AgentDrivenCompressor.STATE_IDLE
            assert compressor.current_attempt == 0
            assert compressor.total_agent_compressions == 1

    def test_stays_requesting_on_retry_needed(self):
        """Test stays in requesting state when retry is possible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace, max_attempts=3)

            # Set up state - first attempt
            compressor.state = AgentDrivenCompressor.STATE_REQUESTING
            compressor.current_attempt = 1
            # Don't create the file - validation will fail

            result = compressor.on_compression_complete_tool_called()

            assert result is False
            assert compressor.state == AgentDrivenCompressor.STATE_REQUESTING
            # Ready for retry

    def test_falls_back_after_max_attempts(self):
        """Test falls back to algorithmic compression after max attempts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace, max_attempts=2)

            # Set up state - already at max attempts
            compressor.state = AgentDrivenCompressor.STATE_REQUESTING
            compressor.current_attempt = 2
            # Don't create file

            result = compressor.on_compression_complete_tool_called()

            # Should return True to proceed with fallback
            assert result is True
            assert compressor.state == AgentDrivenCompressor.STATE_IDLE
            assert compressor.total_fallback_compressions == 1


class TestShouldUseFallback:
    """Test should_use_fallback() method."""

    def test_returns_false_before_max_attempts(self):
        """Test returns False when attempts remaining."""
        compressor = AgentDrivenCompressor(max_attempts=3)
        compressor.current_attempt = 1

        assert compressor.should_use_fallback() is False

    def test_returns_true_at_max_attempts(self):
        """Test returns True when at max attempts."""
        compressor = AgentDrivenCompressor(max_attempts=2)
        compressor.current_attempt = 2

        assert compressor.should_use_fallback() is True

    def test_returns_true_past_max_attempts(self):
        """Test returns True when past max attempts."""
        compressor = AgentDrivenCompressor(max_attempts=2)
        compressor.current_attempt = 5

        assert compressor.should_use_fallback() is True


class TestGetStats:
    """Test get_stats() method."""

    def test_returns_all_stats(self):
        """Test that get_stats returns all tracking information."""
        compressor = AgentDrivenCompressor()

        stats = compressor.get_stats()

        assert "total_agent_compressions" in stats
        assert "total_fallback_compressions" in stats
        assert "total_attempts" in stats
        assert "current_state" in stats
        assert "current_attempt" in stats

    def test_stats_reflect_operations(self):
        """Test that stats reflect actual operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace)

            # Simulate a successful compression
            usage_info = {"usage_percent": 0.80, "current_tokens": 80000, "max_tokens": 100000}
            compressor.build_compression_request(usage_info)

            # Create the required file
            short_term_dir = workspace / "memory" / "short_term"
            short_term_dir.mkdir(parents=True)
            (short_term_dir / "recent.md").write_text("# Summary")

            compressor.on_compression_complete_tool_called()

            stats = compressor.get_stats()
            assert stats["total_agent_compressions"] == 1
            assert stats["total_attempts"] == 1
            assert stats["current_state"] == "idle"


class TestResetState:
    """Test _reset_state() internal method."""

    def test_resets_all_state(self):
        """Test that reset clears all state."""
        compressor = AgentDrivenCompressor()
        compressor.state = AgentDrivenCompressor.STATE_VALIDATING
        compressor.current_attempt = 5
        compressor.pending_usage_info = {"test": "data"}

        compressor._reset_state()

        assert compressor.state == AgentDrivenCompressor.STATE_IDLE
        assert compressor.current_attempt == 0
        assert compressor.pending_usage_info is None


class TestStateTransitions:
    """Integration tests for state machine transitions."""

    def test_full_successful_flow(self):
        """Test complete successful compression flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace)

            # 1. Start in idle
            assert compressor.state == AgentDrivenCompressor.STATE_IDLE

            # 2. Check if compression needed
            usage_info = {
                "should_compress": True,
                "usage_percent": 0.80,
                "current_tokens": 80000,
                "max_tokens": 100000,
            }
            assert compressor.should_request_compression(usage_info) is True

            # 3. Build compression request
            message = compressor.build_compression_request(usage_info)
            assert compressor.state == AgentDrivenCompressor.STATE_REQUESTING
            assert message["role"] == "user"

            # 4. Agent writes memories
            short_term_dir = workspace / "memory" / "short_term"
            short_term_dir.mkdir(parents=True)
            (short_term_dir / "recent.md").write_text("# Summary\n\nConversation summary here")

            # 5. Agent calls compression_complete
            result = compressor.on_compression_complete_tool_called()

            # 6. Verify success
            assert result is True
            assert compressor.state == AgentDrivenCompressor.STATE_IDLE
            assert compressor.total_agent_compressions == 1

    def test_retry_then_success_flow(self):
        """Test flow where first attempt fails but retry succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace, max_attempts=3)

            # Start compression
            usage_info = {"should_compress": True, "usage_percent": 0.80, "current_tokens": 80000, "max_tokens": 100000}
            compressor.build_compression_request(usage_info)

            # First attempt - no file written
            result1 = compressor.on_compression_complete_tool_called()
            assert result1 is False
            assert compressor.state == AgentDrivenCompressor.STATE_REQUESTING

            # Build retry
            retry_msg = compressor.build_retry_request()
            assert "content" in retry_msg
            assert compressor.current_attempt == 2

            # Second attempt - write file
            short_term_dir = workspace / "memory" / "short_term"
            short_term_dir.mkdir(parents=True)
            (short_term_dir / "recent.md").write_text("# Summary")

            result2 = compressor.on_compression_complete_tool_called()
            assert result2 is True
            assert compressor.state == AgentDrivenCompressor.STATE_IDLE

    def test_fallback_flow(self):
        """Test flow where agent fails and fallback is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            compressor = AgentDrivenCompressor(workspace_path=workspace, max_attempts=2)

            # Start compression
            usage_info = {"should_compress": True, "usage_percent": 0.80, "current_tokens": 80000, "max_tokens": 100000}
            compressor.build_compression_request(usage_info)

            # First attempt - fail
            compressor.on_compression_complete_tool_called()

            # Retry
            compressor.build_retry_request()

            # Second attempt - still fail
            result = compressor.on_compression_complete_tool_called()

            # Should fall back
            assert result is True  # Proceed with fallback
            assert compressor.should_use_fallback() is False  # Already reset
            assert compressor.total_fallback_compressions == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
