/**
 * Path Normalization Utility for Workspace Browser
 *
 * Ensures consistent path format across HTTP API and WebSocket data sources.
 * This fixes the path mismatch bug where:
 * - HTTP API returns: "/path/to/workspace"
 * - WebSocket stores: "/path/to/workspace/" (trailing slash)
 *
 * By normalizing all paths, lookups work correctly.
 */

/**
 * Normalize a workspace path for consistent storage and lookup.
 *
 * Handles:
 * - Trailing slashes: "/path/to/workspace/" → "/path/to/workspace"
 * - Multiple slashes: "/path//to///workspace" → "/path/to/workspace"
 * - Empty paths: returns empty string
 * - Preserves leading slash for absolute paths
 *
 * @param path - The path to normalize
 * @returns The normalized path
 */
export function normalizePath(path: string): string {
  if (!path) return '';

  // Remove trailing slashes (but keep single leading slash)
  let normalized = path.replace(/\/+$/, '');

  // Collapse multiple consecutive slashes into single slash
  normalized = normalized.replace(/\/+/g, '/');

  return normalized;
}

/**
 * Check if two paths are equivalent after normalization.
 *
 * @param path1 - First path to compare
 * @param path2 - Second path to compare
 * @returns True if paths are equivalent
 */
export function pathsEqual(path1: string, path2: string): boolean {
  return normalizePath(path1) === normalizePath(path2);
}

/**
 * Debug helper to log path comparison.
 * Use this to diagnose path mismatch issues.
 *
 * @param context - Description of where the comparison is happening
 * @param path1 - First path (e.g., from HTTP API)
 * @param path2 - Second path (e.g., from WebSocket store)
 */
export function debugPathComparison(
  context: string,
  path1: string,
  path2: string
): void {
  const norm1 = normalizePath(path1);
  const norm2 = normalizePath(path2);
  const match = norm1 === norm2;

  if (import.meta.env.DEV) {
    console.log(`[Path:${context}] Comparison:`, {
      original1: path1,
      original2: path2,
      normalized1: norm1,
      normalized2: norm2,
      match,
    });
  }
}
