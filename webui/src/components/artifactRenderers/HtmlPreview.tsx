/**
 * HTML Preview Component
 *
 * Renders static HTML content in a sandboxed iframe.
 * Two modes:
 * 1. srcDoc mode (default): Inlines CSS/JS, but relative links don't work
 * 2. Live preview mode: Uses /workspace-preview/ endpoint, relative links work
 */

import { useMemo } from 'react';
import { Globe } from 'lucide-react';

interface HtmlPreviewProps {
  content: string;
  fileName: string;
  relatedFiles?: Record<string, string>; // filename -> content mapping
  // Optional: Enable live preview with working relative links
  sessionId?: string;
  agentId?: string;
  filePath?: string; // Relative path within workspace (e.g., "index.html" or "pages/about.html")
  workspacePath?: string; // Absolute workspace path (needed for historical workspaces)
}

/**
 * Inline CSS, JS, and image files referenced in the HTML
 */
function inlineRelatedFiles(html: string, relatedFiles: Record<string, string>): string {
  let result = html;

  // Inline CSS files: <link rel="stylesheet" href="style.css"> -> <style>...</style>
  result = result.replace(
    /<link\s+[^>]*rel=["']stylesheet["'][^>]*href=["']([^"']+)["'][^>]*\/?>/gi,
    (match, href) => {
      const fileName = href.split('/').pop() || href;
      const cssContent = relatedFiles[fileName] || relatedFiles[href];
      if (cssContent && !cssContent.startsWith('data:')) {
        return `<style>/* Inlined from ${fileName} */\n${cssContent}</style>`;
      }
      return match; // Keep original if file not found
    }
  );

  // Also handle <link href="..." rel="stylesheet"> order
  result = result.replace(
    /<link\s+[^>]*href=["']([^"']+)["'][^>]*rel=["']stylesheet["'][^>]*\/?>/gi,
    (match, href) => {
      const fileName = href.split('/').pop() || href;
      const cssContent = relatedFiles[fileName] || relatedFiles[href];
      if (cssContent && !cssContent.startsWith('data:')) {
        return `<style>/* Inlined from ${fileName} */\n${cssContent}</style>`;
      }
      return match;
    }
  );

  // Inline JS files: <script src="script.js"></script> -> <script>...</script>
  result = result.replace(
    /<script\s+[^>]*src=["']([^"']+)["'][^>]*><\/script>/gi,
    (match, src) => {
      const fileName = src.split('/').pop() || src;
      const jsContent = relatedFiles[fileName] || relatedFiles[src];
      if (jsContent && !jsContent.startsWith('data:')) {
        return `<script>/* Inlined from ${fileName} */\n${jsContent}</script>`;
      }
      return match; // Keep original if file not found
    }
  );

  // Inline images: <img src="image.png"> -> <img src="data:image/png;base64,...">
  result = result.replace(
    /<img\s+([^>]*)src=["']([^"']+)["']([^>]*)>/gi,
    (match, before, src, after) => {
      // Skip if already a data URL or external URL
      if (src.startsWith('data:') || src.startsWith('http://') || src.startsWith('https://')) {
        return match;
      }
      const fileName = src.split('/').pop() || src;
      const imageDataUrl = relatedFiles[src] || relatedFiles[fileName] || relatedFiles[`./${src}`];
      if (imageDataUrl && imageDataUrl.startsWith('data:')) {
        return `<img ${before}src="${imageDataUrl}"${after}>`;
      }
      return match; // Keep original if file not found
    }
  );

  // Also handle CSS background-image: url() references
  result = result.replace(
    /url\(["']?([^"')]+)["']?\)/gi,
    (match, url) => {
      // Skip if already a data URL or external URL
      if (url.startsWith('data:') || url.startsWith('http://') || url.startsWith('https://')) {
        return match;
      }
      const fileName = url.split('/').pop() || url;
      const imageDataUrl = relatedFiles[url] || relatedFiles[fileName] || relatedFiles[`./${url}`];
      if (imageDataUrl && imageDataUrl.startsWith('data:')) {
        return `url("${imageDataUrl}")`;
      }
      return match;
    }
  );

  return result;
}

export function HtmlPreview({
  content,
  fileName,
  relatedFiles = {},
  sessionId,
  agentId,
  filePath,
  workspacePath,
}: HtmlPreviewProps) {
  // Determine if we should use live preview mode (with working relative links)
  const useLivePreview = Boolean(sessionId && agentId && filePath);

  // Build the live preview URL
  const livePreviewUrl = useMemo(() => {
    if (!useLivePreview) return null;
    // Include workspace query param for historical workspaces
    const baseUrl = `/workspace-preview/${sessionId}/${agentId}/${filePath}`;
    if (workspacePath) {
      return `${baseUrl}?workspace=${encodeURIComponent(workspacePath)}`;
    }
    return baseUrl;
  }, [useLivePreview, sessionId, agentId, filePath, workspacePath]);

  // Prepare the HTML content with inlined CSS/JS (only used in srcDoc mode)
  const preparedContent = useMemo(() => {
    if (useLivePreview) return ''; // Not needed for live preview

    let processedContent = content;

    // Inline related CSS and JS files
    if (Object.keys(relatedFiles).length > 0) {
      processedContent = inlineRelatedFiles(processedContent, relatedFiles);
    }

    // If content already has full HTML structure, use as-is
    if (processedContent.includes('<html') || processedContent.includes('<!DOCTYPE')) {
      return processedContent;
    }

    // Wrap partial HTML in a basic document structure
    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      padding: 16px;
      margin: 0;
    }
  </style>
</head>
<body>
${processedContent}
</body>
</html>`;
  }, [content, relatedFiles, useLivePreview]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-amber-900/30 border-b border-amber-700/50">
        <Globe className="w-4 h-4 text-amber-400" />
        <span className="text-sm text-amber-300">HTML Preview</span>
        <span className="text-xs text-amber-500">- {fileName}</span>
        {useLivePreview && (
          <span className="text-xs text-green-500 ml-auto">(Live - links work)</span>
        )}
      </div>

      {/* Preview iframe - use src for live preview, srcDoc for inline */}
      {useLivePreview ? (
        <iframe
          src={livePreviewUrl!}
          sandbox="allow-scripts allow-same-origin"
          title={`Preview: ${fileName}`}
          className="flex-1 w-full bg-white rounded-b-lg border-0"
          style={{ minHeight: '400px' }}
        />
      ) : (
        <iframe
          srcDoc={preparedContent}
          sandbox="allow-scripts"
          title={`Preview: ${fileName}`}
          className="flex-1 w-full bg-white rounded-b-lg border-0"
          style={{ minHeight: '400px' }}
        />
      )}
    </div>
  );
}

export default HtmlPreview;
