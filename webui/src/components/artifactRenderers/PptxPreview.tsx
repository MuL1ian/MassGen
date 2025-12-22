/**
 * PPTX Preview Component
 *
 * Renders PowerPoint presentations by:
 * 1. Attempting Docker-based PDF conversion for full fidelity (if available)
 * 2. Falling back to text extraction from slides
 */

import { useEffect, useState, useMemo } from 'react';
import { Presentation, AlertCircle, Loader2, ChevronLeft, ChevronRight, FileImage, FileText } from 'lucide-react';
import JSZip from 'jszip';
import PdfPreview from './PdfPreview';

interface PptxPreviewProps {
  content: string; // Base64 encoded PPTX data
  fileName: string;
  // Optional: workspace context for Docker conversion
  workspacePath?: string;
  filePath?: string;
}

interface SlideContent {
  index: number;
  text: string[];
  notes?: string;
}

type PreviewMode = 'auto' | 'pdf' | 'text';

export function PptxPreview({ content, fileName, workspacePath, filePath }: PptxPreviewProps) {
  const [slides, setSlides] = useState<SlideContent[]>([]);
  const [activeSlide, setActiveSlide] = useState(0);
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

        console.log('PPTX Docker conversion response:', {
          success: data.success,
          hasContent: !!data.content,
          contentLength: data.content?.length,
          contentPreview: data.content?.substring(0, 100),
          error: data.error,
          docker_required: data.docker_required,
        });

        if (data.success && data.content) {
          setPdfContent(data.content);
          setDockerAvailable(true);
          console.log('PPTX PDF content set, length:', data.content.length);
        } else {
          console.warn('PPTX conversion failed:', data.error);
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

  // Parse PPTX for text extraction (fallback)
  useEffect(() => {
    async function parsePptx() {
      setIsLoading(true);
      setError(null);

      try {
        if (!content || content.length === 0) {
          throw new Error('No content provided');
        }

        // Try to decode base64
        let bytes: Uint8Array;
        try {
          const binaryString = atob(content);
          bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
        } catch (decodeErr) {
          console.error('Base64 decode failed:', decodeErr);
          throw new Error('File content is not valid base64 encoded data');
        }

        // Load PPTX as ZIP
        let zip;
        try {
          zip = await JSZip.loadAsync(bytes);
        } catch (zipErr) {
          console.error('ZIP load failed:', zipErr);
          throw new Error('Failed to parse PPTX file structure');
        }

        // Find all slide XML files
        const slideFiles: string[] = [];
        zip.forEach((path) => {
          if (path.match(/ppt\/slides\/slide\d+\.xml$/)) {
            slideFiles.push(path);
          }
        });

        if (slideFiles.length === 0) {
          throw new Error('No slides found in presentation');
        }

        // Sort slides by number
        slideFiles.sort((a, b) => {
          const numA = parseInt(a.match(/slide(\d+)/)?.[1] || '0');
          const numB = parseInt(b.match(/slide(\d+)/)?.[1] || '0');
          return numA - numB;
        });

        // Extract text from each slide
        const parsedSlides: SlideContent[] = await Promise.all(
          slideFiles.map(async (path, index) => {
            const xmlContent = await zip.file(path)?.async('text');
            const text: string[] = [];

            if (xmlContent) {
              // Extract text from <a:t> elements
              const textMatches = xmlContent.matchAll(/<a:t>([^<]*)<\/a:t>/g);
              for (const match of textMatches) {
                if (match[1].trim()) {
                  text.push(match[1].trim());
                }
              }
            }

            return {
              index: index + 1,
              text,
            };
          })
        );

        setSlides(parsedSlides);
        setActiveSlide(0);
      } catch (err) {
        console.error('PPTX parsing error:', err);
        setError(err instanceof Error ? err.message : 'Failed to parse presentation');
      } finally {
        setIsLoading(false);
      }
    }

    if (content && (previewMode === 'auto' || previewMode === 'text')) {
      parsePptx();
    }
  }, [content, previewMode]);

  // Generate HTML for current slide (text mode)
  const slideHtml = useMemo(() => {
    if (slides.length === 0 || !slides[activeSlide]) return '';

    const slide = slides[activeSlide];

    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {
      font-family: 'Calibri', -apple-system, BlinkMacSystemFont, sans-serif;
      margin: 0;
      padding: 40px;
      background: linear-gradient(135deg, #1a1b26 0%, #24283b 100%);
      color: #c0caf5;
      min-height: 100vh;
      box-sizing: border-box;
    }
    .slide-container {
      background: #292e42;
      border-radius: 12px;
      padding: 40px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.3);
      max-width: 800px;
      margin: 0 auto;
    }
    .slide-number {
      font-size: 12px;
      color: #7dcfff;
      margin-bottom: 20px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .slide-content p {
      font-size: 18px;
      line-height: 1.6;
      margin: 16px 0;
    }
    .slide-content p:first-child {
      font-size: 28px;
      font-weight: 600;
      color: #7dcfff;
      margin-bottom: 24px;
    }
  </style>
</head>
<body>
  <div class="slide-container">
    <div class="slide-number">Slide ${slide.index} of ${slides.length}</div>
    <div class="slide-content">
      ${slide.text.map((t) => `<p>${t}</p>`).join('')}
      ${slide.text.length === 0 ? '<p style="color: #565f89; font-style: italic;">No text content on this slide</p>' : ''}
    </div>
  </div>
</body>
</html>`;
  }, [slides, activeSlide]);

  // Determine what to show
  const showPdf = pdfContent && (previewMode === 'pdf' || (previewMode === 'auto' && dockerAvailable));
  const showText = !showPdf && slides.length > 0;

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-orange-900/30 border-b border-orange-700/50">
        <div className="flex items-center gap-2">
          <Presentation className="w-4 h-4 text-orange-400" />
          <span className="text-sm text-orange-300">PowerPoint Presentation</span>
          <span className="text-xs text-orange-500">- {fileName}</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Mode toggle */}
          {(pdfContent || slides.length > 0) && (
            <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-0.5">
              <button
                onClick={() => setPreviewMode('pdf')}
                disabled={!pdfContent}
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                  showPdf ? 'bg-orange-600 text-white' : 'text-gray-400 hover:text-gray-300'
                } ${!pdfContent ? 'opacity-50 cursor-not-allowed' : ''}`}
                title={pdfContent ? 'Full fidelity preview' : 'Docker container required for PDF preview'}
              >
                <FileImage className="w-3 h-3" />
                PDF
              </button>
              <button
                onClick={() => setPreviewMode('text')}
                disabled={slides.length === 0}
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                  showText ? 'bg-orange-600 text-white' : 'text-gray-400 hover:text-gray-300'
                }`}
                title="Text extraction mode"
              >
                <FileText className="w-3 h-3" />
                Text
              </button>
            </div>
          )}

          {/* Slide navigation (text mode only) */}
          {showText && slides.length > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveSlide((prev) => Math.max(0, prev - 1))}
                disabled={activeSlide === 0}
                className="p-1 hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4 text-gray-400" />
              </button>
              <span className="text-xs text-gray-400">
                Slide {activeSlide + 1} of {slides.length}
              </span>
              <button
                onClick={() => setActiveSlide((prev) => Math.min(slides.length - 1, prev + 1))}
                disabled={activeSlide === slides.length - 1}
                className="p-1 hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {/* Loading state */}
        {(isLoading || isConverting) && (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <Loader2 className="w-8 h-8 animate-spin mb-3" />
            <span>{isConverting ? 'Converting to PDF...' : 'Parsing presentation...'}</span>
          </div>
        )}

        {/* Error state */}
        {error && !pdfContent && (
          <div className="flex flex-col items-center justify-center h-64 text-red-400">
            <AlertCircle className="w-8 h-8 mb-3" />
            <span className="font-medium">Failed to parse presentation</span>
            <span className="text-sm text-gray-500 mt-1">{error}</span>
          </div>
        )}

        {/* PDF preview mode */}
        {!isLoading && !isConverting && showPdf && pdfContent && (
          <div className="h-full" style={{ minHeight: '500px' }}>
            <PdfPreview content={pdfContent} fileName={fileName.replace(/\.pptx$/i, '.pdf')} />
          </div>
        )}

        {/* Text preview mode */}
        {!isLoading && !isConverting && showText && (
          <>
            {/* Docker not available notice - show when not using PDF mode */}
            {!pdfContent && (
              <div className="mx-4 mt-2 px-3 py-2 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
                <div className="flex items-center gap-2 text-xs text-yellow-400">
                  <AlertCircle className="w-4 h-4" />
                  <span>
                    {!workspacePath
                      ? "Full slide preview available when viewing from workspace (requires Docker)."
                      : "Full preview requires Docker with MassGen container."
                    } Showing text extraction.
                  </span>
                </div>
              </div>
            )}
            <iframe
              srcDoc={slideHtml}
              sandbox=""
              title={`PPTX: ${fileName}`}
              className="w-full h-full border-0"
              style={{ minHeight: '400px' }}
            />
          </>
        )}

        {/* Empty state */}
        {!isLoading && !isConverting && !error && slides.length === 0 && !pdfContent && (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <Presentation className="w-8 h-8 mb-3 opacity-50" />
            <span>No slides found in presentation</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default PptxPreview;
