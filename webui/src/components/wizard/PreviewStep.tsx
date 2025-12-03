/**
 * Preview Step Component
 *
 * Final step - preview generated config and save.
 */

import { motion } from 'framer-motion';
import { FileText, Check, AlertCircle, Loader2 } from 'lucide-react';
import { useWizardStore } from '../../stores/wizardStore';

export function PreviewStep() {
  const generatedYaml = useWizardStore((s) => s.generatedYaml);
  const isLoading = useWizardStore((s) => s.isLoading);
  const error = useWizardStore((s) => s.error);
  const setupStatus = useWizardStore((s) => s.setupStatus);

  if (isLoading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center py-12"
      >
        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
        <p className="text-gray-600 dark:text-gray-400">Generating configuration...</p>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="space-y-6"
      >
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
            <h3 className="text-lg font-semibold text-red-700 dark:text-red-400">
              Error Generating Config
            </h3>
          </div>
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
          Review Configuration
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          This config will be saved to{' '}
          <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded text-xs">
            {setupStatus?.config_path || '~/.config/massgen/config.yaml'}
          </code>
        </p>
      </div>

      {generatedYaml && (
        <div className="bg-gray-900 rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-800 border-b border-gray-700">
            <FileText className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-300">config.yaml</span>
          </div>
          <pre className="p-4 text-sm text-gray-300 overflow-x-auto max-h-[400px] overflow-y-auto">
            <code>{generatedYaml}</code>
          </pre>
        </div>
      )}

      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <Check className="w-5 h-5 text-green-500" />
          <span className="text-sm text-green-700 dark:text-green-400">
            Click "Save & Start" to save this configuration and begin using MassGen.
          </span>
        </div>
      </div>
    </motion.div>
  );
}
