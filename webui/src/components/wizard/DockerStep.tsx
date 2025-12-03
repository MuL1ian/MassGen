/**
 * Docker Step Component
 *
 * First step in the quickstart wizard - choose Docker or local mode.
 */

import { motion } from 'framer-motion';
import { Container, Monitor, AlertTriangle, Check } from 'lucide-react';
import { useWizardStore } from '../../stores/wizardStore';

export function DockerStep() {
  const useDocker = useWizardStore((s) => s.useDocker);
  const setUseDocker = useWizardStore((s) => s.setUseDocker);
  const setupStatus = useWizardStore((s) => s.setupStatus);

  const dockerAvailable = setupStatus?.docker_available ?? false;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
          Execution Mode
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Choose how agents execute code and commands.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Docker Option */}
        <button
          onClick={() => dockerAvailable && setUseDocker(true)}
          disabled={!dockerAvailable}
          className={`p-6 rounded-lg border-2 text-left transition-all ${
            useDocker && dockerAvailable
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : dockerAvailable
              ? 'border-gray-300 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600'
              : 'border-gray-200 dark:border-gray-700 opacity-50 cursor-not-allowed'
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            <Container className={`w-8 h-8 ${useDocker && dockerAvailable ? 'text-blue-500' : 'text-gray-500'}`} />
            <div className="flex items-center gap-2">
              <span className="text-lg font-medium text-gray-800 dark:text-gray-200">
                Docker
              </span>
              {dockerAvailable && (
                <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                  Recommended
                </span>
              )}
            </div>
            {useDocker && dockerAvailable && (
              <Check className="w-5 h-5 text-blue-500 ml-auto" />
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Full code execution in isolated containers. Agents can run commands,
            install packages, and use tools safely.
          </p>
          {!dockerAvailable && (
            <div className="mt-3 flex items-center gap-2 text-amber-600 dark:text-amber-400 text-sm">
              <AlertTriangle className="w-4 h-4" />
              <span>Docker images not found. Run <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">massgen --setup-docker</code></span>
            </div>
          )}
        </button>

        {/* Local Option */}
        <button
          onClick={() => setUseDocker(false)}
          className={`p-6 rounded-lg border-2 text-left transition-all ${
            !useDocker
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600'
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            <Monitor className={`w-8 h-8 ${!useDocker ? 'text-blue-500' : 'text-gray-500'}`} />
            <span className="text-lg font-medium text-gray-800 dark:text-gray-200">
              Local
            </span>
            {!useDocker && (
              <Check className="w-5 h-5 text-blue-500 ml-auto" />
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            File operations only. Agents can create and edit files but cannot
            execute commands or install packages.
          </p>
        </button>
      </div>

      <div className="text-xs text-gray-500 dark:text-gray-500 mt-4">
        You can change this later in the config file.
      </div>
    </motion.div>
  );
}
