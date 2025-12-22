/**
 * Sandpack Preview Component
 *
 * Renders React/Vue/TypeScript components using CodeSandbox's Sandpack.
 * Provides a full bundled preview with live updates.
 */

import { useMemo } from 'react';
import {
  SandpackProvider,
  SandpackLayout,
  SandpackPreview as SandpackPreviewPane,
  SandpackCodeEditor,
} from '@codesandbox/sandpack-react';
import { atomDark } from '@codesandbox/sandpack-themes';
import { Code2 } from 'lucide-react';

interface SandpackPreviewProps {
  content: string;
  fileName: string;
  files?: Record<string, string>; // Additional files for multi-file projects
}

type SandpackTemplate = 'react' | 'react-ts' | 'vue' | 'vue-ts' | 'vanilla' | 'vanilla-ts';

export function SandpackPreview({ content, fileName, files = {} }: SandpackPreviewProps) {
  // Determine the template based on file extension
  const template = useMemo((): SandpackTemplate => {
    const ext = fileName.split('.').pop()?.toLowerCase();

    switch (ext) {
      case 'tsx':
        return 'react-ts';
      case 'jsx':
        return 'react';
      case 'vue':
        return 'vue';
      default:
        return 'react';
    }
  }, [fileName]);

  // Prepare files for Sandpack
  const sandpackFiles = useMemo(() => {
    const result: Record<string, string> = {};

    // Add the main file
    const mainPath = fileName.startsWith('/') ? fileName : `/${fileName}`;
    result[mainPath] = content;

    // Add additional files
    Object.entries(files).forEach(([path, fileContent]) => {
      const normalizedPath = path.startsWith('/') ? path : `/${path}`;
      result[normalizedPath] = fileContent;
    });

    // If this is a React component without App.tsx, wrap it
    if (template.startsWith('react') && !result['/App.tsx'] && !result['/App.jsx']) {
      const ext = template === 'react-ts' ? 'tsx' : 'jsx';

      // Check if the content exports a default component
      if (content.includes('export default') || content.includes('export function')) {
        result[`/App.${ext}`] = `
import Component from '${mainPath.replace(/\.(tsx|jsx)$/, '')}';

export default function App() {
  return <Component />;
}
`;
      }
    }

    return result;
  }, [content, fileName, files, template]);

  // Determine entry file
  const entryFile = useMemo(() => {
    if (sandpackFiles['/App.tsx']) return '/App.tsx';
    if (sandpackFiles['/App.jsx']) return '/App.jsx';
    if (sandpackFiles['/App.vue']) return '/App.vue';
    return fileName.startsWith('/') ? fileName : `/${fileName}`;
  }, [sandpackFiles, fileName]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-violet-900/30 border-b border-violet-700/50">
        <Code2 className="w-4 h-4 text-violet-400" />
        <span className="text-sm text-violet-300">
          {template.includes('react') ? 'React' : template.includes('vue') ? 'Vue' : 'JavaScript'} Preview
        </span>
        <span className="text-xs text-violet-500">- {fileName}</span>
      </div>

      {/* Sandpack */}
      <div className="flex-1 overflow-hidden">
        <SandpackProvider
          template={template}
          files={sandpackFiles}
          theme={atomDark}
          options={{
            activeFile: entryFile,
            visibleFiles: Object.keys(sandpackFiles),
            recompileMode: 'delayed',
            recompileDelay: 500,
          }}
        >
          <SandpackLayout style={{ height: '100%', border: 'none' }}>
            <SandpackCodeEditor
              showTabs
              showLineNumbers
              showInlineErrors
              wrapContent
              style={{ height: '100%', minWidth: '40%' }}
            />
            <SandpackPreviewPane
              showNavigator={false}
              showRefreshButton
              style={{ height: '100%', minWidth: '60%' }}
            />
          </SandpackLayout>
        </SandpackProvider>
      </div>
    </div>
  );
}

export default SandpackPreview;
