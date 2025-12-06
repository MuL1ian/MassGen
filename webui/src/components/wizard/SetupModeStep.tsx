/**
 * Setup Mode Step Component
 *
 * Third step (for 2+ agents) - choose same or different providers.
 */

import { motion } from 'framer-motion';
import { Copy, Shuffle, Check } from 'lucide-react';
import { useWizardStore } from '../../stores/wizardStore';

export function SetupModeStep() {
  const setupMode = useWizardStore((s) => s.setupMode);
  const setSetupMode = useWizardStore((s) => s.setSetupMode);
  const agentCount = useWizardStore((s) => s.agentCount);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
          Setup Mode
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure how your {agentCount} agents will be set up.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Same Config Option */}
        <button
          onClick={() => setSetupMode('same')}
          className={`p-6 rounded-lg border-2 text-left transition-all ${
            setupMode === 'same'
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600'
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            <Copy className={`w-8 h-8 ${setupMode === 'same' ? 'text-blue-500' : 'text-gray-500'}`} />
            <span className="text-lg font-medium text-gray-800 dark:text-gray-200">
              Same for all
            </span>
            {setupMode === 'same' && (
              <Check className="w-5 h-5 text-blue-500 ml-auto" />
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Use the same provider and model for all agents. Quick setup for
            comparing agent responses.
          </p>
        </button>

        {/* Different Config Option */}
        <button
          onClick={() => setSetupMode('different')}
          className={`p-6 rounded-lg border-2 text-left transition-all ${
            setupMode === 'different'
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600'
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            <Shuffle className={`w-8 h-8 ${setupMode === 'different' ? 'text-blue-500' : 'text-gray-500'}`} />
            <span className="text-lg font-medium text-gray-800 dark:text-gray-200">
              Different per agent
            </span>
            {setupMode === 'different' && (
              <Check className="w-5 h-5 text-blue-500 ml-auto" />
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Configure each agent with a different provider and model.
            Great for diverse perspectives.
          </p>
        </button>
      </div>
    </motion.div>
  );
}
