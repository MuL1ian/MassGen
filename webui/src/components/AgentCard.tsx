/**
 * AgentCard Component
 *
 * Displays individual agent panel with streaming content,
 * status badge, and tool activity.
 */

import { motion } from 'framer-motion';
import { Bot, CheckCircle, Clock, AlertCircle, Vote, Loader2, ChevronDown } from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { AgentState, AgentStatus } from '../types';
import { useAgentStore } from '../stores/agentStore';

/**
 * Parse content and highlight tool calls, status messages, etc.
 */
function renderHighlightedContent(content: string): React.ReactNode {
  if (!content) return null;

  const lines = content.split('\n');

  return lines.map((line, idx) => {
    // Tool call markers
    if (line.includes('🔧') || line.includes('Tool:') || line.includes('tool_call')) {
      return (
        <span key={idx} className="text-blue-400">
          {line}
          {'\n'}
        </span>
      );
    }
    // Success/completion markers
    if (line.includes('✅') || line.includes('✓')) {
      return (
        <span key={idx} className="text-green-400">
          {line}
          {'\n'}
        </span>
      );
    }
    // Error markers
    if (line.includes('❌') || line.includes('Error') || line.includes('error')) {
      return (
        <span key={idx} className="text-red-400">
          {line}
          {'\n'}
        </span>
      );
    }
    // Vote markers
    if (line.includes('🗳️') || line.includes('vote') || line.includes('Vote')) {
      return (
        <span key={idx} className="text-amber-400">
          {line}
          {'\n'}
        </span>
      );
    }
    // Answer markers
    if (line.includes('💡') || line.includes('new_answer')) {
      return (
        <span key={idx} className="text-purple-400">
          {line}
          {'\n'}
        </span>
      );
    }
    // Default
    return (
      <span key={idx}>
        {line}
        {'\n'}
      </span>
    );
  });
}

interface AgentCardProps {
  agent: AgentState;
  isWinner?: boolean;
  isVisible?: boolean;
  disableLayoutAnimation?: boolean;
}

// Status config - note: 'completed' only shows after final answer
const statusConfig: Record<AgentStatus, { color: string; icon: typeof Bot; label: string }> = {
  waiting: { color: 'bg-gray-500', icon: Clock, label: 'Waiting' },
  working: { color: 'bg-blue-500', icon: Loader2, label: 'Working' },
  voting: { color: 'bg-amber-500', icon: Vote, label: 'Voting' },
  completed: { color: 'bg-green-500', icon: CheckCircle, label: 'Done' },
  failed: { color: 'bg-red-500', icon: AlertCircle, label: 'Failed' },
};

