/**
 * Artifact Type Detection Utility
 *
 * Detects the appropriate renderer for different file types.
 * Supports all artifact types matching Claude.ai capabilities.
 */

export type ArtifactType =
  | 'react'      // React/Vue/TS components via Sandpack
  | 'html'       // Static HTML/CSS/JS via srcdoc iframe
  | 'svg'        // SVG graphics via sandbox iframe
  | 'mermaid'    // Mermaid diagrams
  | 'markdown'   // Markdown documents
  | 'pdf'        // PDF documents
  | 'image'      // Images (PNG, JPG, GIF, WebP)
  | 'video'      // Videos (MP4/WebM/MOV)
  | 'docx'       // Word documents
  | 'xlsx'       // Excel spreadsheets
  | 'pptx'       // PowerPoint presentations
  | 'code';      // Code with syntax highlighting (default)

export interface ArtifactConfig {
  type: ArtifactType;
  canPreview: boolean;
  label: string;
  icon: string;
}

// File extension to artifact type mapping
const extensionMap: Record<string, ArtifactType> = {
  // React/Vue components (use Sandpack)
  'jsx': 'react',
  'tsx': 'react',
  'vue': 'react',

  // HTML/CSS/JS
  'html': 'html',
  'htm': 'html',

  // SVG
  'svg': 'svg',

  // Mermaid diagrams
  'mermaid': 'mermaid',
  'mmd': 'mermaid',

  // Markdown
  'md': 'markdown',
  'markdown': 'markdown',

  // PDF
  'pdf': 'pdf',

  // Images
  'png': 'image',
  'jpg': 'image',
  'jpeg': 'image',
  'gif': 'image',
  'webp': 'image',

  // Video
  'mp4': 'video',
  'webm': 'video',
  'mov': 'video',

  // Office documents
  'docx': 'docx',
  'xlsx': 'xlsx',
  'pptx': 'pptx',
};

// MIME type to artifact type mapping (fallback)
const mimeTypeMap: Record<string, ArtifactType> = {
  'text/html': 'html',
  'image/svg+xml': 'svg',
  'text/markdown': 'markdown',
  'application/pdf': 'pdf',
  'image/png': 'image',
  'image/jpeg': 'image',
  'image/gif': 'image',
  'image/webp': 'image',
  'video/mp4': 'video',
  'video/webm': 'video',
  'video/quicktime': 'video',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
};

// Artifact type configurations
const artifactConfigs: Record<ArtifactType, Omit<ArtifactConfig, 'type'>> = {
  react: { canPreview: true, label: 'React Component', icon: '⚛️' },
  html: { canPreview: true, label: 'HTML Preview', icon: '🌐' },
  svg: { canPreview: true, label: 'SVG Preview', icon: '🎨' },
  mermaid: { canPreview: true, label: 'Mermaid Diagram', icon: '📊' },
  markdown: { canPreview: true, label: 'Markdown Preview', icon: '📝' },
  pdf: { canPreview: true, label: 'PDF Document', icon: '📄' },
  image: { canPreview: true, label: 'Image', icon: '🖼️' },
  video: { canPreview: true, label: 'Video', icon: '🎬' },
  docx: { canPreview: true, label: 'Word Document', icon: '📘' },
  xlsx: { canPreview: true, label: 'Excel Spreadsheet', icon: '📊' },
  pptx: { canPreview: true, label: 'PowerPoint', icon: '📽️' },
  code: { canPreview: false, label: 'Source Code', icon: '💻' },
};

/**
 * Get file extension from path
 */
function getExtension(filePath: string): string {
  const parts = filePath.split('.');
  return parts.length > 1 ? parts.pop()!.toLowerCase() : '';
}

/**
 * Detect artifact type from file path, MIME type, and content
 */
export function detectArtifactType(
  filePath: string,
  mimeType?: string,
  content?: string
): ArtifactType {
  const ext = getExtension(filePath);

  // Check extension first
  if (ext && extensionMap[ext]) {
    return extensionMap[ext];
  }

  // Check MIME type
  if (mimeType && mimeTypeMap[mimeType]) {
    return mimeTypeMap[mimeType];
  }

  // Content-based detection for ambiguous cases
  if (content) {
    const trimmed = content.trim();

    // Detect HTML
    if (trimmed.startsWith('<!DOCTYPE html>') || trimmed.startsWith('<html')) {
      return 'html';
    }

    // Detect SVG
    if (trimmed.startsWith('<svg') || trimmed.includes('xmlns="http://www.w3.org/2000/svg"')) {
      return 'svg';
    }

    // Detect Mermaid
    if (
      trimmed.startsWith('graph ') ||
      trimmed.startsWith('flowchart ') ||
      trimmed.startsWith('sequenceDiagram') ||
      trimmed.startsWith('classDiagram') ||
      trimmed.startsWith('stateDiagram') ||
      trimmed.startsWith('erDiagram') ||
      trimmed.startsWith('gantt') ||
      trimmed.startsWith('pie ')
    ) {
      return 'mermaid';
    }
  }

  // Default to code
  return 'code';
}

/**
 * Get artifact configuration for a given type
 */
export function getArtifactConfig(type: ArtifactType): ArtifactConfig {
  return {
    type,
    ...artifactConfigs[type],
  };
}

/**
 * Check if a file can be previewed
 */
export function canPreviewFile(filePath: string, mimeType?: string, content?: string): boolean {
  const type = detectArtifactType(filePath, mimeType, content);
  return artifactConfigs[type].canPreview;
}

/**
 * Get all previewable file extensions
 */
export function getPreviewableExtensions(): string[] {
  return Object.keys(extensionMap);
}
