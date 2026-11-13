import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Archive,
  ArrowUpRight,
  CheckCircle2,
  Download,
  FileText,
  Layers,
  Loader2,
  RefreshCw,
  Upload,
} from 'lucide-react';
import {
  exportBatchCsvApi,
  getBatchDetailsApi,
  listBatchesApi,
  uploadBatchApi,
  BatchDetailResponse,
  BatchSummaryItem,
} from '../api/batch';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';

export const BatchVerifyPage: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [batchName, setBatchName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [batchData, setBatchData] = useState<BatchDetailResponse | null>(null);
  const [recentBatches, setRecentBatches] = useState<BatchSummaryItem[]>([]);
  const [exporting, setExporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load recent batches
  const loadRecentBatches = async () => {
    try {
      const list = await listBatchesApi();
      setRecentBatches(list);
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadRecentBatches();
  }, []);

  // Poll active batch details while processing
  useEffect(() => {
    if (!activeBatchId) return;

    let interval: NodeJS.Timeout;
    const fetchDetails = async () => {
      try {
        const data = await getBatchDetailsApi(activeBatchId);
        setBatchData(data);
        if (data.status === 'COMPLETED' || (data.completed_count + data.failed_count === data.total_count && data.total_count > 0)) {
          clearInterval(interval);
          loadRecentBatches();
        }
      } catch (err) {
        // ignore
      }
    };

    fetchDetails();
    interval = setInterval(fetchDetails, 3500);
    return () => clearInterval(interval);
  }, [activeBatchId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFiles.length === 0) return;

    setUploading(true);
    try {
      const formData = new FormData();
      if (batchName.trim()) {
        formData.append('batch_name', batchName.trim());
      }
      selectedFiles.forEach((f) => {
        formData.append('files', f);
      });

      const res = await uploadBatchApi(formData);
      setActiveBatchId(res.batch_id);
      setSelectedFiles([]);
      setBatchName('');
    } catch (err) {
      alert('Failed to start batch upload. Please check file formats (.pdf, .jpg, .png, .zip).');
    } finally {
      setUploading(false);
    }
  };

  const handleExportCsv = async () => {
    if (!activeBatchId) return;
    setExporting(true);
    try {
      const blob = await exportBatchCsvApi(activeBatchId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CertVerify_Batch_Audit_${activeBatchId.slice(0, 8)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Error downloading CSV audit report');
    } finally {
      setExporting(false);
    }
  };

  const completedPct = batchData
    ? Math.round(((batchData.completed_count + batchData.failed_count) / Math.max(batchData.total_count, 1)) * 100)
    : 0;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Layers className="h-8 w-8 text-blue-600" />
            Enterprise Bulk Verification
          </h1>
          <p className="text-slate-500 mt-1">
            Verify batches of up to 50 certificates simultaneously or upload a single ZIP archive for instant campus-drive processing.
          </p>
        </div>
        {recentBatches.length > 0 && !activeBatchId && (
          <Button
            variant="outline"
            onClick={() => setActiveBatchId(recentBatches[0].batch_id)}
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            View Latest Batch ({recentBatches[0].batch_name})
          </Button>
        )}
      </div>

      {/* Upload Box */}
      <Card className="border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg">New Batch Upload</CardTitle>
          <CardDescription>
            Select multiple PDF/image certificates or a single .ZIP file containing candidates' credentials.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUploadSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">
                Batch Name / Reference (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g., Campus Recruitment Drive 2026 - Batch A"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                className="w-full px-3 py-2 text-sm border rounded-lg border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-blue-50/20"
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.zip"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="flex flex-col items-center">
                <div className="h-12 w-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mb-3">
                  <Archive className="h-6 w-6" />
                </div>
                <p className="text-base font-semibold text-slate-800">
                  {selectedFiles.length > 0
                    ? `${selectedFiles.length} file(s) selected`
                    : 'Click to select or drag and drop files here'}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Supports .PDF, .PNG, .JPG files, or a single .ZIP folder (Max 10MB per file)
                </p>
              </div>
            </div>

            {selectedFiles.length > 0 && (
              <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-lg text-xs text-blue-800 flex items-center justify-between">
                <span>Selected: {selectedFiles.map((f) => f.name).slice(0, 3).join(', ')}{selectedFiles.length > 3 ? ` and ${selectedFiles.length - 3} more` : ''}</span>
                <span className="font-semibold">Ready to queue</span>
              </div>
            )}

            <Button
              type="submit"
              disabled={uploading || selectedFiles.length === 0}
              className="w-full sm:w-auto flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading & Queuing Batch...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Launch Batch Verification
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Active Batch Live View */}
      {batchData && (
        <div className="space-y-6 animate-fadeIn">
          {/* Batch Metrics Cards */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">{batchData.batch_name}</h2>
              <p className="text-sm text-slate-500">
                Created on {new Date(batchData.created_at).toLocaleString()} · {batchData.total_count} Certificates
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportCsv}
                disabled={exporting}
                className="flex items-center gap-2"
              >
                {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                Export Master CSV Audit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setActiveBatchId(null)}
              >
                Close View
              </Button>
            </div>
          </div>

          {/* Progress Bar */}
          <Card className="border-slate-200 shadow-sm p-4">
            <div className="flex items-center justify-between text-sm font-medium mb-2">
              <span className="text-slate-700 flex items-center gap-2">
                {batchData.status === 'COMPLETED' ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
                )}
                Batch Processing Progress: {completedPct}%
              </span>
              <span className="text-slate-500">
                {batchData.completed_count + batchData.failed_count} of {batchData.total_count} processed
              </span>
            </div>
            <Progress value={completedPct} className="h-2.5" />
          </Card>

          {/* Stat Cards Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4 border-slate-200">
              <div className="text-xs text-slate-500 font-medium">Total Files</div>
              <div className="text-2xl font-bold text-slate-900 mt-1">{batchData.total_count}</div>
            </Card>
            <Card className="p-4 border-slate-200 bg-emerald-50/30">
              <div className="text-xs text-emerald-700 font-medium">Verified / Completed</div>
              <div className="text-2xl font-bold text-emerald-700 mt-1">{batchData.completed_count}</div>
            </Card>
            <Card className="p-4 border-slate-200 bg-blue-50/30">
              <div className="text-xs text-blue-700 font-medium">Processing / In Queue</div>
              <div className="text-2xl font-bold text-blue-700 mt-1">{batchData.processing_count}</div>
            </Card>
            <Card className="p-4 border-slate-200 bg-amber-50/30">
              <div className="text-xs text-amber-700 font-medium">Avg Risk Score</div>
              <div className="text-2xl font-bold text-slate-900 mt-1">
                {batchData.average_risk_score !== null ? `${batchData.average_risk_score}/100` : 'Calculating...'}
              </div>
            </Card>
          </div>

          {/* Batch Table */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Batch Credential Audit Matrix</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50/70">
                      <TableHead>Filename</TableHead>
                      <TableHead>Candidate Name</TableHead>
                      <TableHead>Issuing Org</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Risk Score</TableHead>
                      <TableHead>Verdict</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {batchData.certificates.map((cert) => (
                      <TableRow key={cert.certificate_id} className="hover:bg-slate-50/50">
                        <TableCell className="font-medium text-slate-900 flex items-center gap-2">
                          <FileText className="h-4 w-4 text-slate-400" />
                          <span className="truncate max-w-[200px]" title={cert.filename}>
                            {cert.filename}
                          </span>
                        </TableCell>
                        <TableCell className="text-slate-700 font-medium">
                          {cert.candidate_name || <span className="text-slate-400 italic">Detecting...</span>}
                        </TableCell>
                        <TableCell className="text-slate-600 text-xs">
                          {cert.organization_name || <span className="text-slate-400 italic">Verifying...</span>}
                        </TableCell>
                        <TableCell>
                          {cert.status === 'COMPLETED' ? (
                            <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 border-none">
                              COMPLETED
                            </Badge>
                          ) : cert.status === 'FAILED' ? (
                            <Badge className="bg-rose-100 text-rose-800 hover:bg-rose-100 border-none">
                              FAILED
                            </Badge>
                          ) : (
                            <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100 border-none flex items-center gap-1 w-fit">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              {cert.progress_percentage}%
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {cert.risk_score !== null && cert.risk_score !== undefined ? (
                            <span
                              className={`font-semibold ${
                                (cert.risk_score ?? 0) <= 20
                                  ? 'text-emerald-600'
                                  : (cert.risk_score ?? 0) <= 60
                                  ? 'text-amber-600'
                                  : 'text-rose-600'
                              }`}
                            >
                              {cert.risk_score}/100
                            </span>
                          ) : (
                            <span className="text-slate-400 text-xs">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {cert.final_verdict === 'VERIFIED' ? (
                            <Badge className="bg-emerald-50 text-emerald-700 border-emerald-300">
                              VERIFIED
                            </Badge>
                          ) : cert.final_verdict === 'SUSPICIOUS' ? (
                            <Badge className="bg-rose-50 text-rose-700 border-rose-300">
                              SUSPICIOUS
                            </Badge>
                          ) : cert.final_verdict === 'UNABLE_TO_VERIFY' ? (
                            <Badge className="bg-slate-100 text-slate-700">UNABLE</Badge>
                          ) : (
                            <span className="text-slate-400 text-xs">Analyzing...</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {cert.job_id && (
                            <Link
                              to={`/verify/${cert.job_id}`}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800"
                            >
                              Inspect
                              <ArrowUpRight className="h-3.5 w-3.5" />
                            </Link>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Recent Batches History */}
      {recentBatches.length > 0 && !activeBatchId && (
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Recent Batches</CardTitle>
            <CardDescription>Historical batch verifications processed by your team.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50/70">
                  <TableHead>Batch Name</TableHead>
                  <TableHead>Total Files</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created Date</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentBatches.map((b) => (
                  <TableRow key={b.batch_id} className="hover:bg-slate-50/50">
                    <TableCell className="font-medium text-slate-900">{b.batch_name}</TableCell>
                    <TableCell>{b.total_count} items</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {b.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {new Date(b.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setActiveBatchId(b.batch_id)}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        Open Batch
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
