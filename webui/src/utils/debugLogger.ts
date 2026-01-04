/**
 * Debug Logger - sends logs to backend for file-based logging
 *
 * When a session is active, logs are written to webui_debug.log in the session's log_dir.
 * When no session is active, logs are written to webui_debug.log in the project root.
 *
 * Use this instead of console.log for debugging issues that are hard
 * to capture in the browser console.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogData {
  [key: string]: unknown;
}

class DebugLogger {
  // Disable by default in production - enable with debugLog.setEnabled(true)
  private enabled = import.meta.env.DEV;
  private queue: Array<{ level: LogLevel; message: string; data?: LogData; sessionId?: string }> = [];
  private flushTimeout: ReturnType<typeof setTimeout> | null = null;
  private sessionId: string | undefined;

  /**
   * Log a debug message
   */
  debug(message: string, data?: LogData) {
    this.log('debug', message, data);
  }

  /**
   * Log an info message
   */
  info(message: string, data?: LogData) {
    this.log('info', message, data);
  }

  /**
   * Log a warning message
   */
  warn(message: string, data?: LogData) {
    this.log('warn', message, data);
  }

  /**
   * Log an error message
   */
  error(message: string, data?: LogData) {
    this.log('error', message, data);
  }

  /**
   * Enable or disable logging
   */
  setEnabled(enabled: boolean) {
    this.enabled = enabled;
  }

  /**
   * Set the current session ID for routing logs to session log_dir
   */
  setSessionId(sessionId: string | undefined) {
    this.sessionId = sessionId;
  }

  private log(level: LogLevel, message: string, data?: LogData) {
    if (!this.enabled) return;

    // Also log to console for immediate visibility
    const consoleMethod = level === 'debug' ? 'log' : level;
    if (data) {
      console[consoleMethod](`[FileLog] ${message}`, data);
    } else {
      console[consoleMethod](`[FileLog] ${message}`);
    }

    // Queue for batch sending (include session ID for routing)
    this.queue.push({ level, message, data, sessionId: this.sessionId });
    this.scheduleFlush();
  }

  private scheduleFlush() {
    if (this.flushTimeout) return;

    // Batch logs and send every 100ms
    this.flushTimeout = setTimeout(() => {
      this.flush();
    }, 100);
  }

  private async flush() {
    this.flushTimeout = null;
    if (this.queue.length === 0) return;

    const logs = [...this.queue];
    this.queue = [];

    // Send each log (could batch further if needed)
    for (const log of logs) {
      try {
        await fetch('/api/debug/log', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(log),
        });
      } catch {
        // Silently fail - don't want logging to break the app
      }
    }
  }
}

// Singleton instance
export const debugLog = new DebugLogger();
