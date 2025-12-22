/**
 * Video Preview Component
 *
 * Displays video files (e.g., MP4/WebM/MOV) using a HTML5 video player.
 */

import { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import { Clapperboard, RotateCw, Volume2, VolumeX } from 'lucide-react';

interface VideoPreviewProps {
  content: string; // Base64-encoded video data or data URL
  fileName: string;
  mimeType?: string;
}

export function VideoPreview({ content, fileName, mimeType }: VideoPreviewProps) {
  const [loadError, setLoadError] = useState<string | null>(null);
  const [muted, setMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const videoSrc = useMemo(() => {
    if (!content) return '';
    if (content.startsWith('data:')) return content;
    const type = mimeType || 'video/mp4';
    return `data:${type};base64,${content}`;
  }, [content, mimeType]);

  useEffect(() => {
    setLoadError(null);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.load();
    }
  }, [videoSrc]);

  const handleReload = useCallback(() => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = 0;
    videoRef.current.play().catch(() => {
      // ignore autoplay errors (e.g., user interaction required)
    });
  }, []);

  const toggleMute = useCallback(() => {
    setMuted((prev) => !prev);
  }, []);

  return (
    <div className="w-full h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-blue-900/30 border-b border-blue-800/50">
        <div className="flex items-center gap-2">
          <Clapperboard className="w-4 h-4 text-blue-300" />
          <span className="text-sm text-blue-100">Video Preview</span>
          <span className="text-xs text-blue-300/80">- {fileName}</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleMute}
            className="p-1.5 text-gray-300 hover:text-white hover:bg-blue-800/40 rounded transition-colors"
            title={muted ? 'Unmute' : 'Mute'}
          >
            {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>
          <button
            onClick={handleReload}
            className="p-1.5 text-gray-300 hover:text-white hover:bg-blue-800/40 rounded transition-colors"
            title="Restart video"
          >
            <RotateCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Video area */}
      <div className="flex-1 flex items-center justify-center bg-black">
        {loadError ? (
          <div className="text-center text-red-300">
            <Clapperboard className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>Failed to load video</p>
            <p className="text-xs text-gray-500 mt-1">{loadError}</p>
          </div>
        ) : videoSrc ? (
          <video
            ref={videoRef}
            key={videoSrc}
            src={videoSrc}
            controls
            muted={muted}
            className="max-h-full max-w-full"
            onError={() => setLoadError('Unsupported video format or corrupted data')}
          />
        ) : (
          <div className="text-gray-500 text-center">
            <Clapperboard className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p>No video content</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default VideoPreview;
