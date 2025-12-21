/**
 * XLSX Preview Component
 *
 * Renders Excel spreadsheets as HTML tables using SheetJS.
 */

import { useEffect, useState, useMemo } from 'react';
import { Table, AlertCircle, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import * as XLSX from 'xlsx';

interface XlsxPreviewProps {
  content: string; // Base64 encoded XLSX data
  fileName: string;
}

interface SheetData {
  name: string;
  data: string[][]; // 2D array of cell values
}

export function XlsxPreview({ content, fileName }: XlsxPreviewProps) {
  const [sheets, setSheets] = useState<SheetData[]>([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function parseXlsx() {
      setIsLoading(true);
      setError(null);

      try {
        // Convert base64 to binary string
        const binaryString = atob(content);

        // Parse the workbook
        const workbook = XLSX.read(binaryString, { type: 'binary' });

        // Extract data from each sheet
        const parsedSheets: SheetData[] = workbook.SheetNames.map((name) => {
          const sheet = workbook.Sheets[name];
          const data = XLSX.utils.sheet_to_json<string[]>(sheet, { header: 1 });
          return { name, data: data as string[][] };
        });

        setSheets(parsedSheets);
        setActiveSheet(0);
      } catch (err) {
        console.error('XLSX parsing error:', err);
        setError(err instanceof Error ? err.message : 'Failed to parse spreadsheet');
      } finally {
        setIsLoading(false);
      }
    }

    if (content) {
      parseXlsx();
    }
  }, [content]);

  // Generate HTML table for current sheet
  const tableHtml = useMemo(() => {
    if (sheets.length === 0 || !sheets[activeSheet]) return '';

    const { data } = sheets[activeSheet];
    if (data.length === 0) return '<p>Empty sheet</p>';

    let html = '<table><thead><tr>';

    // First row as headers
    const headers = data[0] || [];
    headers.forEach((cell) => {
      html += `<th>${cell ?? ''}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Remaining rows as data
    for (let i = 1; i < data.length; i++) {
      html += '<tr>';
      const row = data[i] || [];
      // Ensure we have same number of cells as headers
      for (let j = 0; j < headers.length; j++) {
        html += `<td>${row[j] ?? ''}</td>`;
      }
      html += '</tr>';
    }

    html += '</tbody></table>';
    return html;
  }, [sheets, activeSheet]);

  const fullHtml = useMemo(() => {
    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 13px;
      margin: 0;
      padding: 16px;
      background: #fff;
      color: #1a1a1a;
    }
    table {
      border-collapse: collapse;
      width: 100%;
    }
    th, td {
      border: 1px solid #e0e0e0;
      padding: 6px 10px;
      text-align: left;
      white-space: nowrap;
    }
    th {
      background: #f5f5f5;
      font-weight: 600;
      position: sticky;
      top: 0;
    }
    tr:nth-child(even) { background: #fafafa; }
    tr:hover { background: #f0f7ff; }
  </style>
</head>
<body>
${tableHtml}
</body>
</html>`;
  }, [tableHtml]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-green-900/30 border-b border-green-700/50">
        <div className="flex items-center gap-2">
          <Table className="w-4 h-4 text-green-400" />
          <span className="text-sm text-green-300">Excel Spreadsheet</span>
          <span className="text-xs text-green-500">- {fileName}</span>
        </div>

        {/* Sheet navigation */}
        {sheets.length > 1 && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveSheet((prev) => Math.max(0, prev - 1))}
              disabled={activeSheet === 0}
              className="p-1 hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4 text-gray-400" />
            </button>
            <span className="text-xs text-gray-400">
              {sheets[activeSheet]?.name} ({activeSheet + 1}/{sheets.length})
            </span>
            <button
              onClick={() => setActiveSheet((prev) => Math.min(sheets.length - 1, prev + 1))}
              disabled={activeSheet === sheets.length - 1}
              className="p-1 hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {isLoading && (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <Loader2 className="w-8 h-8 animate-spin mb-3" />
            <span>Parsing spreadsheet...</span>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-64 text-red-400">
            <AlertCircle className="w-8 h-8 mb-3" />
            <span className="font-medium">Failed to parse spreadsheet</span>
            <span className="text-sm text-gray-500 mt-1">{error}</span>
          </div>
        )}

        {!isLoading && !error && sheets.length > 0 && (
          <iframe
            srcDoc={fullHtml}
            sandbox=""
            title={`XLSX: ${fileName}`}
            className="w-full h-full border-0"
            style={{ minHeight: '400px' }}
          />
        )}
      </div>
    </div>
  );
}

export default XlsxPreview;
