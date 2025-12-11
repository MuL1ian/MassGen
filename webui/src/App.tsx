/**
 * MassGen Web UI - Main Application
 *
 * Real-time visualization of multi-agent coordination.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Wifi, WifiOff, AlertCircle, XCircle, ArrowLeft, Loader2, Trophy, X, FileCode } from 'lucide-react';
import { useWebSocket, ConnectionStatus } from './hooks/useWebSocket';
import { useAgentStore, selectQuestion, selectIsComplete, selectAnswers, selectViewMode, selectSelectedAgent, selectAgents, selectFinalAnswer, selectSelectingWinner, selectVoteDistribution, selectAutomationMode } from './stores/agentStore';
import { useThemeStore } from './stores/themeStore';
import { AgentCarousel } from './components/AgentCarousel';
import { AgentCard } from './components/AgentCard';
import { StatusToolbar } from './components/StatusToolbar';
import { ConvergenceAnimation } from './components/ConvergenceAnimation';
import { HeaderControls } from './components/HeaderControls';
import { AnswerBrowserModal } from './components/AnswerBrowserModal';
import { FinalAnswerView } from './components/FinalAnswerView';
import { QuickstartWizard } from './components/QuickstartWizard';
import { NotificationToast } from './components/NotificationToast';
import { KeyboardShortcutsModal } from './components/KeyboardShortcutsModal';
import { ConversationHistory } from './components/ConversationHistory';
import { AutomationView } from './components/AutomationView';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import type { Notification } from './stores/notificationStore';

function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const config: Record<ConnectionStatus, { icon: typeof Wifi; color: string; text: string }> = {
    connecting: { icon: Wifi, color: 'text-amber-500', text: 'Connecting...' },
    connected: { icon: Wifi, color: 'text-green-500', text: 'Connected' },
    disconnected: { icon: WifiOff, color: 'text-red-500', text: 'Disconnected' },
    error: { icon: AlertCircle, color: 'text-red-500', text: 'Error' },
  };

  const { icon: Icon, color, text } = config[status];

  return (
    <div className={`flex items-center gap-2 text-sm ${color}`}>
      <Icon className="w-4 h-4" />
      <span>{text}</span>
    </div>
  );
}

// Parse URL params once at module load (before any renders)
const initialUrlParams = new URLSearchParams(window.location.search);
const initialPrompt = initialUrlParams.get('prompt');
const initialConfig = initialUrlParams.get('config');
const initialSession = initialUrlParams.get('session');

export function App() {
  // Session management - use URL param if provided, otherwise generate random UUID
  const [sessionId, setSessionId] = useState<string>(() => initialSession || crypto.randomUUID());
  // Initialize from URL params synchronously to avoid race conditions
  const [selectedConfig, setSelectedConfig] = useState<string | null>(initialConfig);
  const [inputQuestion, setInputQuestion] = useState(initialPrompt || '');
  const [followUpQuestion, setFollowUpQuestion] = useState('');

  const question = useAgentStore(selectQuestion);
  const isComplete = useAgentStore(selectIsComplete);
  const answers = useAgentStore(selectAnswers);
  const viewMode = useAgentStore(selectViewMode);
  const selectedAgent = useAgentStore(selectSelectedAgent);
  const agents = useAgentStore(selectAgents);
  const finalAnswer = useAgentStore(selectFinalAnswer);
  const selectingWinner = useAgentStore(selectSelectingWinner);
  const voteDistribution = useAgentStore(selectVoteDistribution);
  const automationMode = useAgentStore(selectAutomationMode);
  const reset = useAgentStore((s) => s.reset);
  const backToCoordination = useAgentStore((s) => s.backToCoordination);
  const setViewMode = useAgentStore((s) => s.setViewMode);
  const startContinuation = useAgentStore((s) => s.startContinuation);
  const turnNumber = useAgentStore((s) => s.turnNumber);

  // Get winner agent for finalStreaming view
  const winnerAgent = selectedAgent ? agents[selectedAgent] : null;

  // Store scroll position when leaving coordination view
  const coordinationScrollRef = useRef<number>(0);

  // Theme - apply effective theme class to document
  const getEffectiveTheme = useThemeStore((s) => s.getEffectiveTheme);
  const themeMode = useThemeStore((s) => s.mode);

  useEffect(() => {
    const effectiveTheme = getEffectiveTheme();
    const root = document.documentElement;
    if (effectiveTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [getEffectiveTheme, themeMode]);

  // Track URL params from initial load (using module-level constants)
  const urlParamsRef = useRef<{ prompt: string | null; config: string | null; session: string | null } | null>(
    (initialPrompt || initialConfig || initialSession) ? { prompt: initialPrompt, config: initialConfig, session: initialSession } : null
  );
  const urlParamsProcessed = useRef(false);

  // Log URL params if present (for debugging)
  useEffect(() => {
    if (initialPrompt || initialConfig || initialSession) {
      console.log('[WebUI] URL params detected:', { prompt: initialPrompt, config: initialConfig, session: initialSession });
    }
  }, []); // Only run once on mount

  // Answer/Vote browser modal state
  const [isAnswerBrowserOpen, setIsAnswerBrowserOpen] = useState(false);
  const [browserInitialTab, setBrowserInitialTab] = useState<'answers' | 'votes' | 'workspace' | 'timeline'>('answers');

  // Keyboard shortcuts modal state
  const [isShortcutsModalOpen, setIsShortcutsModalOpen] = useState(false);

  // Config viewer modal state
  const [isConfigViewerOpen, setIsConfigViewerOpen] = useState(false);
  const [configContent, setConfigContent] = useState<string>('');
  const [configLoading, setConfigLoading] = useState(false);

  // Keyboard shortcuts hook
  const { shortcuts } = useKeyboardShortcuts({
    onOpenAnswerBrowser: useCallback(() => {
      setBrowserInitialTab('answers');
      setIsAnswerBrowserOpen(true);
    }, []),
    onOpenVoteBrowser: useCallback(() => {
      setBrowserInitialTab('votes');
      setIsAnswerBrowserOpen(true);
    }, []),
    onOpenWorkspaceBrowser: useCallback(() => {
      setBrowserInitialTab('workspace');
      setIsAnswerBrowserOpen(true);
    }, []),
    onOpenTimeline: useCallback(() => {
      setBrowserInitialTab('timeline');
      setIsAnswerBrowserOpen(true);
    }, []),
    onOpenShortcutsHelp: useCallback(() => {
      setIsShortcutsModalOpen(true);
    }, []),
    enabled: !isAnswerBrowserOpen && !isShortcutsModalOpen && !isConfigViewerOpen,
  });

  const { status, startCoordination, continueConversation, cancelCoordination, error } = useWebSocket({
    sessionId,
    autoConnect: true,
  });

  // Auto-connect to active running session (for automation mode)
  // This runs once on mount to find an existing coordination session
  // Skip if a session was explicitly specified via URL param
  const autoConnectAttempted = useRef(false);
  useEffect(() => {
    if (autoConnectAttempted.current) return;
    if (initialSession) {
      // User explicitly requested a specific session via URL
      console.log('[WebUI] Using session from URL param:', initialSession);
      autoConnectAttempted.current = true;
      return;
    }
    autoConnectAttempted.current = true;

    // Fetch sessions to see if there's an active one to connect to
    fetch('/api/sessions')
      .then(res => res.json())
      .then((data: { sessions: Array<{ session_id: string; is_running: boolean; has_display: boolean }> }) => {
        // Find an active running session with a display (the CLI coordination)
        const activeSession = data.sessions?.find(s => s.is_running && s.has_display);
        if (activeSession && activeSession.session_id !== sessionId) {
          console.log('[WebUI] Auto-connecting to active session:', activeSession.session_id);
          setSessionId(activeSession.session_id);
        }
      })
      .catch(err => {
        console.warn('[WebUI] Failed to fetch sessions for auto-connect:', err);
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-start coordination when connected and URL params are present
  useEffect(() => {
    if (urlParamsProcessed.current) return;
    if (!urlParamsRef.current) return;
    if (status !== 'connected') return;

    const { prompt, config } = urlParamsRef.current;

    // Auto-start if both prompt and config are provided
    if (prompt && config) {
      console.log('[WebUI] Auto-starting coordination with URL params');
      urlParamsProcessed.current = true;
      startCoordination(prompt, config);
      // Clear URL params to prevent re-trigger on refresh
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [status, startCoordination]);

  // Handle going back to coordination view with scroll position restoration
  const handleBackToCoordination = useCallback(() => {
    backToCoordination();
    // Restore scroll position after render
    requestAnimationFrame(() => {
      window.scrollTo(0, coordinationScrollRef.current);
    });
  }, [backToCoordination]);

  // Handle going to final answer view
  const handleViewFinalAnswer = useCallback(() => {
    setViewMode('finalComplete');
  }, [setViewMode]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    cancelCoordination();
    reset();
  }, [cancelCoordination, reset]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (inputQuestion.trim() && status === 'connected') {
        // Pass config path when starting coordination
        startCoordination(inputQuestion.trim(), selectedConfig || undefined);
        setInputQuestion('');
      }
    },
    [inputQuestion, status, startCoordination, selectedConfig]
  );

  const handleNewSession = useCallback(() => {
    reset();
    setSessionId(crypto.randomUUID());
  }, [reset]);

  // Handle notification click - open appropriate browser tab
  const handleNotificationClick = useCallback((notification: Notification) => {
    if (notification.type === 'answer') {
      setBrowserInitialTab('answers');
      setIsAnswerBrowserOpen(true);
    } else if (notification.type === 'vote') {
      setBrowserInitialTab('votes');
      setIsAnswerBrowserOpen(true);
    }
  }, []);

  // Handle viewing full response from conversation history
  const handleViewHistoryResponse = useCallback((_turn: number) => {
    // Open answer browser to show the response from that turn
    setBrowserInitialTab('answers');
    setIsAnswerBrowserOpen(true);
    // TODO: Could pass turn number to filter answers by turn
  }, []);

  // Handle follow-up question submission (from footer form)
  const handleFollowUp = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (followUpQuestion.trim() && status === 'connected') {
        // Update store state for new turn
        startContinuation(followUpQuestion.trim());
        // Send continue action to WebSocket
        continueConversation(followUpQuestion.trim());
        setFollowUpQuestion('');
      }
    },
    [followUpQuestion, status, startContinuation, continueConversation]
  );

  // Handle follow-up from FinalAnswerView (takes question string directly)
  const handleFollowUpFromFinalAnswer = useCallback(
    (question: string) => {
      if (question.trim() && status === 'connected') {
        // Update store state for new turn
        startContinuation(question.trim());
        // Send continue action to WebSocket
        continueConversation(question.trim());
      }
    },
    [status, startContinuation, continueConversation]
  );

  const handleConfigChange = useCallback((configPath: string) => {
    setSelectedConfig(configPath);
  }, []);

  // Handle viewing config
  const handleViewConfig = useCallback(async () => {
    if (!selectedConfig) return;

    setConfigLoading(true);
    setIsConfigViewerOpen(true);

    try {
      const res = await fetch(`/api/config/content?path=${encodeURIComponent(selectedConfig)}`);
      if (res.ok) {
        const data = await res.json();
        setConfigContent(data.content || 'Unable to load config content');
      } else {
        setConfigContent('Failed to load config content');
      }
    } catch (err) {
      setConfigContent('Error loading config content');
      console.error('Failed to fetch config content:', err);
    } finally {
      setConfigLoading(false);
    }
  }, [selectedConfig]);

  const handleSessionChange = useCallback((newSessionId: string) => {
    if (newSessionId !== sessionId) {
      // Don't reset - state_snapshot from server will restore the session state
      setSessionId(newSessionId);
    }
  }, [sessionId]);

  // Get config name for display
  const configName = selectedConfig
    ? selectedConfig.split('/').pop()?.replace('.yaml', '') || 'Selected'
    : 'No config';

  // Automation mode: show simplified timeline view
  if (automationMode) {
    return <AutomationView onSessionChange={handleSessionChange} sessionFromUrl={!!initialSession} />;
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Header */}
      <header className="bg-gray-100/50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              MassGen
            </h1>
            <span className="text-gray-400 dark:text-gray-500 text-sm">Multi-Agent Coordination</span>
            <ConnectionIndicator status={status} />
          </div>
          <HeaderControls
            currentSessionId={sessionId}
            selectedConfig={selectedConfig}
            onConfigChange={handleConfigChange}
            onSessionChange={handleSessionChange}
            onNewSession={handleNewSession}
            onOpenAnswerBrowser={() => { setBrowserInitialTab('answers'); setIsAnswerBrowserOpen(true); }}
            onOpenVoteBrowser={() => { setBrowserInitialTab('votes'); setIsAnswerBrowserOpen(true); }}
            onViewConfig={handleViewConfig}
            answerCount={answers.length}
            voteCount={Object.values(voteDistribution).reduce((sum, count) => sum + count, 0)}
          />
        </div>
      </header>

      {/* Question Display */}
      {question && (
        <div className="bg-gray-100/30 dark:bg-gray-800/30 border-b border-gray-200 dark:border-gray-700 px-6 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Conversation history dropdown (floating, doesn't affect layout) */}
              {turnNumber > 1 && (
                <ConversationHistory
                  onViewResponse={handleViewHistoryResponse}
                />
              )}
              <div>
                <span className="text-gray-500 dark:text-gray-500 text-sm">Question: </span>
                <span className="text-gray-800 dark:text-gray-200">{question}</span>
              </div>
            </div>
            <div className="text-xs text-gray-500">
              Config: <span className="text-gray-600 dark:text-gray-400">{configName}</span>
            </div>
          </div>
        </div>
      )}

      {/* Status Toolbar */}
      <StatusToolbar />

      {/* Main Content */}
      <main className="flex-1 p-6 overflow-hidden">
        <div className="max-w-7xl mx-auto space-y-6 h-full flex flex-col">
          {/* Error Display */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"
            >
              <AlertCircle className="w-5 h-5 text-red-500" />
              <span className="text-red-200">{error}</span>
            </motion.div>
          )}

          {/* No Config Warning */}
          {!selectedConfig && !question && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-amber-900/30 border border-amber-700 rounded-lg p-4 flex items-center gap-3"
            >
              <AlertCircle className="w-5 h-5 text-amber-500" />
              <span className="text-amber-200">
                Please select a configuration from the dropdown above before starting.
              </span>
            </motion.div>
          )}

          {/* View Mode Routing - flex-1 for full height in finalStreaming */}
          <div className="flex-1 min-h-0">
          <AnimatePresence mode="sync">
            {/* Coordination View - All Agents */}
            {viewMode === 'coordination' && (
              <motion.section
                key="coordination"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="relative"
              >
                <AgentCarousel />

                {/* Selecting Winner Overlay */}
                <AnimatePresence>
                  {selectingWinner && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="absolute inset-0 bg-gray-900/70 backdrop-blur-sm flex items-center justify-center z-20 rounded-lg"
                    >
                      <div className="flex flex-col items-center gap-4 text-white max-w-md">
                        <Trophy className="w-12 h-12 text-yellow-500 animate-pulse" />
                        <span className="text-xl font-semibold">Selecting Winner</span>

                        {/* Vote Results */}
                        <div className="flex flex-col gap-2 w-full px-4">
                          {Object.entries(voteDistribution)
                            .sort(([, a], [, b]) => b - a)
                            .map(([agentId, votes], idx) => {
                              const agent = agents[agentId];
                              const displayName = agent?.modelName
                                ? `${agentId} (${agent.modelName})`
                                : agentId;
                              const isLeading = idx === 0;
                              return (
                                <motion.div
                                  key={agentId}
                                  initial={{ opacity: 0, x: -20 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: idx * 0.1 }}
                                  className={`flex items-center justify-between px-3 py-2 rounded-lg ${
                                    isLeading
                                      ? 'bg-yellow-500/30 border border-yellow-500/50'
                                      : 'bg-gray-700/50'
                                  }`}
                                >
                                  <span className={isLeading ? 'font-medium' : ''}>{displayName}</span>
                                  <span className={`font-bold ${isLeading ? 'text-yellow-400' : 'text-gray-400'}`}>
                                    {votes} vote{votes !== 1 ? 's' : ''}
                                  </span>
                                </motion.div>
                              );
                            })}
                        </div>

                        <div className="flex items-center gap-2 text-sm text-gray-300">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Starting final answer generation...</span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.section>
            )}

            {/* Final Streaming View - Winner streaming final answer (full-screen) */}
            {viewMode === 'finalStreaming' && winnerAgent && (
              <motion.section
                key="finalStreaming"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                {/* Header */}
                <div className="flex items-center gap-4 mb-4">
                  <button
                    onClick={handleBackToCoordination}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600
                             rounded-lg text-sm transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                  </button>
                  <div className="flex items-center gap-2">
                    <Trophy className="w-6 h-6 text-yellow-500" />
                    <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
                      Winner: {winnerAgent.modelName ? `${winnerAgent.id} (${winnerAgent.modelName})` : winnerAgent.id}
                    </h2>
                  </div>
                  {!isComplete && (
                    <div className="flex items-center gap-2 text-blue-500 dark:text-blue-400 ml-auto">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span className="text-sm">Generating final answer...</span>
                    </div>
                  )}
                </div>

                {/* Fixed-height AgentCard container - matches carousel card height */}
                <div className="h-[450px]">
                  <AgentCard agent={winnerAgent} isWinner={true} disableLayoutAnimation={true} />
                </div>
              </motion.section>
            )}
          </AnimatePresence>
          </div>
        </div>
      </main>

      {/* Input Form */}
      <footer className="bg-gray-100/50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          {isComplete ? (
            <div className="flex flex-col gap-4">
              {/* Status row with action buttons */}
              <div className="flex items-center justify-center gap-4">
                <span className="text-green-500 dark:text-green-400">
                  Turn {turnNumber} Complete!
                </span>
                {/* Show "View Final Answer" button when we have a final answer and are in coordination view */}
                {finalAnswer && viewMode === 'coordination' && (
                  <button
                    onClick={handleViewFinalAnswer}
                    className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-500 rounded-lg transition-colors text-white"
                  >
                    <Trophy className="w-4 h-4" />
                    View Final Answer
                  </button>
                )}
                <button
                  onClick={handleNewSession}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors text-white"
                >
                  New Session
                </button>
              </div>

              {/* Follow-up input row */}
              <form onSubmit={handleFollowUp} className="flex gap-4">
                <input
                  type="text"
                  value={followUpQuestion}
                  onChange={(e) => setFollowUpQuestion(e.target.value)}
                  placeholder="Ask a follow-up question..."
                  disabled={status !== 'connected'}
                  className="flex-1 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3
                           text-gray-900 dark:text-gray-100 placeholder-gray-500
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  type="submit"
                  disabled={!followUpQuestion.trim() || status !== 'connected'}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-400 dark:disabled:bg-gray-600
                           disabled:cursor-not-allowed rounded-lg transition-colors text-white
                           flex items-center gap-2"
                >
                  <Send className="w-5 h-5" />
                  <span>Continue</span>
                </button>
              </form>
            </div>
          ) : question ? (
            /* Cancel button during coordination */
            <div className="flex items-center justify-center gap-4">
              <span className="text-gray-600 dark:text-gray-400">Coordination in progress...</span>
              <button
                onClick={handleCancel}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg transition-colors text-white"
              >
                <XCircle className="w-5 h-5" />
                Cancel
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex gap-4">
              <input
                type="text"
                value={inputQuestion}
                onChange={(e) => setInputQuestion(e.target.value)}
                placeholder={selectedConfig
                  ? "Enter your question for multi-agent coordination..."
                  : "Select a config first..."
                }
                disabled={status !== 'connected' || !selectedConfig}
                className="flex-1 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3
                         text-gray-900 dark:text-gray-100 placeholder-gray-500
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={!inputQuestion.trim() || status !== 'connected' || !selectedConfig}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-400 dark:disabled:bg-gray-600
                         disabled:cursor-not-allowed rounded-lg transition-colors text-white
                         flex items-center gap-2"
              >
                <Send className="w-5 h-5" />
                <span>Start</span>
              </button>
            </form>
          )}
        </div>
      </footer>

      {/* Full-screen Final Answer View */}
      <AnimatePresence>
        {viewMode === 'finalComplete' && (
          <FinalAnswerView
            onBackToAgents={handleBackToCoordination}
            onFollowUp={handleFollowUpFromFinalAnswer}
            onNewSession={handleNewSession}
            isConnected={status === 'connected'}
          />
        )}
      </AnimatePresence>

      {/* Celebration Animation (shows briefly on finalComplete) */}
      <ConvergenceAnimation />

      {/* Answer/Vote Browser Modal (accessible via header buttons) */}
      <AnswerBrowserModal
        isOpen={isAnswerBrowserOpen}
        onClose={() => setIsAnswerBrowserOpen(false)}
        initialTab={browserInitialTab}
      />

      {/* Quickstart Wizard Modal */}
      <QuickstartWizard onConfigSaved={handleConfigChange} />

      {/* Config Viewer Modal */}
      <AnimatePresence>
        {isConfigViewerOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={() => setIsConfigViewerOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[80vh] flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <FileCode className="w-5 h-5 text-blue-500" />
                  <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                    Config File
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 truncate max-w-md" title={selectedConfig || ''}>
                    {selectedConfig}
                  </span>
                  <button
                    onClick={() => setIsConfigViewerOpen(false)}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-auto p-4">
                {configLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                    <span className="ml-2 text-gray-500">Loading config...</span>
                  </div>
                ) : (
                  <pre className="text-sm text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-900 rounded-lg p-4 overflow-auto whitespace-pre font-mono">
                    {configContent}
                  </pre>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Notification Toast (bottom-right) */}
      <NotificationToast onNotificationClick={handleNotificationClick} />

      {/* Keyboard Shortcuts Modal */}
      <KeyboardShortcutsModal
        isOpen={isShortcutsModalOpen}
        onClose={() => setIsShortcutsModalOpen(false)}
        shortcuts={shortcuts}
      />
    </div>
  );
}

export default App;
