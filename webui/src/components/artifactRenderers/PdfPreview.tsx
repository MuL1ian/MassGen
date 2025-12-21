/**
 * PDF Preview Component
 *
 * Displays PDF documents using the native browser PDF viewer.
 * Uses Blob URLs for better handling of large files.
 */

import { useEffect, useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';

interface PdfPreviewProps {
  content: string; // Base64 encoded PDF data or data URL
  fileName: string;
}

export function PdfPreview({ content, fileName }: PdfPreviewProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Convert base64 to Blob URL for better large file handling
  useEffect(() => {
    console.log('PdfPreview received content:', {
      fileName,
      contentLength: content?.length,
      contentPreview: content?.substring(0, 100),
      startsWithData: content?.startsWith('data:'),
    });

    try {
      // Extract base64 data
      let base64Data = content;
      if (content.startsWith('data:')) {
        base64Data = content.split(',')[1] || content;
      }

      // Decode base64 to binary
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Create Blob and URL
      const blob = new Blob([bytes], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      console.log('PdfPreview created blob URL, size:', blob.size);
      setBlobUrl(url);
      setError(null);

      // Cleanup on unmount or content change
      return () => {
        URL.revokeObjectURL(url);
      };
    } catch (err) {
      console.error('PdfPreview failed to create blob:', err);
      setError(err instanceof Error ? err.message : 'Failed to load PDF');
      setBlobUrl(null);
    }
  }, [content, fileName]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-red-900/30 border-b border-red-700/50">
        <FileText className="w-4 h-4 text-red-400" />
        <span className="text-sm text-red-300">PDF Document</span>
        <span className="text-xs text-red-500">- {fileName}</span>
      </div>

      {/* Loading state */}
      {!blobUrl && !error && (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="flex-1 flex items-center justify-center text-red-400">
          <span>Failed to load PDF: {error}</span>
        </div>
      )}

      {/* PDF viewer using iframe with blob URL */}
      {blobUrl && (
        <iframe
          src={blobUrl}
          title={`PDF: ${fileName}`}
          className="flex-1 w-full border-0"
          style={{ minHeight: '500px', height: '100%' }}
        />
      )}
    </div>
  );
}

export default PdfPreview;
