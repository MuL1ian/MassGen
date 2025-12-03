/**
 * VoteVisualization Component
 *
 * Displays vote distribution with animated bars.
 * Highlights the winner with golden effect.
 */

import { motion } from 'framer-motion';
import { Vote, Trophy } from 'lucide-react';
import { useAgentStore, selectVoteDistribution, selectSelectedAgent, selectAgentOrder } from '../stores/agentStore';

export function VoteVisualization() {
  const voteDistribution = useAgentStore(selectVoteDistribution);
  const selectedAgent = useAgentStore(selectSelectedAgent);
  const agentOrder = useAgentStore(selectAgentOrder);

  // Get max votes for scaling
  const maxVotes = Math.max(...Object.values(voteDistribution), 1);
  const totalVotes = Object.values(voteDistribution).reduce((a, b) => a + b, 0);

  // Sort by vote count
  const sortedAgents = [...agentOrder].sort(
    (a, b) => (voteDistribution[b] || 0) - (voteDistribution[a] || 0)
  );

  if (totalVotes === 0) {
    return (
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 text-gray-400 mb-4">
          <Vote className="w-5 h-5" />
          <h3 className="font-medium">Vote Distribution</h3>
        </div>
        <div className="text-gray-500 text-sm text-center py-4">
          No votes recorded yet
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-gray-300">
          <Vote className="w-5 h-5" />
          <h3 className="font-medium">Vote Distribution</h3>
        </div>
        <span className="text-sm text-gray-500">Total: {totalVotes}</span>
      </div>

      <div className="space-y-3">
        {sortedAgents.map((agentId) => {
          const votes = voteDistribution[agentId] || 0;
          const percentage = (votes / maxVotes) * 100;
          const isWinner = selectedAgent === agentId;

          return (
            <div key={agentId} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={isWinner ? 'text-yellow-400 font-medium' : 'text-gray-300'}>
                    {agentId}
                  </span>
                  {isWinner && <Trophy className="w-4 h-4 text-yellow-500" />}
                </div>
                <span className={isWinner ? 'text-yellow-400' : 'text-gray-500'}>
                  {votes} vote{votes !== 1 ? 's' : ''}
                </span>
              </div>

              {/* Vote Bar */}
              <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${percentage}%` }}
                  transition={{
                    type: 'spring',
                    stiffness: 100,
                    damping: 15,
                  }}
                  className={`h-full rounded-full ${
                    isWinner ? 'vote-bar-winner' : 'vote-bar'
                  }`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default VoteVisualization;
