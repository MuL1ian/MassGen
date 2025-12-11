/**
 * StatusToolbar Component
 *
 * Horizontal overview of all agents' status.
 * Shows status badges, vote details, and allows quick navigation.
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Bot, CheckCircle, Clock, AlertCircle, Vote, Loader2, ArrowRight } from 'lucide-react';
import { useAgentStore, selectAgents, selectAgentOrder, selectSelectedAgent } from '../stores/agentStore';
import type { AgentStatus } from '../types';

const statusIcons: Record<AgentStatus, typeof Bot> = {
  waiting: Clock,
  working: Loader2,
  voting: Vote,
  completed: CheckCircle,
  failed: AlertCircle,
};

const statusColors: Record<AgentStatus, string> = {
  waiting: 'bg-gray-600 text-gray-300',
  working: 'bg-blue-600 text-blue-100',
  voting: 'bg-amber-600 text-amber-100',
  completed: 'bg-green-600 text-green-100',
  failed: 'bg-red-600 text-red-100',
};

interface StatusToolbarProps {
  onAgentClick?: (agentId: string) => void;
}

/**
 * Get answer label for an agent (e.g., "answer1.1" for first agent's first answer)
 */
function getAnswerLabel(agentId: string, agentOrder: string[], answerNum: number = 1): string {
  const agentIndex = agentOrder.indexOf(agentId) + 1;
  return `answer${agentIndex}.${answerNum}`;
}

export function StatusToolbar({ onAgentClick }: StatusToolbarProps) {
  const agents = useAgentStore(selectAgents);
  const agentOrder = useAgentStore(selectAgentOrder);
  const selectedAgent = useAgentStore(selectSelectedAgent);

  // Compute status counts and vote info
  const { workingCount, votedCount, voteDetails } = useMemo(() => {
    let working = 0;
    let voted = 0;
    const votes: Array<{ voter: string; votedFor: string; answerLabel: string }> = [];

    agentOrder.forEach((agentId) => {
      const agent = agents[agentId];
      if (!agent) return;

      // Count working agents (status is working or voting but hasn't voted yet)
      if (agent.status === 'working' || (agent.status === 'voting' && !agent.voteTarget)) {
        working++;
      }

      // Count voted agents
      if (agent.voteTarget) {
        voted++;
        // Get target agent's answer count for label
        const targetAgent = agents[agent.voteTarget];
        const answerNum = targetAgent?.answerCount || 1;
        votes.push({
          voter: agentId,
          votedFor: agent.voteTarget,
          answerLabel: getAnswerLabel(agent.voteTarget, agentOrder, answerNum),
        });
      }
    });

    return { workingCount: working, votedCount: voted, voteDetails: votes };
  }, [agents, agentOrder]);

  return (
    <div className="bg-gray-100/50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Agent Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          {agentOrder.map((agentId) => {
            const agent = agents[agentId];
            if (!agent) return null;

            const Icon = statusIcons[agent.status];
            const colorClass = statusColors[agent.status];
            const isWinner = selectedAgent === agentId;
            const hasVoted = !!agent.voteTarget;

            return (
              <motion.button
                key={agentId}
                onClick={() => onAgentClick?.(agentId)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`
                  flex items-center gap-2 px-3 py-1.5 rounded-full
                  transition-all duration-200 cursor-pointer
                  ${colorClass}
                  ${isWinner ? 'ring-2 ring-yellow-500 ring-offset-2 ring-offset-white dark:ring-offset-gray-900' : ''}
                  ${hasVoted && !isWinner ? 'ring-1 ring-amber-500/50' : ''}
                `}
              >
                <Icon
                  className={`w-4 h-4 ${agent.status === 'working' ? 'animate-spin' : ''}`}
                />
                <span className="text-sm font-medium">{agentId}</span>
                <span className="text-xs bg-black/20 px-1.5 rounded-full">
                  #{agentOrder.indexOf(agentId) + 1}
                </span>
                {isWinner && <span className="text-sm">👑</span>}
              </motion.button>
            );
          })}
        </div>

        {/* Summary Stats */}
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
            <Loader2 className="w-4 h-4 text-blue-500" />
            <span>Working: {workingCount}</span>
          </div>
          <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>Voted: {votedCount}</span>
          </div>
        </div>
      </div>

      {/* Vote Details */}
      {voteDetails.length > 0 && (
        <div className="max-w-7xl mx-auto flex items-center gap-2 mt-2 flex-wrap">
          {voteDetails.map((vote) => (
            <span
              key={vote.voter}
              className="flex items-center gap-1 px-2 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded text-xs"
            >
              <span className="font-medium">{vote.voter}</span>
              <ArrowRight className="w-3 h-3" />
              <span className="text-amber-600 dark:text-amber-200">{vote.answerLabel}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default StatusToolbar;
