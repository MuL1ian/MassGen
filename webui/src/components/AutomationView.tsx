/**
 * AutomationView Component
 *
 * Wraps the existing TimelineView with a status header for automation mode.
 * Shows phase, elapsed time, question, and status.json path.
 * Also polls for active sessions and displays basic info while waiting.
 */

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Loader2, Clock, Users, FileText, Vote } from 'lucide-react';
import { TimelineView } from './timeline';
import { AnswerBrowserModal } from './AnswerBrowserModal';
import {
  useAgentStore,
  selectAgents,
  selectQuestion,
  selectLogDir,
  selectAgentOrder,
  selectIsComplete,
  selectSelectedAgent,
  selectAnswers,
} from '../stores/agentStore';

interface SessionInfo {
  session_id: string;
  is_running: boolean;
  has_display: boolean;
  question?: string;
  connections: number;
}

interface AutomationViewProps {
  onSessionChange?: (sessionId: string) => void;
  /** If true, don't auto-connect to other sessions (user explicitly requested a session) */
  sessionFromUrl?: boolean;
}

export function AutomationView({ onSessionChange, sessionFromUrl }: AutomationViewProps) {
  const agents = useAgentStore(selectAgents);
  const agentOrder = useAgentStore(selectAgentOrder);
  const question = useAgentStore(selectQuestion);
  const logDir = useAgentStore(selectLogDir);
  const isComplete = useAgentStore(selectIsComplete);
  const selectedAgent = useAgentStore(selectSelectedAgent);
  const sessionId = useAgentStore((s) => s.sessionId);
  const answers = useAgentStore(selectAnswers);

  // Answer browser modal state
  const [isAnswerBrowserOpen, setIsAnswerBrowserOpen] = useState(false);
  const [browserInitialTab, setBrowserInitialTab] = useState<'answers' | 'votes' | 'workspace' | 'timeline'>('answers');

  // Polling state for when no session is active
  const [pollingSessions, setPollingSessions] = useState<SessionInfo[]>([]);
  const [pollingError, setPollingError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Count answers and votes for display
  const answerCount = Object.keys(answers).length;
  const voteCount = Object.values(agents).filter(a => a.voteTarget).length;

  // Elapsed time counter - stops when coordination is complete
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    // Don't start/continue timer if already complete
    if (isComplete) return;

    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, [isComplete]);

  // Poll for active sessions when no agents are loaded
  const pollSessions = useCallback(async () => {
    try {
      const res = await fetch('/api/sessions');
      const data = await res.json();
      setPollingSessions(data.sessions || []);
      setPollingError(null);
    } catch (err) {
      setPollingError('Failed to fetch sessions');
    }
  }, []);

  // Start polling when no agents exist
  useEffect(() => {
    const hasAgents = agentOrder.length > 0;

    if (!hasAgents && !pollingIntervalRef.current) {
      // Start polling
      pollSessions();
      pollingIntervalRef.current = setInterval(pollSessions, 2000);
    } else if (hasAgents && pollingIntervalRef.current) {
      // Stop polling once we have agents
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [agentOrder.length, pollSessions]);

  // Find running sessions from polling
  const runningSessions = useMemo(() => {
    return pollingSessions.filter((s) => s.is_running || s.has_display);
  }, [pollingSessions]);

  // Auto-connect to running session when found
  const autoConnectedRef = useRef(false);
  useEffect(() => {
    // Only auto-connect once, when we have no agents and find a running session
    if (autoConnectedRef.current) return;
    if (sessionFromUrl) return; // Don't override explicit session from URL
    if (agentOrder.length > 0) return; // Already have session data
    if (runningSessions.length === 0) return; // No running sessions

    const targetSession = runningSessions[0];
    if (targetSession.session_id !== sessionId && onSessionChange) {
      console.log('[AutomationView] Auto-connecting to running session:', targetSession.session_id);
      autoConnectedRef.current = true;
      onSessionChange(targetSession.session_id);
    }
  }, [runningSessions, sessionId, agentOrder.length, onSessionChange, sessionFromUrl]);

  // Derive phase from agent statuses
  const phase = useMemo(() => {
    const statuses = Object.values(agents).map((a) => a.status);
    if (isComplete) return 'COMPLETE';
    if (statuses.some((s) => s === 'completed' && selectedAgent)) return 'PRESENTING';
    if (statuses.some((s) => s === 'voting')) return 'VOTING';
    if (statuses.some((s) => s === 'working')) return 'ANSWERING';
    // If we have no agents but have running sessions, show STARTING
    if (agentOrder.length === 0 && runningSessions.length > 0) return 'STARTING';
    return 'IDLE';
  }, [agents, isComplete, selectedAgent, agentOrder.length, runningSessions.length]);

  // Format elapsed time as MM:SS
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Phase color
  const phaseColor = useMemo(() => {
    switch (phase) {
      case 'STARTING':
        return 'text-purple-400';
      case 'ANSWERING':
        return 'text-blue-400';
      case 'VOTING':
        return 'text-amber-400';
      case 'PRESENTING':
        return 'text-yellow-400';
      case 'COMPLETE':
        return 'text-green-400';
      default:
        return 'text-gray-400';
    }
  }, [phase]);

  // Whether we have session data loaded
  const hasSessionData = agentOrder.length > 0 || question;

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Status Header */}
      <div className="border-b border-gray-700 px-6 py-4 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-4">
            <span className="px-2 py-1 bg-blue-600 text-white text-xs font-bold rounded uppercase tracking-wide">
              Automation
            </span>
            <span className={`text-sm font-medium ${phaseColor}`}>
              Phase: {phase}
            </span>
            <span className="text-gray-500 text-sm">
              {agentOrder.length} agents
            </span>
          </div>
          <div className="flex items-center gap-3">
            {/* Answer/Vote browser buttons */}
            {answerCount > 0 && (
              <button
                onClick={() => {
                  setBrowserInitialTab('answers');
                  setIsAnswerBrowserOpen(true);
                }}
                className="flex items-center gap-1.5 px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300"
              >
                <FileText className="w-3.5 h-3.5" />
                {answerCount} Answers
              </button>
            )}
            {voteCount > 0 && (
              <button
                onClick={() => {
                  setBrowserInitialTab('votes');
                  setIsAnswerBrowserOpen(true);
                }}
                className="flex items-center gap-1.5 px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300"
              >
                <Vote className="w-3.5 h-3.5" />
                {voteCount} Votes
              </button>
            )}
            <span className="text-gray-400 text-sm font-mono">
              Elapsed: {formatTime(elapsed)}
            </span>
          </div>
        </div>

        {/* Question - show from store or from running sessions */}
        {question ? (
          <div className="text-gray-300 text-sm mb-1 truncate" title={question}>
            {question}
          </div>
        ) : runningSessions.length > 0 && runningSessions[0].question ? (
          <div className="text-gray-300 text-sm mb-1 truncate" title={runningSessions[0].question}>
            {runningSessions[0].question}
          </div>
        ) : null}

        {/* Status.json path */}
        {logDir && (
          <div className="text-gray-500 text-xs font-mono truncate" title={`${logDir}/status.json`}>
            Status: {logDir}/status.json
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {hasSessionData ? (
          /* Timeline View when we have session data */
          <TimelineView />
        ) : (
          /* Waiting state when no session data */
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            {runningSessions.length > 0 ? (
              /* Coordination is running but not connected yet */
              <>
                <Loader2 className="w-12 h-12 mb-4 animate-spin text-purple-400" />
                <h2 className="text-xl font-semibold text-gray-200 mb-2">
                  Coordination Starting...
                </h2>
                <p className="text-gray-500 mb-4">
                  Waiting for agents to initialize
                </p>
                <div className="bg-gray-800 rounded-lg p-4 max-w-md">
                  <div className="flex items-center gap-3 text-sm">
                    <Users className="w-4 h-4 text-blue-400" />
                    <span className="text-gray-300">
                      {runningSessions.length} active session{runningSessions.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  {runningSessions[0]?.question && (
                    <div className="flex items-start gap-3 text-sm mt-2">
                      <FileText className="w-4 h-4 text-green-400 mt-0.5" />
                      <span className="text-gray-400 truncate">
                        {runningSessions[0].question}
                      </span>
                    </div>
                  )}
                </div>
              </>
            ) : (
              /* No sessions at all */
              <>
                <Clock className="w-12 h-12 mb-4 text-gray-600" />
                <h2 className="text-xl font-semibold text-gray-300 mb-2">
                  Waiting for Coordination
                </h2>
                <p className="text-gray-500 text-center max-w-md">
                  No active sessions detected.
                  {pollingError && (
                    <span className="block mt-2 text-amber-500 text-sm">
                      {pollingError}
                    </span>
                  )}
                </p>
                <div className="mt-4 text-xs text-gray-600">
                  Session ID: {sessionId?.slice(0, 8)}...
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Answer Browser Modal */}
      <AnswerBrowserModal
        isOpen={isAnswerBrowserOpen}
        onClose={() => setIsAnswerBrowserOpen(false)}
        initialTab={browserInitialTab}
      />
    </div>
  );
}
