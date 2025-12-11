/**
 * Agent Config Step Component
 *
 * Fourth step - configure provider and model for each agent.
 * Uses searchable combobox for both provider and model selection.
 */

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bot, Key, AlertCircle } from 'lucide-react';
import { useWizardStore, ProviderInfo } from '../../stores/wizardStore';
import { SearchableCombobox } from './SearchableCombobox';

interface AgentConfigRowProps {
  agentId: string;
  provider: string;
  model: string;
  providers: ProviderInfo[];
  onProviderChange: (provider: string) => void;
  onModelChange: (model: string) => void;
}

function AgentConfigRow({
  agentId,
  provider,
  model,
  providers,
  onProviderChange,
  onModelChange,
}: AgentConfigRowProps) {
  const dynamicModels = useWizardStore((s) => s.dynamicModels);
  const loadingModels = useWizardStore((s) => s.loadingModels);
  const fetchDynamicModels = useWizardStore((s) => s.fetchDynamicModels);

  const selectedProvider = providers.find((p) => p.id === provider);
  const agentLetter = agentId.replace('agent_', '').toUpperCase();

  // Fetch dynamic models when provider changes
  useEffect(() => {
    if (provider && !dynamicModels[provider]) {
      fetchDynamicModels(provider);
    }
  }, [provider, dynamicModels, fetchDynamicModels]);

  // Get models for this provider (dynamic if available, otherwise static)
  const availableModels = provider
    ? dynamicModels[provider] || selectedProvider?.models || []
    : [];

  // Build provider options
  const availableProviders = providers.filter((p) => p.has_api_key);
  const unavailableProviders = providers.filter((p) => !p.has_api_key);

  const providerOptions = [
    ...availableProviders.map((p) => ({
      value: p.id,
      label: p.name,
      group: 'Available',
    })),
    ...unavailableProviders.map((p) => ({
      value: p.id,
      label: `${p.name} (needs ${p.env_var})`,
      disabled: true,
      group: 'Unavailable (no API key)',
    })),
  ];

  // Build model options - filter out "custom" placeholder and show all real models
  const modelOptions = availableModels
    .filter((m) => m !== 'custom')  // Don't show "custom" as an option
    .map((m) => ({
      value: m,
      label: m === selectedProvider?.default_model ? `${m} (default)` : m,
    }));

  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-4">
        <Bot className="w-5 h-5 text-blue-500" />
        <span className="font-medium text-gray-800 dark:text-gray-200">
          Agent {agentLetter}
        </span>
        {model ? (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            ({model})
          </span>
        ) : !provider ? (
          <span className="text-xs text-amber-500 flex items-center gap-1">
            <Key className="w-3 h-3" />
            Not configured
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Provider
          </label>
          <SearchableCombobox
            options={providerOptions}
            value={provider}
            onChange={(newProvider) => {
              // Parent's onProviderChange handles setting both provider and default model
              onProviderChange(newProvider);
            }}
            placeholder="Search providers..."
            allowCustom={false}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Model {modelOptions.length > 0 && (
              <span className="text-xs text-gray-500 font-normal ml-1">
                ({modelOptions.length} available)
              </span>
            )}
          </label>
          <SearchableCombobox
            options={modelOptions}
            value={model}
            onChange={onModelChange}
            placeholder={
              !provider
                ? 'Select provider first'
                : loadingModels[provider]
                ? 'Loading models...'
                : modelOptions.length > 0
                ? `Search ${modelOptions.length} models...`
                : 'Type a model name...'
            }
            disabled={!provider}
            loading={loadingModels[provider] || false}
            allowCustom={true}  // Allow custom model names
          />
        </div>
      </div>
    </div>
  );
}

export function AgentConfigStep() {
  const providers = useWizardStore((s) => s.providers);
  const agents = useWizardStore((s) => s.agents);
  const setupMode = useWizardStore((s) => s.setupMode);
  const setAgentConfig = useWizardStore((s) => s.setAgentConfig);
  const setAllAgentsConfig = useWizardStore((s) => s.setAllAgentsConfig);

  const availableProviders = providers.filter((p) => p.has_api_key);

  if (availableProviders.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="space-y-6"
      >
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-3">
            <AlertCircle className="w-6 h-6 text-amber-500" />
            <h3 className="text-lg font-semibold text-amber-700 dark:text-amber-400">
              No API Keys Found
            </h3>
          </div>
          <p className="text-sm text-amber-600 dark:text-amber-400 mb-4">
            Please set up API keys for at least one provider. You can do this by:
          </p>
          <ul className="text-sm text-amber-600 dark:text-amber-400 list-disc list-inside space-y-1">
            <li>Setting environment variables (e.g., OPENAI_API_KEY)</li>
            <li>Running <code className="bg-amber-100 dark:bg-amber-900/40 px-1 rounded">massgen --setup</code> in terminal</li>
            <li>Creating a <code className="bg-amber-100 dark:bg-amber-900/40 px-1 rounded">~/.massgen/.env</code> file</li>
          </ul>
        </div>
      </motion.div>
    );
  }

  // Same config for all agents
  if (setupMode === 'same' && agents.length > 1) {
    const firstAgent = agents[0] || { id: 'agent_a', provider: '', model: '' };

    return (
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="space-y-6"
      >
        <div>
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
            Configure All Agents
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            All {agents.length} agents will use the same configuration.
          </p>
        </div>

        <AgentConfigRow
          agentId="all_agents"
          provider={firstAgent.provider}
          model={firstAgent.model}
          providers={providers}
          onProviderChange={(provider) => {
            const providerInfo = providers.find((p) => p.id === provider);
            // For providers with dynamic model lists (like OpenRouter), don't set "custom" as default
            const defaultModel = providerInfo?.default_model === 'custom' ? '' : (providerInfo?.default_model || '');
            setAllAgentsConfig(provider, defaultModel);
          }}
          onModelChange={(model) => setAllAgentsConfig(firstAgent.provider, model)}
        />
      </motion.div>
    );
  }

  // Different config per agent
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
          Configure Each Agent
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Select a provider and model for each agent. Type to search or enter a custom model name.
        </p>
      </div>

      <div className="space-y-4">
        {agents.map((agent, index) => (
          <AgentConfigRow
            key={agent.id}
            agentId={agent.id}
            provider={agent.provider}
            model={agent.model}
            providers={providers}
            onProviderChange={(provider) => {
              const providerInfo = providers.find((p) => p.id === provider);
              // For providers with dynamic model lists (like OpenRouter), don't set "custom" as default
              const defaultModel = providerInfo?.default_model === 'custom' ? '' : (providerInfo?.default_model || '');
              setAgentConfig(index, provider, defaultModel);
            }}
            onModelChange={(model) => setAgentConfig(index, agent.provider, model)}
          />
        ))}
      </div>
    </motion.div>
  );
}
