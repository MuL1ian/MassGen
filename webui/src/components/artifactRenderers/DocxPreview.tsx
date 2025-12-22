/**
 * DOCX Preview Component
 *
 * Renders Word documents by:
 * 1. Attempting Docker-based PDF conversion for full fidelity (if available)
 * 2. Falling back to HTML conversion using mammoth.js
 */

import { useEffect, useState } from 'react';
import { FileText, AlertCircle, Loader2, FileImage } from 'lucide-react';
import mammoth from 'mammoth';
import PdfPreview from './PdfPreview';

interface DocxPreviewProps {
  content: string; // Base64 encoded DOCX data
  fileName: string;
  // Optional: workspace context for Docker conversion
  workspacePath?: string;
  filePath?: string;
}

type PreviewMode = 'auto' | 'pdf' | 'html';

export function DocxPreview({ content, fileName, workspacePath, filePath }: DocxPreviewProps) {
  const [htmlContent, setHtmlContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [previewMode, setPreviewMode] = useState<PreviewMode>('auto');

  // PDF conversion state
  const [pdfContent, setPdfContent] = useState<string | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [dockerAvailable, setDockerAvailable] = useState<boolean | null>(null);

  // Try Docker PDF conversion
  useEffect(() => {
    async function tryDockerConversion() {
      if (!workspacePath || !filePath) {
        setDockerAvailable(false);
        return;
      }

      setIsConverting(true);

      try {
        const response = await fetch('/api/convert/document', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: filePath,
            workspace: workspacePath,
          }),
        });

        const data = await response.json();

        if (data.success && data.content) {
          setPdfContent(data.content);
          setDockerAvailable(true);
        } else {
          setDockerAvailable(data.docker_required === true ? false : null);
        }
      } catch (err) {
        console.error('Docker conversion failed:', err);
        setDockerAvailable(false);
      } finally {
        setIsConverting(false);
      }
    }

    if (previewMode === 'auto' || previewMode === 'pdf') {
      tryDockerConversion();
    }
  }, [workspacePath, filePath, previewMode]);

  // Convert DOCX to HTML using mammoth (fallback)
  useEffect(() => {
    async function convertDocx() {
      setIsLoading(true);
      setError(null);

      try {
        // Convert base64 to ArrayBuffer
        const binaryString = atob(content);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const arrayBuffer = bytes.buffer;

        // Convert DOCX to HTML using mammoth
        const result = await mammoth.convertToHtml({ arrayBuffer });

        // Wrap in styled HTML document
        const styledHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {
      font-family: 'Calibri', -apple-system, BlinkMacSystemFont, sans-serif;
      line-height: 1.5;
      color: #1a1a1a;
      background: #fff;
      padding: 40px;
      margin: 0;
      max-width: 800px;
    }
    h1, h2, h3, h4, h5, h6 {
      color: #2b579a;
      margin-top: 24px;
      margin-bottom: 12px;
    }
    p { margin: 12px 0; }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 16px 0;
    }
    th, td {
      border: 1px solid #ddd;
      padding: 8px 12px;
      text-align: left;
    }
    th { background: #f5f5f5; }
    img { max-width: 100%; }
    ul, ol { padding-left: 24px; }
    blockquote {
      border-left: 4px solid #2b579a;
      margin: 16px 0;
      padding-left: 16px;
      color: #666;
    }
  </style>
</head>
<body>
${result.value}
</body>
</html>`;

        setHtmlContent(styledHtml);

        // Log any warnings
        if (result.messages.length > 0) {
          console.warn('Mammoth conversion warnings:', result.messages);
        }
      } catch (err) {
        console.error('DOCX conversion error:', err);
        setError(err instanceof Error ? err.message : 'Failed to convert document');
      } finally {
        setIsLoading(false);
      }
    }

    if (content && (previewMode === 'auto' || previewMode === 'html')) {
      convertDocx();
    }
  }, [content, previewMode]);

  // Determine what to show
  const showPdf = pdfContent && (previewMode === 'pdf' || (previewMode === 'auto' && dockerAvailable));
  const showHtml = !showPdf && htmlContent;

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-blue-900/30 border-b border-blue-700/50">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-400" />
          <span className="text-sm text-blue-300">Word Document</span>
          <span className="text-xs text-blue-500">- {fileName}</span>
        </div>

        {/* Mode toggle */}
        {(pdfContent || htmlContent) && (
          <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-0.5">
            <button
              onClick={() => setPreviewMode('pdf')}
              disabled={!pdfContent}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                showPdf ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-300'
              } ${!pdfContent ? 'opacity-50 cursor-not-allowed' : ''}`}
              title={pdfContent ? 'Full fidelity preview' : 'Docker container required for PDF preview'}
            >
              <FileImage className="w-3 h-3" />
              PDF
            </button>
            <button
              onClick={() => setPreviewMode('html')}
              disabled={!htmlContent}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                showHtml ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-300'
              }`}
              title="HTML conversion mode"
            >
              <FileText className="w-3 h-3" />
              HTML
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {/* Loading state */}
        {(isLoading || isConverting) && (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <Loader2 className="w-8 h-8 animate-spin mb-3" />
            <span>{isConverting ? 'Converting to PDF...' : 'Converting document...'}</span>
          </div>
        )}

        {/* Error state */}
        {error && !pdfContent && (
          <div className="flex flex-col items-center justify-center h-64 text-red-400">
            <AlertCircle className="w-8 h-8 mb-3" />
            <span className="font-medium">Failed to convert document</span>
            <span className="text-sm text-gray-500 mt-1">{error}</span>
          </div>
        )}

        {/* PDF preview mode */}
        {!isLoading && !isConverting && showPdf && pdfContent && (
          <div className="h-full" style={{ minHeight: '500px' }}>
            <PdfPreview content={pdfContent} fileName={fileName.replace(/\.docx$/i, '.pdf')} />
          </div>
        )}

        {/* HTML preview mode */}
        {!isLoading && !isConverting && showHtml && (
          <>
            {/* Docker not available notice - show when not using PDF mode */}
            {!pdfContent && (
              <div className="mx-4 mt-2 px-3 py-2 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
                <div className="flex items-center gap-2 text-xs text-yellow-400">
                  <AlertCircle className="w-4 h-4" />
                  <span>
                    {!workspacePath
                      ? "Full document preview available when viewing from workspace (requires Docker)."
                      : "Full preview requires Docker with MassGen container."
                    } Showing HTML conversion.
                  </span>
                </div>
              </div>
            )}
            <iframe
              srcDoc={htmlContent}
              sandbox=""
              title={`DOCX: ${fileName}`}
              className="w-full h-full border-0"
              style={{ minHeight: '500px' }}
            />
          </>
        )}
      </div>
    </div>
  );
}

export default DocxPreview;
