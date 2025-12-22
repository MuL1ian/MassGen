/**
 * Markdown Preview Component
 *
 * Renders Markdown content as HTML using the marked library.
 */

import { useMemo } from 'react';
import { FileText } from 'lucide-react';
import { marked } from 'marked';

interface MarkdownPreviewProps {
  content: string;
  fileName: string;
}

export function MarkdownPreview({ content, fileName }: MarkdownPreviewProps) {
  // Convert markdown to HTML
  const htmlContent = useMemo(() => {
    // Configure marked for safety
    marked.setOptions({
      gfm: true, // GitHub Flavored Markdown
      breaks: true, // Convert line breaks to <br>
    });

    try {
      const renderedMarkdown = marked.parse(content);
      return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      line-height: 1.6;
      color: #c0caf5;
      background: #1a1b26;
      padding: 24px;
      margin: 0;
      max-width: 100%;
      overflow-x: hidden;
    }
    h1, h2, h3, h4, h5, h6 {
      color: #7dcfff;
      margin-top: 24px;
      margin-bottom: 16px;
      font-weight: 600;
    }
    h1 { font-size: 2em; border-bottom: 1px solid #3b4261; padding-bottom: 0.3em; }
    h2 { font-size: 1.5em; border-bottom: 1px solid #3b4261; padding-bottom: 0.3em; }
    h3 { font-size: 1.25em; }
    p { margin: 16px 0; }
    a { color: #7dcfff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    code {
      background: #292e42;
      padding: 0.2em 0.4em;
      border-radius: 4px;
      font-family: 'SF Mono', Monaco, monospace;
      font-size: 0.9em;
    }
    pre {
      background: #292e42;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
    }
    pre code {
      background: none;
      padding: 0;
    }
    blockquote {
      border-left: 4px solid #7dcfff;
      margin: 16px 0;
      padding-left: 16px;
      color: #a9b1d6;
    }
    ul, ol {
      padding-left: 24px;
      margin: 16px 0;
    }
    li { margin: 8px 0; }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 16px 0;
    }
    th, td {
      border: 1px solid #3b4261;
      padding: 8px 12px;
      text-align: left;
    }
    th {
      background: #292e42;
      font-weight: 600;
    }
    img {
      max-width: 100%;
      border-radius: 8px;
    }
    hr {
      border: none;
      border-top: 1px solid #3b4261;
      margin: 24px 0;
    }
    .task-list-item {
      list-style: none;
      margin-left: -20px;
    }
    .task-list-item input {
      margin-right: 8px;
    }
  </style>
</head>
<body>
${renderedMarkdown}
</body>
</html>`;
    } catch (error) {
      console.error('Markdown parsing error:', error);
      return `<html><body><pre>${content}</pre></body></html>`;
    }
  }, [content]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-blue-900/30 border-b border-blue-700/50">
        <FileText className="w-4 h-4 text-blue-400" />
        <span className="text-sm text-blue-300">Markdown Preview</span>
        <span className="text-xs text-blue-500">- {fileName}</span>
      </div>

      {/* Preview iframe */}
      <iframe
        srcDoc={htmlContent}
        sandbox=""
        title={`Markdown: ${fileName}`}
        className="flex-1 w-full border-0"
        style={{ minHeight: '400px' }}
      />
    </div>
  );
}

export default MarkdownPreview;
