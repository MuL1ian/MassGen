/**
 * MassGen Web UI - Main Application
 *
 * Real-time visualization of multi-agent coordination.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Wifi, WifiOff, AlertCircle, XCircle, ArrowLeft, Loader2, Trophy } from 'lucide-react';
import { useWebSocket, ConnectionStatus } from './hooks/useWebSocket';
import { useAgentStore, selectQuestion, selectIsComplete, selectAnswers, selectViewMode, selectSelectedAgent, selectAgents, selectFinalAnswer } from './stores/agentStore';
import { useThemeStore } from './stores/themeStore';
import { AgentCarousel } from './components/AgentCarousel';
import { AgentCard } from './components/AgentCard';
import { StatusToolbar } from './components/StatusToolbar';
import { ConvergenceAnimation } from './components/ConvergenceAnimation';
import { HeaderControls } from './components/HeaderControls';
import { AnswerBrowserModal } from './components/AnswerBrowserModal';
import { FinalAnswerView } from './components/FinalAnswerView';

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

export function App() {
  // Session management
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
  const [inputQuestion, setInputQuestion] = useState('');

  const question = useAgentStore(selectQuestion);
  const isComplete = useAgentStore(selectIsComplete);
  const answers = useAgentStore(selectAnswers);
  const viewMode = useAgentStore(selectViewMode);
  const selectedAgent = useAgentStore(selectSelectedAgent);
  const agents = useAgentStore(selectAgents);
  const finalAnswer = useAgentStore(selectFinalAnswer);
  const reset = useAgentStore((s) => s.reset);
  const backToCoordination = useAgentStore((s) => s.backToCoordination);
  const setViewMode = useAgentStore((s) => s.setViewMode);

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

  // Answer browser modal state
  const [isAnswerBrowserOpen, setIsAnswerBrowserOpen] = useState(false);

  const { status, startCoordination, cancelCoordination, error } = useWebSocket({
    sessionId,
    autoConnect: true,
  });

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

  const handleConfigChange = useCallback((configPath: string) => {
    setSelectedConfig(configPath);
  }, []);

  const handleSessionChange = useCallback((newSessionId: string) => {
    if (newSessionId !== sessionId) {
      reset();
      setSessionId(newSessionId);
    }
  }, [sessionId, reset]);

  // Get config name for display
  const configName = selectedConfig
    ? selectedConfig.split('/').pop()?.replace('.yaml', '') || 'Selected'
    : 'No config';

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
            onOpenAnswerBrowser={() => setIsAnswerBrowserOpen(true)}
            answerCount={answers.length}
          />
        </div>
      </header>

      {/* Question Display */}
      {question && (
        <div className="bg-gray-100/30 dark:bg-gray-800/30 border-b border-gray-200 dark:border-gray-700 px-6 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div>
              <span className="text-gray-500 dark:text-gray-500 text-sm">Question: </span>
              <span className="text-gray-800 dark:text-gray-200">{question}</span>
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
      <main className="flex-1 p-6">
        <div className="max-w-7xl mx-auto space-y-6">
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

          {/* View Mode Routing */}
          <AnimatePresence mode="wait">
            {/* Coordination View - All Agents */}
            {viewMode === 'coordination' && (
              <motion.section
                key="coordination"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <AgentCarousel />
              </motion.section>
            )}

            {/* Final Streaming View - Winner streaming final answer */}
            {viewMode === 'finalStreaming' && winnerAgent && (
              <motion.section
                key="finalStreaming"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="flex items-center gap-4 mb-4">
                  <button
                    onClick={handleBackToCoordination}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600
                             rounded-lg text-sm transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    Back to All Agents
                  </button>
                  <div className="flex items-center gap-2">
                    <Trophy className="w-5 h-5 text-yellow-500" />
                    <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                      {winnerAgent.modelName ? `${winnerAgent.id} (${winnerAgent.modelName})` : winnerAgent.id}
                    </h2>
                  </div>
                  <div className="flex items-center gap-2 text-blue-500 dark:text-blue-400 ml-auto">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Generating final answer...</span>
                  </div>
                </div>
                {/* Match the single-agent grid layout from AgentCarousel */}
                <div className="grid grid-cols-1 gap-4 py-4">
                  <div className="h-[450px] min-w-0">
                    <AgentCard agent={winnerAgent} isWinner={true} />
                  </div>
                </div>
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Input Form */}
      <footer className="bg-gray-100/50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          {isComplete ? (
            <div className="flex items-center justify-center gap-4">
              <span className="text-green-500 dark:text-green-400">Coordination Complete!</span>
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
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors text-white"
              >
                Start New Session
              </button>
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
          <FinalAnswerView onBackToAgents={handleBackToCoordination} />
        )}
      </AnimatePresence>

      {/* Celebration Animation (shows briefly on finalComplete) */}
      <ConvergenceAnimation />

      {/* Answer Browser Modal (accessible via header button) */}
      <AnswerBrowserModal
        isOpen={isAnswerBrowserOpen}
        onClose={() => setIsAnswerBrowserOpen(false)}
      />
    </div>
  );
}

export default App;
