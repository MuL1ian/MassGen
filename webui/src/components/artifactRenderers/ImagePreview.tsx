/**
 * Image Preview Component
 *
 * Displays images with zoom capability.
 * Supports PNG, JPG, GIF, WebP formats.
 */

import { useState, useCallback, useMemo } from 'react';
import { Image as ImageIcon, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';

interface ImagePreviewProps {
  content: string; // Base64 encoded image data or data URL
  fileName: string;
  mimeType?: string;
}

export function ImagePreview({ content, fileName, mimeType }: ImagePreviewProps) {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Create image source URL
  const imageSrc = useMemo(() => {
    if (!content) {
      return '';
    }

    // If content is already a data URL, use it directly
    if (content.startsWith('data:')) {
      return content;
    }

    // Otherwise, assume it's base64 and construct data URL
    const type = mimeType || 'image/png';
    return `data:${type};base64,${content}`;
  }, [content, mimeType]);

  const handleImageError = () => {
    setLoadError('Failed to load image');
  };

  const handleZoomIn = useCallback(() => {
    setZoom((prev) => Math.min(prev + 25, 300));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((prev) => Math.max(prev - 25, 25));
  }, []);

  const handleRotate = useCallback(() => {
    setRotation((prev) => (prev + 90) % 360);
  }, []);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-green-900/30 border-b border-green-700/50">
        <div className="flex items-center gap-2">
          <ImageIcon className="w-4 h-4 text-green-400" />
          <span className="text-sm text-green-300">Image Preview</span>
          <span className="text-xs text-green-500">- {fileName}</span>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-gray-200"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-400 min-w-[3rem] text-center">{zoom}%</span>
          <button
            onClick={handleZoomIn}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-gray-200"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleRotate}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-gray-200"
            title="Rotate"
          >
            <RotateCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Image container */}
      <div className="flex-1 overflow-auto bg-gray-800/50 flex items-center justify-center p-4">
        {loadError ? (
          <div className="text-red-400 text-center">
            <ImageIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>{loadError}</p>
            <p className="text-xs text-gray-500 mt-1">Content length: {content?.length || 0}</p>
          </div>
        ) : imageSrc ? (
          <img
            src={imageSrc}
            alt={fileName}
            onError={handleImageError}
            style={{
              transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
              transition: 'transform 0.2s ease',
              maxWidth: 'none',
            }}
            className="object-contain"
          />
        ) : (
          <div className="text-gray-500 text-center">
            <ImageIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No image content</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ImagePreview;
