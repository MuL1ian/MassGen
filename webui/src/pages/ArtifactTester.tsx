/**
 * Artifact Tester Page
 *
 * Standalone page to test artifact preview renderers with local files.
 * Drop or select files to test how they render without running MassGen.
 * For DOCX/PPTX files, uploads to a temp workspace to enable Docker conversion testing.
 */

import { useState, useCallback, useEffect } from 'react';
import { Upload, FileType, X, AlertCircle, Loader2 } from 'lucide-react';
import { detectArtifactType, getArtifactConfig } from '../utils/artifactTypes';
import {
  HtmlPreview,
  SvgPreview,
  ImagePreview,
  MarkdownPreview,
  PdfPreview,
  MermaidPreview,
  DocxPreview,
  XlsxPreview,
  PptxPreview,
  VideoPreview,
  SandpackPreview,
} from '../components/artifactRenderers';

interface LoadedFile {
  name: string;
  content: string;
  base64: string;
  size: number;
  type: string;
}

interface WorkspaceInfo {
  workspacePath: string;
  filePath: string;
}

export function ArtifactTester() {
  const [file, setFile] = useState<LoadedFile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [workspaceInfo, setWorkspaceInfo] = useState<WorkspaceInfo | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Detect artifact type
  const artifactType = file
    ? (() => {
        const detected = detectArtifactType(file.name, file.type, file.content);
        if (file.type.startsWith('video')) return 'video';
        const lower = file.name.toLowerCase();
        if (lower.endsWith('.mp4') || lower.endsWith('.webm') || lower.endsWith('.mov')) return 'video';
        return detected;
      })()
    : 'code';
  const artifactConfig = getArtifactConfig(artifactType);

  // Check if this file type needs Docker conversion (DOCX, PPTX)
  const needsDockerConversion = ['docx', 'pptx'].includes(artifactType);

  // Upload file to temp workspace for Docker conversion testing
  useEffect(() => {
    async function uploadToWorkspace() {
      if (!file || !needsDockerConversion) {
        setWorkspaceInfo(null);
        return;
      }

      setIsUploading(true);
      try {
        const response = await fetch('/api/tester/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fileName: file.name,
            content: file.base64,
          }),
        });

        const data = await response.json();

        if (data.success) {
          setWorkspaceInfo({
            workspacePath: data.workspacePath,
            filePath: data.filePath,
          });
          console.log('File uploaded for Docker conversion:', data);
        } else {
          console.error('Failed to upload for Docker conversion:', data.error);
          setWorkspaceInfo(null);
        }
      } catch (err) {
        console.error('Upload error:', err);
        setWorkspaceInfo(null);
      } finally {
        setIsUploading(false);
      }
    }

    uploadToWorkspace();
  }, [file, needsDockerConversion]);

  const handleFile = useCallback(async (selectedFile: File) => {
    setError(null);
    setWorkspaceInfo(null);

    try {
      const ext = selectedFile.name.toLowerCase().split('.').pop() || '';
      const mime = selectedFile.type || '';
      const isVideo = mime.startsWith('video') || ['mp4', 'webm', 'mov'].includes(ext);
      const isPdf = mime === 'application/pdf' || ext === 'pdf';
      const isImage = mime.startsWith('image') || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext);
      const isOffice = ['docx', 'xlsx', 'pptx'].includes(ext);
      const treatAsBinary = isVideo || isPdf || isImage || isOffice;

      // Read as text only for text-like files to avoid massive binary strings
      const textContent = treatAsBinary ? '' : await selectedFile.text();

      // Read as base64 for binary files
      const base64Content = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          // Remove data URL prefix (e.g., "data:application/pdf;base64,")
          const base64 = result.split(',')[1] || result;
          resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(selectedFile);
      });

      setFile({
        name: selectedFile.name,
        content: textContent,
        base64: base64Content,
        size: selectedFile.size,
        type: selectedFile.type || (isVideo ? 'video/mp4' : ''),
      });

      console.log('File loaded:', {
        name: selectedFile.name,
        size: selectedFile.size,
        type: selectedFile.type,
        contentLength: textContent.length,
        base64Length: base64Content.length,
        contentPreview: textContent.substring(0, 200),
      });
    } catch (err) {
      console.error('Failed to read file:', err);
      setError(err instanceof Error ? err.message : 'Failed to read file');
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFile(droppedFile);
    }
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFile(selectedFile);
    }
  }, [handleFile]);

  const clearFile = useCallback(() => {
    setFile(null);
    setError(null);
    setWorkspaceInfo(null);
  }, []);

  // Determine which content to use (text vs base64)
  const isBinaryType = ['docx', 'xlsx', 'pptx', 'pdf', 'image', 'video'].includes(artifactType);
  const contentToUse = file ? (isBinaryType ? file.base64 : file.content) : '';

  // Render the appropriate preview
  const renderPreview = () => {
    if (!file) return null;

    const fileName = file.name;

    switch (artifactType) {
      case 'html':
        return <HtmlPreview content={file.content} fileName={fileName} />;
      case 'svg':
        return <SvgPreview content={file.content} fileName={fileName} />;
      case 'image':
        return <ImagePreview content={file.base64} fileName={fileName} mimeType={file.type} />;
      case 'markdown':
        return <MarkdownPreview content={file.content} fileName={fileName} />;
      case 'pdf':
        return <PdfPreview content={file.base64} fileName={fileName} />;
      case 'mermaid':
        return <MermaidPreview content={file.content} fileName={fileName} />;
      case 'docx':
        return (
          <DocxPreview
            content={file.base64}
            fileName={fileName}
            workspacePath={workspaceInfo?.workspacePath}
            filePath={workspaceInfo?.filePath}
          />
        );
      case 'xlsx':
        return <XlsxPreview content={file.base64} fileName={fileName} />;
      case 'pptx':
        return (
          <PptxPreview
            content={file.base64}
            fileName={fileName}
            workspacePath={workspaceInfo?.workspacePath}
            filePath={workspaceInfo?.filePath}
          />
        );
      case 'video':
        return <VideoPreview content={file.base64} fileName={fileName} mimeType={file.type} />;
      case 'react':
        return <SandpackPreview content={file.content} fileName={fileName} />;
      default:
        return (
          <div className="p-4">
            {file.content ? (
              <pre className="whitespace-pre-wrap text-sm text-gray-300 font-mono">
                {file.content.substring(0, 5000)}
                {file.content.length > 5000 && '\n... (truncated)'}
              </pre>
            ) : (
              <div className="text-sm text-gray-400">
                Binary file loaded. Use preview or download above.
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2">Artifact Preview Tester</h1>
          <p className="text-gray-400">
            Drop or select a file to test how it renders in the artifact preview system.
          </p>
        </div>

        {/* File Upload Area */}
        {!file && (
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`
              border-2 border-dashed rounded-xl p-12 text-center transition-colors
              ${isDragging
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-gray-600 hover:border-gray-500'
              }
            `}
          >
            <Upload className="w-12 h-12 mx-auto mb-4 text-gray-500" />
            <p className="text-lg mb-2">Drop a file here or click to select</p>
            <p className="text-sm text-gray-500 mb-4">
              Supports: HTML, JSX/TSX, SVG, Markdown, PDF, DOCX, XLSX, PPTX, Images, Video, Mermaid
            </p>
            <label className="inline-block">
              <input
                type="file"
                onChange={handleInputChange}
                className="hidden"
              />
              <span className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg cursor-pointer transition-colors">
                Select File
              </span>
            </label>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mt-4 p-4 bg-red-900/30 border border-red-700 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {/* File Info & Preview */}
        {file && (
          <div className="space-y-4">
            {/* File Info Bar */}
            <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
              <div className="flex items-center gap-4">
                <FileType className="w-6 h-6 text-gray-400" />
                <div>
                  <div className="font-medium">{file.name}</div>
                  <div className="text-sm text-gray-400">
                    {(file.size / 1024).toFixed(1)} KB • {file.type || 'unknown type'} •
                    Detected as: <span className="text-blue-400">{artifactConfig.label}</span>
                    {needsDockerConversion && (
                      <span className="ml-2">
                        {isUploading ? (
                          <span className="text-yellow-400">
                            <Loader2 className="w-3 h-3 inline animate-spin mr-1" />
                            Preparing for Docker...
                          </span>
                        ) : workspaceInfo ? (
                          <span className="text-green-400">• Docker ready</span>
                        ) : (
                          <span className="text-gray-500">• Docker unavailable</span>
                        )}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={clearFile}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                title="Clear file"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Debug Info */}
            <details className="p-4 bg-gray-800/50 rounded-lg">
              <summary className="cursor-pointer text-sm text-gray-400 hover:text-gray-300">
                Debug Info (click to expand)
              </summary>
              <div className="mt-3 space-y-2 text-xs font-mono text-gray-500">
                <div>Artifact Type: {artifactType}</div>
                <div>Using: {isBinaryType ? 'base64' : 'text'} content</div>
                <div>Content Length: {contentToUse.length} chars</div>
                <div>Base64 Length: {file.base64.length} chars</div>
                <div>Text Length: {file.content.length} chars</div>
                {workspaceInfo && (
                  <>
                    <div className="text-green-400">Workspace Path: {workspaceInfo.workspacePath}</div>
                    <div className="text-green-400">File Path: {workspaceInfo.filePath}</div>
                  </>
                )}
                <div className="mt-2">
                  Content Preview (first 500 chars):
                  <pre className="mt-1 p-2 bg-gray-900 rounded overflow-x-auto">
                    {contentToUse.substring(0, 500)}
                  </pre>
                </div>
              </div>
            </details>

            {/* Preview Area */}
            <div className="bg-gray-800 rounded-lg overflow-hidden" style={{ minHeight: '500px' }}>
              {isUploading && needsDockerConversion ? (
                <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                  <Loader2 className="w-8 h-8 animate-spin mb-3" />
                  <span>Preparing file for Docker conversion...</span>
                </div>
              ) : (
                renderPreview()
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ArtifactTester;
