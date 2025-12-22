/**
 * SVG Preview Component
 *
 * Renders SVG content in a sandboxed iframe with no script execution.
 */

import { useMemo } from 'react';
import { Palette } from 'lucide-react';

interface SvgPreviewProps {
  content: string;
  fileName: string;
}

export function SvgPreview({ content, fileName }: SvgPreviewProps) {
  // Wrap SVG in a minimal HTML document for proper rendering
  const htmlContent = useMemo(() => {
    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    html, body {
      margin: 0;
      padding: 0;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #1a1b26;
    }
    svg {
      max-width: 100%;
      max-height: 100%;
    }
  </style>
</head>
<body>
${content}
</body>
</html>`;
  }, [content]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-purple-900/30 border-b border-purple-700/50">
        <Palette className="w-4 h-4 text-purple-400" />
        <span className="text-sm text-purple-300">SVG Preview</span>
        <span className="text-xs text-purple-500">- {fileName}</span>
      </div>

      {/* Preview iframe - no scripts allowed for SVG */}
      <iframe
        srcDoc={htmlContent}
        sandbox=""
        title={`SVG: ${fileName}`}
        className="flex-1 w-full border-0"
        style={{ minHeight: '300px' }}
      />
    </div>
  );
}

export default SvgPreview;
