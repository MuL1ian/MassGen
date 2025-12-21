/**
 * Mermaid Preview Component
 *
 * Renders Mermaid diagrams (flowcharts, sequence diagrams, etc.)
 */

import { useEffect, useRef, useState } from 'react';
import { GitBranch, AlertCircle, Loader2 } from 'lucide-react';
import mermaid from 'mermaid';

interface MermaidPreviewProps {
  content: string;
  fileName: string;
}

// Initialize mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#7dcfff',
    primaryTextColor: '#c0caf5',
    primaryBorderColor: '#3b4261',
    lineColor: '#7dcfff',
    secondaryColor: '#bb9af7',
    tertiaryColor: '#292e42',
    background: '#1a1b26',
    mainBkg: '#292e42',
    nodeBorder: '#3b4261',
    clusterBkg: '#24283b',
    titleColor: '#c0caf5',
    edgeLabelBackground: '#24283b',
  },
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
});

export function MermaidPreview({ content, fileName }: MermaidPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function renderDiagram() {
      if (!containerRef.current) return;

      setIsLoading(true);
      setError(null);

      try {
        // Clear previous content
        containerRef.current.innerHTML = '';

        // Generate unique ID for this diagram
        const id = `mermaid-${Date.now()}`;

        // Render the diagram
        const { svg } = await mermaid.render(id, content);

        // Insert the rendered SVG
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        console.error('Mermaid rendering error:', err);
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      } finally {
        setIsLoading(false);
      }
    }

    renderDiagram();
  }, [content]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-cyan-900/30 border-b border-cyan-700/50">
        <GitBranch className="w-4 h-4 text-cyan-400" />
        <span className="text-sm text-cyan-300">Mermaid Diagram</span>
        <span className="text-xs text-cyan-500">- {fileName}</span>
      </div>

      {/* Diagram container */}
      <div className="flex-1 overflow-auto bg-gray-900 flex items-center justify-center p-4">
        {isLoading && (
          <div className="flex flex-col items-center gap-2 text-gray-400">
            <Loader2 className="w-8 h-8 animate-spin" />
            <span>Rendering diagram...</span>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center gap-2 text-red-400 max-w-md text-center">
            <AlertCircle className="w-8 h-8" />
            <span className="font-medium">Failed to render diagram</span>
            <span className="text-sm text-gray-500">{error}</span>
            <pre className="mt-4 p-4 bg-gray-800 rounded text-xs text-gray-400 overflow-auto max-w-full">
              {content}
            </pre>
          </div>
        )}

        <div
          ref={containerRef}
          className={`mermaid-container ${isLoading || error ? 'hidden' : ''}`}
          style={{ minHeight: '200px' }}
        />
      </div>
    </div>
  );
}

export default MermaidPreview;
