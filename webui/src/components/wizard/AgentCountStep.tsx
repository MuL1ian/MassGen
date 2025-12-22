/**
 * Agent Count Step Component
 *
 * Second step - choose number of agents.
 */

import { motion } from 'framer-motion';
import { Users, Check } from 'lucide-react';
import { useWizardStore } from '../../stores/wizardStore';

const agentOptions = [
  { count: 1, label: '1 agent', description: 'Single agent' },
  { count: 2, label: '2 agents', description: 'Basic collaboration' },
  { count: 3, label: '3 agents', description: 'Recommended for most tasks', recommended: true },
  { count: 4, label: '4 agents', description: 'More diverse perspectives' },
  { count: 5, label: '5 agents', description: 'Maximum collaboration' },
];

export function AgentCountStep() {
  const agentCount = useWizardStore((s) => s.agentCount);
  const setAgentCount = useWizardStore((s) => s.setAgentCount);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
          How many agents?
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          More agents provide diverse perspectives but use more API credits.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {agentOptions.map((option) => (
          <button
            key={option.count}
            onClick={() => setAgentCount(option.count)}
            className={`p-4 rounded-lg border-2 text-left transition-all ${
              agentCount === option.count
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Users className={`w-5 h-5 ${agentCount === option.count ? 'text-blue-500' : 'text-gray-500'}`} />
                <span className="font-medium text-gray-800 dark:text-gray-200">
                  {option.label}
                </span>
              </div>
              {agentCount === option.count && (
                <Check className="w-5 h-5 text-blue-500" />
              )}
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              {option.description}
            </p>
            {option.recommended && (
              <span className="inline-block mt-2 text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                Recommended
              </span>
            )}
          </button>
        ))}
      </div>
    </motion.div>
  );
}
