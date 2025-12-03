/**
 * useFileContent Hook
 *
 * Fetches and caches file content from workspace for viewing.
 */

import { useState, useCallback } from 'react';
import type { FileContentResponse } from '../types';

interface UseFileContentReturn {
  content: FileContentResponse | null;
  isLoading: boolean;
  error: string | null;
  fetchFile: (filePath: string, workspacePath: string) => Promise<void>;
  clearContent: () => void;
}

// Simple in-memory cache for file contents
const fileCache = new Map<string, FileContentResponse>();

export function useFileContent(): UseFileContentReturn {
  const [content, setContent] = useState<FileContentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFile = useCallback(async (filePath: string, workspacePath: string) => {
    const cacheKey = `${workspacePath}:${filePath}`;

    // Check cache first
    const cached = fileCache.get(cacheKey);
    if (cached) {
      setContent(cached);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        path: filePath,
        workspace: workspacePath,
      });

      const response = await fetch(`/api/workspace/file?${params}`);
      const data: FileContentResponse = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch file');
      }

      // Cache the result
      fileCache.set(cacheKey, data);

      setContent(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load file');
      setContent(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearContent = useCallback(() => {
    setContent(null);
    setError(null);
  }, []);

  return {
    content,
    isLoading,
    error,
    fetchFile,
    clearContent,
  };
}

// Clear cache (useful for testing or when workspaces change)
export function clearFileCache(): void {
  fileCache.clear();
}
