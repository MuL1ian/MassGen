/**
 * Coordination Step Component
 *
 * Optional step - configure coordination settings shared across all agents.
 * Settings: voting sensitivity, answer novelty requirement.
 */

import { motion } from 'framer-motion';
import { Settings, Vote, Sparkles, Info, ListOrdered } from 'lucide-react';
import { useWizardStore } from '../../stores/wizardStore';

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
          </div>
        </div>
      </div>
    </motion.div>
  );
}
