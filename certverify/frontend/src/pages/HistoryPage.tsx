import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Trash2,
  UploadCloud,
} from 'lucide-react';
import { format } from 'date-fns';
import { deleteCertificateApi, getCertificatesApi, getReportUrlApi } from '../api/certificates';
import { apiClient } from '../api/client';
import { Certificate } from '../types';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';

export const HistoryPage: React.FC = () => {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Delete dialog state
  const [deleteTarget, setDeleteTarget] = useState<Certificate | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const fetchCertificates = async () => {
    try {
      const res = await getCertificatesApi(page, 10);
      setCertificates(res.items);
      setTotalPages(res.pages);
      setTotalCount(res.total);
    } catch (err) {
      console.error('Failed to fetch certificates:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCertificates();
  }, [page]);

  const hasActiveJobs = certificates.some(
    (c) => c.job_status === 'PENDING' || c.job_status === 'PROCESSING'
  );

  // Auto-refresh interval 8s only when there are active jobs
  useEffect(() => {
    if (!hasActiveJobs) return;

    const interval = setInterval(() => {
      fetchCertificates();
    }, 8000);

    return () => clearInterval(interval);
  }, [hasActiveJobs, page]);

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteCertificateApi(deleteTarget.id);
      setDeleteTarget(null);
      await fetchCertificates();
    } catch (err) {
      console.error('Failed to delete certificate:', err);
    } finally {
      setDeleting(false);
    }
  };

  const handleDownloadReport = async (jobId: string) => {
    setDownloadingId(jobId);
    try {
      await getReportUrlApi(jobId);
      const response = await apiClient.get(`/api/v1/verify/${jobId}/report/download`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `CertVerify_Audit_Report_${jobId.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.open(blobUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60000);
    } catch (err) {
      console.error('Failed to get report:', err);
    } finally {
      setDownloadingId(null);
    }
  };

  const getStatusBadge = (status?: string | null) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge variant="success">Completed</Badge>;
      case 'PROCESSING':
      case 'PENDING':
        return <Badge variant="warning">Analyzing</Badge>;
      case 'FAILED':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">Queued</Badge>;
    }
  };

  const getVerdictBadge = (verdict?: string | null) => {
    switch (verdict) {
      case 'VERIFIED':
        return <Badge variant="success">Verified</Badge>;
      case 'SUSPICIOUS':
        return <Badge variant="destructive">Suspicious</Badge>;
      case 'UNABLE_TO_VERIFY':
        return <Badge variant="secondary">Unable to Verify</Badge>;
      default:
        return <span className="text-slate-400 text-xs">—</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Verification History</h1>
          <p className="text-sm text-slate-500 mt-1">
            Complete archive of uploaded credentials and forensic evaluation records ({totalCount} total)
          </p>
        </div>
        <Link to="/upload">
          <Button className="bg-blue-600 hover:bg-blue-700">
            <UploadCloud className="h-4 w-4 mr-2" />
            Upload New Document
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader className="border-b border-slate-100 pb-4">
          <CardTitle className="text-base font-semibold">Document Archive</CardTitle>
          <CardDescription>Track status, forensic findings, and download PDF audits</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : certificates.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Document File</TableHead>
                    <TableHead>Format</TableHead>
                    <TableHead>Uploaded</TableHead>
                    <TableHead>Job Status</TableHead>
                    <TableHead>Risk Verdict</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {certificates.map((cert) => (
                    <TableRow key={cert.id}>
                      <TableCell className="font-medium text-slate-900">
                        <div className="flex items-center gap-2 max-w-[240px]">
                          <FileText className="h-4 w-4 text-blue-600 shrink-0" />
                          <span className="truncate">{cert.original_filename}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-xs uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-700 border">
                          {cert.file_type}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                        {format(new Date(cert.created_at), 'dd MMM yyyy, HH:mm')}
                      </TableCell>
                      <TableCell>{getStatusBadge(cert.job_status)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getVerdictBadge(cert.final_verdict)}
                          {cert.risk_score !== null && cert.risk_score !== undefined && (
                            <span className="text-xs font-mono text-slate-500 font-semibold">
                              ({cert.risk_score}/100)
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {cert.job_id && (
                            <Link
                              to={`/verify/${cert.job_id}`}
                              className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-2.5 h-8 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
                            >
                              <ExternalLink className="h-3.5 w-3.5 mr-1" />
                              Inspect
                            </Link>
                          )}

                          {cert.job_status === 'COMPLETED' && cert.job_id && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8 px-2.5 text-xs text-slate-700"
                              onClick={() => handleDownloadReport(cert.job_id!)}
                              disabled={downloadingId === cert.job_id}
                            >
                              {downloadingId === cert.job_id ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Download className="h-3.5 w-3.5" />
                              )}
                            </Button>
                          )}

                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50"
                            onClick={() => setDeleteTarget(cert)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="py-16 text-center">
              <UploadCloud className="h-12 w-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-800">No certificates in archive</h3>
              <p className="text-xs text-slate-500 mt-1 mb-5">
                Upload your first certificate document to begin automated AI verification.
              </p>
              <Link to="/upload">
                <Button className="bg-blue-600 hover:bg-blue-700">
                  Upload Certificate Now
                </Button>
              </Link>
            </div>
          )}

          {/* Pagination bar */}
          {totalPages > 1 && (
            <div className="border-t border-slate-100 p-4 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Page <span className="font-semibold text-slate-900">{page}</span> of{' '}
                <span className="font-semibold text-slate-900">{totalPages}</span>
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="text-xs"
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="text-xs"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogHeader>
          <DialogTitle>Delete Certificate</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete{' '}
            <span className="font-semibold text-slate-900">{deleteTarget?.original_filename}</span>?
            This will permanently remove the stored file and all associated verification records.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDeleteTarget(null)}
            disabled={deleting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={confirmDelete}
            disabled={deleting}
          >
            {deleting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Record'
            )}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
};

