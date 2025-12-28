/**
 * Coordination Step Component
 *
 * Optional step - configure coordination settings shared across all agents.
 * Settings: voting sensitivity, answer novelty requirement, subagents.
 */

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Settings, Vote, Sparkles, Info, ListOrdered, GitBranch, Cpu, Plus, Trash2, Users } from 'lucide-react';
import { useWizardStore } from '../../stores/wizardStore';
import { SearchableCombobox } from './SearchableCombobox';

type SensitivityLevel = 'lenient' | 'balanced' | 'strict';

interface SettingOption {
  value: SensitivityLevel;
  label: string;
  description: string;
}

const votingSensitivityOptions: SettingOption[] = [
  {
    value: 'lenient',
    label: 'Lenient',
    description: 'Agents accept answers more easily',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    description: 'Moderate scrutiny of answers',
  },
  {
    value: 'strict',
    label: 'Strict',
    description: 'Agents are highly critical',
  },
];

const answerNoveltyOptions: SettingOption[] = [
  {
    value: 'lenient',
    label: 'Lenient',
    description: 'Similar answers are accepted',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    description: 'Some differentiation required',
  },
  {
    value: 'strict',
    label: 'Strict',
    description: 'Answers must be substantially different',
  },
];

interface SelectDropdownProps {
  label: string;
  description: string;
  icon: React.ReactNode;
  value: SensitivityLevel;
  options: SettingOption[];
  onChange: (value: SensitivityLevel) => void;
}

function SelectDropdown({ label, description, icon, value, options, onChange }: SelectDropdownProps) {
  return (
    <div className="p-5 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
          {icon}
        </div>
        <div className="flex-1">
          <h3 className="font-medium text-gray-800 dark:text-gray-200">{label}</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{description}</p>
        </div>
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as SensitivityLevel)}
        className="w-full px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600
                   rounded-lg text-gray-800 dark:text-gray-200 text-sm
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   cursor-pointer"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label} - {option.description}
          </option>
        ))}
      </select>
    </div>
  );
}

