/**
 * Quickstart Wizard Modal
 *
 * Full-screen modal for guided configuration setup.
 */

import { useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, Loader2, Wand2 } from 'lucide-react';
import { useWizardStore, WizardStep } from '../stores/wizardStore';
import {
  DockerStep,
  ApiKeyStep,
  AgentCountStep,
  SetupModeStep,
  AgentConfigStep,
  CoordinationStep,
  PreviewStep,
} from './wizard';

const stepConfig: Record<WizardStep, { title: string; subtitle: string }> = {
  docker: { title: 'Execution Mode', subtitle: 'Step 1 of 7' },
  apiKeys: { title: 'API Keys', subtitle: 'Step 2 of 7' },
  agentCount: { title: 'Number of Agents', subtitle: 'Step 3 of 7' },
  setupMode: { title: 'Setup Mode', subtitle: 'Step 4 of 7' },
  agentConfig: { title: 'Agent Configuration', subtitle: 'Step 5 of 7' },
  coordination: { title: 'Coordination Settings', subtitle: 'Step 6 of 7' },
  preview: { title: 'Review & Save', subtitle: 'Step 7 of 7' },
};

interface QuickstartWizardProps {
  onConfigSaved?: (configPath: string) => void;
}

export function QuickstartWizard({ onConfigSaved }: QuickstartWizardProps) {
  const isOpen = useWizardStore((s) => s.isOpen);
  const currentStep = useWizardStore((s) => s.currentStep);
  const isLoading = useWizardStore((s) => s.isLoading);
  const agents = useWizardStore((s) => s.agents);
  const agentCount = useWizardStore((s) => s.agentCount);

  const closeWizard = useWizardStore((s) => s.closeWizard);
  const nextStep = useWizardStore((s) => s.nextStep);
  const prevStep = useWizardStore((s) => s.prevStep);
  const saveConfig = useWizardStore((s) => s.saveConfig);
  const reset = useWizardStore((s) => s.reset);

  const handleClose = useCallback(() => {
    closeWizard();
    reset();
  }, [closeWizard, reset]);

  const handleSave = useCallback(async () => {
    const success = await saveConfig();
    if (success) {
      // Get the saved path from store (set by saveConfig)
      const configPath = useWizardStore.getState().savedConfigPath;
      handleClose();
      // Notify parent of the saved config path
      if (configPath && onConfigSaved) {
        onConfigSaved(configPath);
      }
    }
  }, [saveConfig, handleClose, onConfigSaved]);

  const providers = useWizardStore((s) => s.providers);

  // Check if we can proceed to next step
  const canProceed = useCallback(() => {
    switch (currentStep) {
      case 'docker':
        return true; // Always can proceed from docker step
      case 'apiKeys':
        // Must have at least one provider with API key
        return providers.some((p) => p.has_api_key);
      case 'agentCount':
        return agentCount >= 1 && agentCount <= 5;
      case 'setupMode':
        return true;
      case 'agentConfig':
        // All agents must have provider and model selected
        return agents.every((agent) => agent.provider && agent.model);
      case 'coordination':
        return true; // Coordination settings are optional, defaults are fine
      case 'preview':
        return true;
      default:
        return false;
    }
  }, [currentStep, agentCount, agents, providers]);

  // Render current step content
  const renderStep = () => {
    switch (currentStep) {
      case 'docker':
        return <DockerStep />;
      case 'apiKeys':
        return <ApiKeyStep />;
      case 'agentCount':
        return <AgentCountStep />;
      case 'setupMode':
        return <SetupModeStep />;
      case 'agentConfig':
        return <AgentConfigStep />;
      case 'coordination':
        return <CoordinationStep />;
      case 'preview':
        return <PreviewStep />;
      default:
        return null;
    }
  };

  const stepInfo = stepConfig[currentStep];
  const isFirstStep = currentStep === 'docker';
  const isLastStep = currentStep === 'preview';

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="relative w-full max-w-6xl mx-4 h-[90vh] bg-white dark:bg-gray-900
                       rounded-xl shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Wand2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                    Quickstart Setup
                  </h1>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {stepInfo.subtitle} - {stepInfo.title}
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400
                         dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Progress Bar */}
            <div className="px-6 py-2 bg-gray-50 dark:bg-gray-800/50">
              <div className="flex items-center gap-2">
                {['docker', 'apiKeys', 'agentCount', 'setupMode', 'agentConfig', 'coordination', 'preview'].map((step, index) => {
                  const allSteps = ['docker', 'apiKeys', 'agentCount', 'setupMode', 'agentConfig', 'coordination', 'preview'];
                  const stepIndex = allSteps.indexOf(currentStep);
                  const isActive = index === stepIndex;
                  const isComplete = index < stepIndex;
                  // Hide apiKeys step indicator when providers have keys
                  if (step === 'apiKeys' && providers.some((p) => p.has_api_key)) {
                    return null;
                  }
                  // Hide setupMode step indicator when only 1 agent
                  if (step === 'setupMode' && agentCount === 1) {
                    return null;
                  }
                  return (
                    <div key={step} className="flex-1">
                      <div
                        className={`h-1.5 rounded-full transition-colors ${
                          isComplete
                            ? 'bg-blue-500'
                            : isActive
                            ? 'bg-blue-300 dark:bg-blue-600'
                            : 'bg-gray-200 dark:bg-gray-700'
                        }`}
                      />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-6">
              <AnimatePresence mode="wait">
                {renderStep()}
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              <button
                onClick={isFirstStep ? handleClose : prevStep}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400
                         hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>{isFirstStep ? 'Cancel' : 'Back'}</span>
              </button>

              {isLastStep ? (
                <button
                  onClick={handleSave}
                  disabled={isLoading || !canProceed()}
                  className="flex items-center gap-2 px-6 py-2 bg-green-600 hover:bg-green-500
                           disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed
                           text-white rounded-lg transition-colors"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-4 h-4" />
                      <span>Save & Start</span>
                    </>
                  )}
                </button>
              ) : (
                <button
                  onClick={nextStep}
                  disabled={!canProceed()}
                  className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-500
                           disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed
                           text-white rounded-lg transition-colors"
                >
                  <span>Next</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
