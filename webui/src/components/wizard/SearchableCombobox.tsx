/**
 * Searchable Combobox Component
 *
 * An input with autocomplete suggestions. Always accepts typed values.
 */

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Loader2 } from 'lucide-react';

interface Option {
  value: string;
  label: string;
  disabled?: boolean;
  group?: string;
}

interface SearchableComboboxProps {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  /** If true, any typed value is accepted. If false, only values from options list are accepted. Default: true */
  allowCustom?: boolean;
}

export function SearchableCombobox({
  options,
  value,
  onChange,
  placeholder = 'Type or select...',
  disabled = false,
  loading = false,
  allowCustom = true,
}: SearchableComboboxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value);
  const [isUserTyping, setIsUserTyping] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync input value with prop value
  useEffect(() => {
    setInputValue(value);
    setIsUserTyping(false);
  }, [value]);

  // Filter options based on input - only filter if user is actively typing something different
  // When dropdown opens with existing selection, show all options
  const shouldFilter = isUserTyping && inputValue.trim() && inputValue !== value;
  const filteredOptions = shouldFilter
    ? options.filter(
        (opt) =>
          !opt.disabled &&
          (opt.label.toLowerCase().includes(inputValue.toLowerCase()) ||
           opt.value.toLowerCase().includes(inputValue.toLowerCase()))
      )
    : options.filter((opt) => !opt.disabled);

  // Limit displayed options for performance
  const displayedOptions = filteredOptions.slice(0, 100);

  // Handle input change - update local state, only notify parent if allowCustom
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    setIsUserTyping(true);
    // Only propagate value to parent if custom values are allowed
    if (allowCustom) {
      onChange(newValue);
    }
    if (!isOpen) setIsOpen(true);
  };

  // Handle option click
  const handleOptionClick = (optionValue: string) => {
    setInputValue(optionValue);
    setIsUserTyping(false);
    onChange(optionValue);
    setIsOpen(false);
    inputRef.current?.blur();
  };

  // Handle blur - close dropdown after delay (mousedown with preventDefault handles clicks)
  const handleBlur = () => {
    setTimeout(() => {
      setIsOpen(false);
    }, 150);
  };

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      inputRef.current?.blur();
    } else if (e.key === 'Enter') {
      setIsOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      {/* Input */}
      <div
        className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border
                   ${disabled ? 'bg-gray-100 dark:bg-gray-800 cursor-not-allowed' : 'bg-white dark:bg-gray-700'}
                   ${isOpen ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-gray-300 dark:border-gray-600'}
                   transition-all`}
      >
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onFocus={() => setIsOpen(true)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 bg-transparent outline-none text-gray-800 dark:text-gray-200
                     placeholder-gray-500 text-sm min-w-0"
        />
        {loading ? (
          <Loader2 className="w-4 h-4 text-gray-400 animate-spin flex-shrink-0" />
        ) : (
          <ChevronDown
            className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform cursor-pointer
                       ${isOpen ? 'rotate-180' : ''}`}
            onClick={() => {
              if (!disabled) {
                setIsOpen(!isOpen);
                if (!isOpen) inputRef.current?.focus();
              }
            }}
          />
        )}
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="absolute z-[100] w-full mt-1 max-h-[400px] overflow-auto
                     bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                     rounded-lg shadow-2xl"
        >
          {loading ? (
            <div className="px-3 py-4 text-sm text-gray-500 text-center flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading models...
            </div>
          ) : displayedOptions.length > 0 ? (
            <>
              {displayedOptions.map((option) => {
                const isSelected = option.value === value;

                return (
                  <div
                    key={option.value}
                    onMouseDown={(e) => {
                      e.preventDefault(); // Prevent blur
                      handleOptionClick(option.value);
                    }}
                    className={`w-full px-3 py-2.5 text-left text-sm flex items-center gap-2 cursor-pointer
                               text-gray-800 dark:text-gray-200
                               ${isSelected ? 'bg-blue-50 dark:bg-blue-900/30' : 'hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                  >
                    <span className="flex-1 truncate">{option.label}</span>
                    {isSelected && <Check className="w-4 h-4 text-blue-500 flex-shrink-0" />}
                  </div>
                );
              })}
              {filteredOptions.length > 100 && (
                <div className="px-3 py-2 text-xs text-gray-500 border-t border-gray-200 dark:border-gray-700">
                  Showing 100 of {filteredOptions.length} results. Type to filter.
                </div>
              )}
            </>
          ) : (
            <div className="px-3 py-3 text-sm text-gray-500 text-center">
              {inputValue.trim() ? `No matches for "${inputValue}"` : 'Type to search or enter a model name'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
