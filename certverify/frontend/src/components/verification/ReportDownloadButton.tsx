import React, { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { apiClient } from '../../api/client';
import { getReportUrlApi } from '../../api/certificates';
import { useAuthStore } from '../../store/authStore';
import { Button } from '../ui/button';

interface ReportDownloadButtonProps {
  jobId: string;
}

export const ReportDownloadButton: React.FC<ReportDownloadButtonProps> = ({ jobId }) => {
  const [loading, setLoading] = useState(false);
  const token = useAuthStore((s) => s.token);

  const handleDownload = async () => {
    if (!jobId) return;
    setLoading(true);

    try {
      // 1. Ensure report is generated and ready on backend
      await getReportUrlApi(jobId);

      // 2. Fetch binary PDF stream via authenticated API client
      const response = await apiClient.get(`/api/v1/verify/${jobId}/report/download`, {
        responseType: 'blob',
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const blobUrl = window.URL.createObjectURL(blob);

      // 3. Trigger immediate file download
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `CertVerify_Audit_Report_${jobId.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // 4. Also open in new browser tab for direct inspection
      window.open(blobUrl, '_blank');

      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
      }, 60000);
    } catch (err) {
      console.error('Failed to generate or fetch PDF report:', err);
      // Fallback: direct window open with query token parameter
      if (token) {
        window.open(
          `/api/v1/verify/${jobId}/report/download?token=${encodeURIComponent(token)}`,
          '_blank'
        );
      } else {
        alert('Report generation failed. Please ensure verification is completed.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      onClick={handleDownload}
      disabled={loading}
      variant="outline"
      className="border-slate-300 text-slate-800 hover:bg-slate-100 shadow-sm"
    >
      {loading ? (
        <>
          <Loader2 className="h-4 w-4 mr-2 animate-spin text-blue-600" />
          Preparing PDF Report...
        </>
      ) : (
        <>
          <Download className="h-4 w-4 mr-2 text-slate-600" />
          Download PDF Audit Report
        </>
      )}
    </Button>
  );
};