export function AgentCard({ agent, isWinner = false, isVisible = true, disableLayoutAnimation = false }: AgentCardProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const setAgentRound = useAgentStore((s) => s.setAgentRound);

  // Store-based dropdown state for persistence across re-renders
  const agentUIState = useAgentStore((s) => s.agentUIState[agent.id]);
  const setAgentDropdownOpen = useAgentStore((s) => s.setAgentDropdownOpen);
  const closeAllDropdowns = useAgentStore((s) => s.closeAllDropdowns);
  const showRoundDropdown = agentUIState?.dropdownOpen ?? false;

  const { color, icon: StatusIcon, label } = statusConfig[agent.status];

  // Get display name with model
  const displayName = agent.modelName
    ? `${agent.id} (${agent.modelName})`
    : agent.id;

  // Get current display round info (what user sees in dropdown)
  const displayRound = agent.rounds?.find(r => r.id === agent.displayRoundId);
  const roundLabel = displayRound?.label || 'current';
  const hasMultipleRounds = (agent.rounds?.length || 0) > 1;

  // Determine what content to display:
  // - If viewing current round and it's still streaming (has currentContent), show live streaming content
  // - Otherwise, use the round's stored content (for completed rounds or when browsing history)
  const isViewingCurrentRound = agent.displayRoundId === agent.currentRoundId;
  const displayContent = isViewingCurrentRound && agent.currentContent
    ? agent.currentContent
    : displayRound?.content || agent.currentContent || '';

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [agent.currentContent]);

  // Click-outside handler to close dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        if (showRoundDropdown) {
          setAgentDropdownOpen(agent.id, false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showRoundDropdown, agent.id, setAgentDropdownOpen]);

  // Handler to toggle dropdown (close all others first)
  const handleDropdownToggle = () => {
    if (showRoundDropdown) {
      setAgentDropdownOpen(agent.id, false);
    } else {
      closeAllDropdowns();
      setAgentDropdownOpen(agent.id, true);
    }
  };

  return (
    <motion.div
      layout={!disableLayoutAnimation}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{
        opacity: isVisible ? 1 : 0.3,
        scale: isWinner && !disableLayoutAnimation ? 1.02 : 1,
      }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 30,
      }}
      className={`
        flex flex-col h-full w-full
        bg-white dark:bg-gray-800 rounded-lg border-2 overflow-hidden
        ${isWinner ? 'border-yellow-500 shadow-lg shadow-yellow-500/20' : 'border-gray-200 dark:border-gray-700'}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-gray-100/50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          <span className="font-medium text-gray-800 dark:text-gray-200">{displayName}</span>
          {isWinner && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="text-yellow-500 text-lg"
            >
              👑
            </motion.span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Round Selector Dropdown */}
          {hasMultipleRounds && (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={handleDropdownToggle}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700
                         hover:bg-gray-300 dark:hover:bg-gray-600 rounded transition-colors"
              >
                <span className="text-gray-700 dark:text-gray-300">{roundLabel}</span>
                <ChevronDown className={`w-3 h-3 transition-transform ${showRoundDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showRoundDropdown && (
                <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg z-10 min-w-[120px]">
                  {agent.rounds?.map((round) => (
                    <button
                      key={round.id}
                      onClick={() => {
                        setAgentRound(agent.id, round.id);
                        setAgentDropdownOpen(agent.id, false);
                      }}
                      className={`w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-gray-700
                               ${round.id === agent.displayRoundId ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'}`}
                    >
                      {round.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Status Badge */}
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full ${color}`}>
            <StatusIcon
              className={`w-3.5 h-3.5 text-white ${agent.status === 'working' ? 'animate-spin' : ''}`}
            />
            <span className="text-xs font-medium text-white">{label}</span>
          </div>
        </div>
      </div>

      {/* Answer Count & Vote Target */}
      <div className="flex items-center gap-4 px-3 py-2 bg-gray-100/50 dark:bg-gray-800/50 text-sm">
        <span className="text-gray-500 dark:text-gray-400">
          Answers: <span className="text-gray-800 dark:text-gray-200 font-medium">{agent.answerCount}</span>
        </span>
        {agent.voteTarget && (
          <span className="text-gray-500 dark:text-gray-400">
            Voted for:{' '}
            <span className="text-amber-600 dark:text-amber-400 font-medium">{agent.voteTarget}</span>
          </span>
        )}
      </div>

      {/* Content Area */}
      <div
        ref={contentRef}
        className="flex-1 p-3 overflow-y-auto custom-scrollbar text-sm font-mono"
      >
        <pre className="whitespace-pre-wrap text-gray-700 dark:text-gray-300 leading-relaxed">
          {displayContent ? (
            <>
              {renderHighlightedContent(displayContent)}
              {/* Pulsing ellipses when streaming - only for current round */}
              {isViewingCurrentRound && agent.status === 'working' && (
                <span className="text-blue-400">
                  <span className="streaming-dot">.</span>
                  <span className="streaming-dot">.</span>
                  <span className="streaming-dot">.</span>
                </span>
              )}
            </>
          ) : (
            <span className="text-gray-500 italic">
              {agent.status === 'working' ? 'Generating response' : 'Waiting'}
              <span className="typing-dot">.</span>
              <span className="typing-dot">.</span>
              <span className="typing-dot">.</span>
            </span>
          )}
        </pre>
      </div>

      {/* Tool Activity */}
      {agent.toolCalls.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-2 bg-gray-100/30 dark:bg-gray-900/30">
          <div className="text-xs text-gray-500 mb-1">Recent Tools:</div>
          <div className="flex flex-wrap gap-1">
            {agent.toolCalls.slice(-3).map((tool, idx) => (
              <span
                key={idx}
                className={`px-2 py-0.5 rounded text-xs ${
                  tool.success === false
                    ? 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'
                    : tool.result
                    ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
                    : 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
                }`}
              >
                {tool.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default AgentCard;