export function CoordinationStep() {
  const coordinationSettings = useWizardStore((s) => s.coordinationSettings);
  const setCoordinationSettings = useWizardStore((s) => s.setCoordinationSettings);
  const agentCount = useWizardStore((s) => s.agentCount);
  const providers = useWizardStore((s) => s.providers);
  const dynamicModels = useWizardStore((s) => s.dynamicModels);
  const loadingModels = useWizardStore((s) => s.loadingModels);
  const fetchDynamicModels = useWizardStore((s) => s.fetchDynamicModels);

  // Get subagent configs from orchestrator
  const subagentConfigs = coordinationSettings.subagent_orchestrator?.agents || [];

  // Fetch models for all providers used in subagent configs
  useEffect(() => {
    if (coordinationSettings.subagent_model_choice === 'custom') {
      subagentConfigs.forEach(config => {
        if (config.backend.type) {
          fetchDynamicModels(config.backend.type);
        }
      });
    }
  }, [subagentConfigs, coordinationSettings.subagent_model_choice, fetchDynamicModels]);

  const handleVotingSensitivityChange = (value: SensitivityLevel) => {
    setCoordinationSettings({ voting_sensitivity: value });
  };

  const handleAnswerNoveltyChange = (value: SensitivityLevel) => {
    setCoordinationSettings({ answer_novelty_requirement: value });
  };

  const handleMaxAnswersChange = (value: string) => {
    const num = parseInt(value, 10);
    setCoordinationSettings({ max_new_answers_per_agent: isNaN(num) || num <= 0 ? undefined : num });
  };

  const handleSubagentsChange = (enabled: boolean) => {
    setCoordinationSettings({
      enable_subagents: enabled,
      // Reset subagent model choice when disabling
      ...(enabled ? {} : { subagent_model_choice: undefined, subagent_orchestrator: undefined })
    });
  };

  const handlePersonaGeneratorChange = (enabled: boolean) => {
    setCoordinationSettings({
      persona_generator: enabled ? { enabled: true, diversity_mode: 'perspective' } : undefined
    });
  };

  const handleDiversityModeChange = (mode: 'perspective' | 'implementation') => {
    setCoordinationSettings({
      persona_generator: {
        enabled: true,
        diversity_mode: mode
      }
    });
  };

  const handleSubagentModelChoiceChange = (choice: 'inherit' | 'custom') => {
    if (choice === 'custom' && subagentConfigs.length === 0) {
      // Initialize with one empty config
      setCoordinationSettings({
        subagent_model_choice: choice,
        subagent_orchestrator: {
          enabled: true,
          agents: [{ backend: { type: '', model: '' } }]
        }
      });
    } else {
      setCoordinationSettings({
        subagent_model_choice: choice,
        // Clear orchestrator config when switching to inherit
        ...(choice === 'inherit' ? { subagent_orchestrator: undefined } : {})
      });
    }
  };

  const handleAddSubagent = () => {
    const newConfigs = [...subagentConfigs, { backend: { type: '', model: '' } }];
    setCoordinationSettings({
      subagent_orchestrator: {
        enabled: true,
        agents: newConfigs
      }
    });
  };

  const handleRemoveSubagent = (index: number) => {
    const newConfigs = subagentConfigs.filter((_, i) => i !== index);
    if (newConfigs.length === 0) {
      // If removing last one, add an empty one
      newConfigs.push({ backend: { type: '', model: '' } });
    }
    setCoordinationSettings({
      subagent_orchestrator: {
        enabled: true,
        agents: newConfigs
      }
    });
  };

  const handleSubagentProviderChange = (index: number, providerId: string) => {
    const providerInfo = providers.find(p => p.id === providerId);
    const newConfigs = [...subagentConfigs];
    newConfigs[index] = {
      backend: {
        type: providerId,
        model: providerInfo?.default_model || '',
      }
    };
    setCoordinationSettings({
      subagent_orchestrator: {
        enabled: true,
        agents: newConfigs
      }
    });
  };

  const handleSubagentModelChange = (index: number, model: string) => {
    const newConfigs = [...subagentConfigs];
    newConfigs[index] = {
      backend: {
        ...newConfigs[index].backend,
        model: model,
      }
    };
    setCoordinationSettings({
      subagent_orchestrator: {
        enabled: true,
        agents: newConfigs
      }
    });
  };

  // Helper to get models for a specific provider
  const getModelsForProvider = (providerId: string) => dynamicModels[providerId] || [];
  const isLoadingModelsForProvider = (providerId: string) => loadingModels[providerId] || false;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Settings className="w-5 h-5 text-blue-500" />
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
            Coordination Settings
          </h2>
          <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full">
            Optional
          </span>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure how your {agentCount} agents coordinate and evaluate answers.
          These settings affect all agents.
        </p>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-700 dark:text-blue-300">
          <strong>Tip:</strong> Start with "Lenient" settings for faster consensus.
          Use "Strict" settings when you need more thorough deliberation.
        </div>
      </div>

      {/* Settings */}
      <div className="space-y-4">
        <SelectDropdown
          label="Voting Sensitivity"
          description="How critical are agents when voting on proposed answers?"
          icon={<Vote className="w-5 h-5 text-blue-500" />}
          value={coordinationSettings.voting_sensitivity}
          options={votingSensitivityOptions}
          onChange={handleVotingSensitivityChange}
        />

        <SelectDropdown
          label="Answer Novelty Requirement"
          description="How different must new answers be from existing proposals?"
          icon={<Sparkles className="w-5 h-5 text-blue-500" />}
          value={coordinationSettings.answer_novelty_requirement}
          options={answerNoveltyOptions}
          onChange={handleAnswerNoveltyChange}
        />

        {/* Max answers per agent */}
        <div className="p-5 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-start gap-3 mb-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <ListOrdered className="w-5 h-5 text-blue-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-gray-800 dark:text-gray-200">Max Answers per Agent</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Limit how many answers each agent can provide (leave empty for unlimited)
              </p>
            </div>
          </div>
          <input
            type="number"
            min="1"
            placeholder="Unlimited"
            value={coordinationSettings.max_new_answers_per_agent ?? ''}
            onChange={(e) => handleMaxAnswersChange(e.target.value)}
            className="w-full px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600
                       rounded-lg text-gray-800 dark:text-gray-200 text-sm
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       placeholder-gray-400"
          />
        </div>

        {/* Enable subagents */}
        <div className="p-5 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <GitBranch className="w-5 h-5 text-blue-500" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-800 dark:text-gray-200">Enable Subagents</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                    Allow agents to spawn parallel child processes for independent tasks
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={coordinationSettings.enable_subagents ?? false}
                    onChange={(e) => handleSubagentsChange(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4
                                  peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer
                                  dark:bg-gray-700 peer-checked:after:translate-x-full
                                  peer-checked:after:border-white after:content-[''] after:absolute
                                  after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300
                                  after:border after:rounded-full after:h-5 after:w-5 after:transition-all
                                  dark:border-gray-600 peer-checked:bg-blue-600"></div>
                </label>
              </div>

              {/* Subagent model selection - shown when subagents are enabled */}
              {coordinationSettings.enable_subagents && (
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-4">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      Choose which model subagents should use:
                    </p>
                    <div className="flex gap-3">
                      <button
                        type="button"
                        onClick={() => handleSubagentModelChoiceChange('inherit')}
                        className={`flex-1 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors
                          ${coordinationSettings.subagent_model_choice !== 'custom'
                            ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300'
                            : 'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                          }`}
                      >
                        Same as parent agents
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSubagentModelChoiceChange('custom')}
                        className={`flex-1 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors
                          ${coordinationSettings.subagent_model_choice === 'custom'
                            ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300'
                            : 'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                          }`}
                      >
                        Choose different model
                      </button>
                    </div>
                  </div>

                  {/* Custom model selection */}
                  {coordinationSettings.subagent_model_choice === 'custom' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Cpu className="w-4 h-4 text-blue-500" />
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Subagent Backends ({subagentConfigs.length})
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={handleAddSubagent}
                          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-600 dark:text-blue-400
                                     hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded transition-colors"
                        >
                          <Plus className="w-3 h-3" />
                          Add Agent
                        </button>
                      </div>

                      {/* List of subagent configs */}
                      {subagentConfigs.map((config, index) => (
                        <div key={index} className="p-4 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
                          <div className="flex items-center justify-between mb-3">
                            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                              Subagent {index + 1}
                            </span>
                            {subagentConfigs.length > 1 && (
                              <button
                                type="button"
                                onClick={() => handleRemoveSubagent(index)}
                                className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors"
                                title="Remove this subagent"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>

                          <div className="space-y-3">
                            {/* Provider selection */}
                            <div>
                              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Provider</label>
                              <select
                                value={config.backend.type}
                                onChange={(e) => handleSubagentProviderChange(index, e.target.value)}
                                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600
                                           rounded-lg text-gray-800 dark:text-gray-200 text-sm
                                           focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="">Select provider...</option>
                                {providers.filter(p => p.has_api_key).map((provider) => (
                                  <option key={provider.id} value={provider.id}>
                                    {provider.name}
                                  </option>
                                ))}
                              </select>
                            </div>

                            {/* Model selection */}
                            {config.backend.type && (
                              <div>
                                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Model</label>
                                {isLoadingModelsForProvider(config.backend.type) ? (
                                  <div className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-500">
                                    Loading models...
                                  </div>
                                ) : (
                                  <SearchableCombobox
                                    options={getModelsForProvider(config.backend.type).map(m => ({ value: m, label: m }))}
                                    value={config.backend.model}
                                    onChange={(model) => handleSubagentModelChange(index, model)}
                                    placeholder="Select or type model..."
                                  />
                                )}
                              </div>
                            )}

                            {config.backend.type && config.backend.model && (
                              <div className="text-xs text-green-600 dark:text-green-400">
                                ✓ {config.backend.model}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}

                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Each subagent spawned will use one of these configurations. Add multiple to have diverse subagent models.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Enable persona generation - only show for multi-agent */}
        {agentCount > 1 && (
          <div className="p-5 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Users className="w-5 h-5 text-blue-500" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-800 dark:text-gray-200">Persona Generation</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                      Auto-generate diverse approaches for each agent to explore different regions of the solution space
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={coordinationSettings.persona_generator?.enabled ?? false}
                      onChange={(e) => handlePersonaGeneratorChange(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4
                                    peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer
                                    dark:bg-gray-700 peer-checked:after:translate-x-full
                                    peer-checked:after:border-white after:content-[''] after:absolute
                                    after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300
                                    after:border after:rounded-full after:h-5 after:w-5 after:transition-all
                                    dark:border-gray-600 peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                {/* Diversity mode selector - show when persona generation is enabled */}
                {coordinationSettings.persona_generator?.enabled && (
                  <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Diversity Mode
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => handleDiversityModeChange('perspective')}
                        className={`p-3 rounded-lg border text-left transition-all ${
                          (coordinationSettings.persona_generator?.diversity_mode ?? 'perspective') === 'perspective'
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }`}
                      >
                        <div className="font-medium text-gray-800 dark:text-gray-200 text-sm">Perspective</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Different values & priorities (e.g., simplicity vs robustness)
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDiversityModeChange('implementation')}
                        className={`p-3 rounded-lg border text-left transition-all ${
                          coordinationSettings.persona_generator?.diversity_mode === 'implementation'
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }`}
                      >
                        <div className="font-medium text-gray-800 dark:text-gray-200 text-sm">Implementation</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Different solution types (e.g., minimal vs feature-rich)
                        </div>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Current settings summary */}
      <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
        <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-300">Current settings: </span>
            Voting is <span className="font-medium text-blue-600 dark:text-blue-400">{coordinationSettings.voting_sensitivity}</span>,
            answer novelty is <span className="font-medium text-blue-600 dark:text-blue-400">{coordinationSettings.answer_novelty_requirement}</span>.
          </div>
          <div>
            Max answers: <span className="font-medium text-blue-600 dark:text-blue-400">
              {coordinationSettings.max_new_answers_per_agent ?? 'unlimited'}
            </span>.
            Subagents: <span className="font-medium text-blue-600 dark:text-blue-400">
              {coordinationSettings.enable_subagents
                ? coordinationSettings.subagent_model_choice === 'custom' && subagentConfigs.length > 0
                  ? `enabled (${subagentConfigs.length} custom backend${subagentConfigs.length > 1 ? 's' : ''})`
                  : 'enabled (inherit parent)'
                : 'disabled'}
            </span>.
            {agentCount > 1 && (
              <>
                {' '}Personas: <span className="font-medium text-blue-600 dark:text-blue-400">
                  {coordinationSettings.persona_generator?.enabled
                    ? `enabled (${coordinationSettings.persona_generator?.diversity_mode ?? 'perspective'})`
                    : 'disabled'}
                </span>.
              </>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
