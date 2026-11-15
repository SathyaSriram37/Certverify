import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck,
  Globe,
  Loader2,
  QrCode,
  RefreshCw,
  ScanLine,
  ShieldAlert,
} from 'lucide-react';
import { getJobStatusApi, getResultsApi, retryVerificationApi } from '../api/certificates';
import { ResultsResponse, VerificationJob } from '../types';
import { ModuleBreakdown } from '../components/verification/ModuleBreakdown';
import { ReportDownloadButton } from '../components/verification/ReportDownloadButton';
import { RiskScoreCard } from '../components/verification/RiskScoreCard';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';

const PIPELINE_STEPS = [
  'Document Classification',
  'OCR Extraction',
  'Company Verification',
  'Document Forensics',
  'Duplicate Detection',
  'Risk Assessment',
];

export const VerificationResultPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<VerificationJob | null>(null);
  const [resultsData, setResultsData] = useState<ResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchingResults, setFetchingResults] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const loadData = useCallback(async () => {
    if (!jobId) {
      setErrorMessage('No Job ID provided in the route URL.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      // 1. Fetch initial job status
      const jobStatus = await getJobStatusApi(jobId);
      setJob(jobStatus);

      // 2. If already completed, load results immediately
      if (jobStatus.status === 'COMPLETED') {
        setFetchingResults(true);
        try {
          const res = await getResultsApi(jobId);
          setResultsData(res);
        } catch (resErr: any) {
          console.error('Failed to load verification results:', resErr);
          setErrorMessage(
            resErr.response?.data?.detail || 'Failed to load detailed verification findings.'
          );
        } finally {
          setFetchingResults(false);
        }
      } else if (jobStatus.status === 'PENDING' || jobStatus.status === 'PROCESSING') {
        // Start background polling every 3 seconds until finished
        stopPolling();
        pollingRef.current = setInterval(async () => {
          try {
            const updated = await getJobStatusApi(jobId);
            setJob(updated);

            if (updated.status === 'COMPLETED') {
              stopPolling();
              setFetchingResults(true);
              const res = await getResultsApi(jobId);
              setResultsData(res);
              setFetchingResults(false);
            } else if (updated.status === 'FAILED') {
              stopPolling();
            }
          } catch (pollErr) {
            console.error('Polling error:', pollErr);
          }
        }, 3000);
      }
    } catch (err: any) {
      console.error('Error fetching verification job:', err);
      setErrorMessage(
        err.response?.data?.detail || 'Verification job could not be retrieved from the server.'
      );
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    if (!jobId) return;
    setRetrying(true);
    try {
      const updated = await retryVerificationApi(jobId);
      setJob(updated);
      setResultsData(null);
      loadData();
    } catch (err: any) {
      console.error('Failed to retry verification:', err);
      alert(err.response?.data?.detail || 'Failed to trigger verification retry.');
    } finally {
      setRetrying(false);
    }
  };

  useEffect(() => {
    loadData();
    return () => {
      stopPolling();
    };
  }, [loadData]);

  // Helper getters for results modules
  const getModule = (name: string) =>
    resultsData?.results?.find((r) => r.module_name === name);

  const entityResult = getModule('ENTITY_EXTRACTION');
  const entities = (entityResult?.details as Record<string, any>) || {};
  const classificationResult = getModule('CLASSIFICATION');
  const companyResult = getModule('COMPANY_INTELLIGENCE');
  const companyData = (companyResult?.details as Record<string, any>) || {};
  const isoResult = getModule('ISO_VERIFICATION');
  const isoData = (isoResult?.details as Record<string, any>) || {};
  const logoResult = getModule('LOGO_SIMILARITY');
  const logoData = (logoResult?.details as Record<string, any>) || {};
  const pdfForensicsResult = getModule('PDF_FORENSICS');
  const imageForensicsResult = getModule('IMAGE_FORENSICS');
  const forensicsData = (imageForensicsResult?.details as Record<string, any>) || {};
  const qrResult = getModule('QR_CODE');
  const qrData = (qrResult?.details as Record<string, any>) || {};
  const sigResult = getModule('DIGITAL_SIGNATURE');
  const sigData = (sigResult?.details as Record<string, any>) || {};
  const dupResult = getModule('DUPLICATE_DETECTION');
  const dupData = (dupResult?.details as Record<string, any>) || {};

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-16">
      {/* Top back navigation */}
      <div className="flex items-center justify-between">
        <Link to="/history">
          <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-900">
            <ArrowLeft className="h-4 w-4 mr-1.5" /> Back to History
          </Button>
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-slate-400">JOB ID: {jobId}</span>
          {(job?.status === 'FAILED' || job?.status === 'PENDING') && (
            <Button
              variant="default"
              size="sm"
              onClick={handleRetry}
              disabled={retrying || loading}
              className="h-8 text-xs bg-blue-600 hover:bg-blue-700 text-white"
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${retrying ? 'animate-spin' : ''}`} />
              {retrying ? 'Starting Re-analysis...' : 'Re-run Verification'}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadData()}
            className="h-8 text-xs text-slate-600"
            disabled={loading || fetchingResults}
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading || fetchingResults ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* ERROR STATE */}
      {errorMessage && (
        <Alert variant="destructive">
          <AlertTriangle className="h-5 w-5" />
          <AlertTitle className="text-base font-bold">Unable to Load Verification</AlertTitle>
          <AlertDescription className="mt-2 space-y-3">
            <p>{errorMessage}</p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => loadData()}>
                Try Again
              </Button>
              <Link to="/history">
                <Button size="sm" variant="secondary">
                  Return to Archive
                </Button>
              </Link>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* INITIAL LOADING STATE */}
      {loading && !job && (
        <div className="h-96 flex flex-col items-center justify-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-sm font-medium text-slate-600">Loading verification pipeline status...</p>
        </div>
      )}

      {/* RECORD NOT FOUND */}
      {!loading && !job && !errorMessage && (
        <Card className="p-8 text-center border-slate-200">
          <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">Verification Job Not Found</h3>
          <p className="text-xs text-slate-500 mt-1 mb-4">
            The requested verification job could not be located in your account.
          </p>
          <Link to="/history">
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
              Back to History
            </Button>
          </Link>
        </Card>
      )}

      {/* PIPELINE ACTIVE / PROCESSING STATE */}
      {job && (job.status === 'PENDING' || job.status === 'PROCESSING') && (
        <Card className="border-blue-200 bg-blue-50/20 shadow-sm">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 mb-2">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
            <CardTitle className="text-xl font-bold text-slate-900">
              AI Verification In Progress
            </CardTitle>
            <CardDescription>
              Current step: <span className="font-semibold text-blue-600">{job.current_step || 'Initializing checks'}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-4">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold text-slate-700">
                <span>Verification Pipeline Progress</span>
                <span>{job.progress_percentage}%</span>
              </div>
              <Progress value={job.progress_percentage} />
            </div>

            {/* Stepper list */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
              {PIPELINE_STEPS.map((step, idx) => {
                const stepProgressWeight = (idx + 1) * 16.6;
                const isDone = job.progress_percentage >= stepProgressWeight;
                const isActive = !isDone && job.progress_percentage >= idx * 16.6;

                return (
                  <div
                    key={step}
                    className={`flex items-center gap-2 p-3 rounded-lg border text-xs font-medium ${
                      isDone
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                        : isActive
                        ? 'bg-blue-50 border-blue-300 text-blue-800 font-semibold'
                        : 'bg-white border-slate-200 text-slate-400'
                    }`}
                  >
                    {isDone ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    ) : isActive ? (
                      <Loader2 className="h-4 w-4 text-blue-600 animate-spin shrink-0" />
                    ) : (
                      <Clock className="h-4 w-4 text-slate-300 shrink-0" />
                    )}
                    <span className="truncate">{step}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* FAILED STATE */}
      {job?.status === 'FAILED' && (
        <Alert variant="destructive">
          <AlertTriangle className="h-5 w-5" />
          <AlertTitle className="text-base font-bold">Verification Pipeline Failed</AlertTitle>
          <AlertDescription className="mt-2 space-y-3">
            <p>{job.error_message || 'An unexpected failure occurred while analyzing the certificate file.'}</p>
            <div>
              <Button
                size="sm"
                variant="outline"
                onClick={handleRetry}
                disabled={retrying}
                className="bg-white text-rose-700 border-rose-300 hover:bg-rose-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${retrying ? 'animate-spin' : ''}`} />
                {retrying ? 'Retrying...' : 'Retry Verification Now'}
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* COMPLETED BUT STILL FETCHING RESULTS DATA */}
      {job?.status === 'COMPLETED' && fetchingResults && !resultsData && (
        <div className="h-80 flex flex-col items-center justify-center space-y-3 bg-white rounded-xl border border-slate-200 shadow-sm">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-sm font-medium text-slate-700">Compiling comprehensive forensic report &amp; metrics...</p>
        </div>
      )}

      {/* COMPLETED STATE: FULL 7 AUDIT CARDS */}
      {job?.status === 'COMPLETED' && resultsData && (
        <>
          {/* Card 1: RiskScoreCard + Report Download Button */}
          {resultsData.risk_assessment && (
            <div className="space-y-4">
              <div className="flex justify-end">
                <ReportDownloadButton jobId={jobId || (job as any).job_id || job.id} />
              </div>
              <RiskScoreCard assessment={resultsData.risk_assessment} />
            </div>
          )}

          {/* Card 2: Module Breakdown */}
          {resultsData.results && resultsData.results.length > 0 && (
            <ModuleBreakdown results={resultsData.results} />
          )}

          {/* Card 3: Extracted Information */}
          <Card className="shadow-sm border-slate-200">
            <CardHeader className="border-b border-slate-100 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">Extracted Credential Data</CardTitle>
                  <CardDescription>OCR and structural entity extraction results</CardDescription>
                </div>
                {classificationResult && (
                  <Badge variant="purple">
                    {classificationResult.finding_summary}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-1/3">Field</TableHead>
                    <TableHead>Extracted Value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-medium text-slate-600">Candidate / Recipient</TableCell>
                    <TableCell className="font-semibold text-slate-900">{entities.candidate_name || '—'}</TableCell>
                  </TableRow>
                  {(entities.standard_code || entities.accreditation_body) && (
                    <TableRow>
                      <TableCell className="font-medium text-slate-600">Standard / Accreditation</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {entities.standard_code && (
                            <Badge className="bg-blue-100 text-blue-800 border-blue-200">
                              {entities.standard_code}
                            </Badge>
                          )}
                          {entities.accreditation_body && (
                            <Badge className="bg-purple-100 text-purple-800 border-purple-200">
                              Accredited: {entities.accreditation_body}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  <TableRow>
                    <TableCell className="font-medium text-slate-600">Issuing Organization</TableCell>
                    <TableCell className="font-semibold text-slate-900">{entities.organization_name || '—'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium text-slate-600">Issue Date</TableCell>
                    <TableCell className="text-slate-800">{entities.issue_date || '—'}</TableCell>
                  </TableRow>
                  {entities.expiry_date && (
                    <TableRow>
                      <TableCell className="font-medium text-slate-600">Valid Until / Expiry</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="text-slate-800">{entities.expiry_date}</span>
                          {entities.is_expired ? (
                            <Badge className="bg-rose-100 text-rose-700 border-rose-200">EXPIRED</Badge>
                          ) : (
                            <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">VALID / ACTIVE</Badge>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  <TableRow>
                    <TableCell className="font-medium text-slate-600">Certificate Number / ID</TableCell>
                    <TableCell className="font-mono text-slate-800">{entities.cert_number || '—'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium text-slate-600">Official Website</TableCell>
                    <TableCell>
                      {entities.website ? (
                        <a
                          href={entities.website}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline inline-flex items-center gap-1"
                        >
                          {entities.website} <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium text-slate-600">Email Address</TableCell>
                    <TableCell className="text-slate-800">{entities.email || '—'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium text-slate-600">Signatory Authority</TableCell>
                    <TableCell className="text-slate-800">{entities.signatory || '—'}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Card 4: Company Intelligence */}
          <Card className="shadow-sm border-slate-200">
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="text-base font-semibold">Company Intelligence &amp; Registry Verification</CardTitle>
              <CardDescription>Live web corroboration, SSL authenticity, and registry checks</CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Organization Profile</span>
                  <p className="font-bold text-slate-900">{companyData.org_name || entities.organization_name || 'Not provided'}</p>
                  <div className="flex items-center gap-2 pt-1">
                    <span className="text-xs text-slate-600">Public Online Footprint:</span>
                    {companyData.online_presence_found ? (
                      <Badge variant="success">Found</Badge>
                    ) : (
                      <Badge variant="destructive">Not Found</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-600">Gov Registry (MCA Hint):</span>
                    {companyData.mca_hint ? (
                      <Badge variant="success">Registered</Badge>
                    ) : (
                      <Badge variant="secondary">Not Verified</Badge>
                    )}
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Web Domain &amp; Brand Audit</span>
                  <div className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-slate-500" />
                    <span className="text-xs text-slate-700 truncate">{companyData.website_provided || 'No website'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-600">Domain Active:</span>
                    {companyData.website_active ? (
                      <Badge variant="success">Active (200 OK)</Badge>
                    ) : (
                      <Badge variant="destructive">Inactive</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-600">Logo Match:</span>
                    {logoData.favicon_found ? (
                      <Badge variant="success">{((Number(logoData.similarity_score) || 0) * 100).toFixed(0)}% Visual Match</Badge>
                    ) : (
                      <Badge variant="secondary">Not Checked</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-600">ISO Standards Claim:</span>
                    <Badge variant={isoData.evidence_found ? 'success' : 'secondary'}>
                      {isoResult?.finding_summary || 'Not Claimed'}
                    </Badge>
                  </div>
                </div>
              </div>

              {Array.isArray(companyData.evidence_sources) && companyData.evidence_sources.length > 0 && (
                <div className="pt-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase block mb-1">
                    Evidence Sources:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {companyData.evidence_sources.map((src: string, i: number) => {
                      const host = typeof src === 'string' ? src.replace('https://', '').replace('http://', '').split('/')[0] : String(src);
                      return (
                        <a
                          key={i}
                          href={src}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-md border border-blue-200 hover:underline flex items-center gap-1"
                        >
                          {host} <ExternalLink className="h-3 w-3" />
                        </a>
                      );
                    })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Card 5: Document Forensics & ELA */}
          <Card className="shadow-sm border-slate-200">
            <CardHeader className="border-b border-slate-100 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">Document Forensics &amp; Manipulation Detection</CardTitle>
                  <CardDescription>Error Level Analysis (ELA), EXIF software signatures, and structural metadata</CardDescription>
                </div>
                <Badge
                  variant={
                    imageForensicsResult?.status === 'PASS'
                      ? 'success'
                      : imageForensicsResult?.status === 'WARNING'
                      ? 'warning'
                      : 'destructive'
                  }
                >
                  {imageForensicsResult?.status === 'PASS'
                    ? 'CLEAN INTEGRITY'
                    : imageForensicsResult?.status === 'WARNING'
                    ? 'MINOR ANOMALIES'
                    : 'TAMPERING SUSPECTED'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              {forensicsData.annotated_image_url && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-red-700 flex items-center gap-1.5">
                    <ShieldAlert className="h-4 w-4" /> Detected Tampering Anomaly Map (Highlighted Red):
                  </p>
                  <img
                    src={forensicsData.annotated_image_url}
                    alt="Forensic Tamper Map"
                    className="w-full max-h-96 object-contain rounded-lg border-2 border-red-400 shadow-md bg-black"
                  />
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="p-3 bg-slate-50 rounded-lg border">
                  <span className="text-xs text-slate-500 font-medium block">ELA Difference Score</span>
                  <span className="text-lg font-bold text-slate-900">{forensicsData.ela_mean ?? '—'}</span>
                  <span className="text-[11px] text-slate-400 block mt-0.5">Threshold: {forensicsData.threshold ?? '36.0'}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border">
                  <span className="text-xs text-slate-500 font-medium block">Editing Software Signature</span>
                  <span className="text-sm font-semibold text-slate-900 truncate block">
                    {forensicsData.editing_software_detected || 'None Detected'}
                  </span>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border">
                  <span className="text-xs text-slate-500 font-medium block">Covert White-Out Overlay</span>
                  <span className={`text-sm font-bold truncate block ${
                    pdfForensicsResult?.details?.whiteout_data?.whiteout_detected
                      ? 'text-rose-600'
                      : 'text-emerald-600'
                  }`}>
                    {pdfForensicsResult?.details?.whiteout_data?.whiteout_detected
                      ? `Tampering Detected (${pdfForensicsResult.details.whiteout_data.suspicious_box_count} patches)`
                      : 'Clean (Zero Masking)'}
                  </span>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border">
                  <span className="text-xs text-slate-500 font-medium block">PDF Font Families</span>
                  <span className="text-lg font-bold text-slate-900">
                    {pdfForensicsResult?.details?.font_family_count ?? 'N/A'}
                  </span>
                </div>
              </div>

              {/* Advanced Deepfake & FFT Frequency Domain Analysis */}
              {forensicsData.deepfake_audit?.fft_data?.fft_analyzed && (
                <div className="p-4 bg-slate-900 text-slate-100 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                      <ScanLine className="h-4 w-4" /> 2D Fast Fourier Transform (FFT) Deepfake Audit
                    </span>
                    <Badge
                      className={
                        forensicsData.deepfake_audit.is_ai_generated
                          ? 'bg-rose-500 text-white'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }
                    >
                      {forensicsData.deepfake_audit.is_ai_generated ? 'AI GENERATED SUSPECTED' : 'AUTHENTIC PHYSICAL SCAN'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
                    <div>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Radial energy roll-off ratio: <span className="text-white font-mono font-bold">{forensicsData.deepfake_audit.fft_data.spectral_energy_ratio}</span>.
                        Synthetic Diffusion/GAN models produce periodic checkerboard anomalies; this document exhibits authentic continuous paper/vector spectral properties.
                      </p>
                      <div className="mt-2 text-[11px] text-slate-500">
                        AI Generation Probability: <span className="text-emerald-400 font-bold">{Math.round(forensicsData.deepfake_audit.fft_data.synthetic_ai_score * 100)}%</span>
                      </div>
                    </div>
                    {forensicsData.deepfake_audit.fft_data.fft_spectrum_url && (
                      <div className="text-center">
                        <img
                          src={forensicsData.deepfake_audit.fft_data.fft_spectrum_url}
                          alt="FFT Frequency Domain Spectrum Heatmap"
                          className="h-28 mx-auto rounded-lg border border-slate-700 shadow-inner object-cover"
                        />
                        <span className="text-[10px] text-slate-500 mt-1 block">Frequency Magnitude Spectrum</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Physical Ink Signature Crops */}
              {forensicsData.deepfake_audit?.signature_data?.signature_crops?.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <FileCheck className="h-4 w-4 text-emerald-600" /> Isolated Physical Ink Signatures ({forensicsData.deepfake_audit.signature_data.signatures_detected} detected):
                  </span>
                  <div className="flex flex-wrap gap-3">
                    {forensicsData.deepfake_audit.signature_data.signature_crops.map((url: string, idx: number) => (
                      <div key={idx} className="p-2 bg-white rounded-lg border shadow-sm flex flex-col items-center">
                        <img src={url} alt={`Signature ${idx + 1}`} className="h-14 max-w-[140px] object-contain" />
                        <span className="text-[10px] text-slate-500 mt-1">Signatory {idx + 1}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {pdfForensicsResult?.details?.suspicious_flags &&
                pdfForensicsResult.details.suspicious_flags.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-amber-700">Flagged Metadata Anomalies:</span>
                    <ul className="list-disc list-inside text-xs text-slate-600 space-y-1">
                      {pdfForensicsResult.details.suspicious_flags.map((flag: string, i: number) => (
                        <li key={i}>{flag}</li>
                      ))}
                    </ul>
                  </div>
                )}
            </CardContent>
          </Card>

          {/* Card 6: QR Code & Digital Signature */}
          <Card className="shadow-sm border-slate-200">
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="text-base font-semibold">QR Code &amp; Digital Signature Verification</CardTitle>
              <CardDescription>Verification of embedded cryptographic signatures and encoded QR destination URLs</CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* QR Section */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <QrCode className="h-5 w-5 text-blue-600" />
                    <span className="font-semibold text-sm text-slate-900">QR Code Inspection</span>
                  </div>
                  {Array.isArray(qrData.qr_results) && qrData.qr_results.length > 0 ? (
                    qrData.qr_results.map((q: any, i: number) => (
                      <div key={i} className="p-3 rounded-lg border bg-slate-50 text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-slate-700 truncate max-w-[200px]">{q.domain || q.raw_data}</span>
                          <Badge variant={q.domain_type === 'OFFICIAL' ? 'success' : q.is_suspicious ? 'destructive' : 'blue'}>
                            {q.domain_type || 'SCANNED'}
                          </Badge>
                        </div>
                        {q.is_url && (
                          <a
                            href={q.raw_data}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-600 hover:underline block truncate"
                          >
                            {q.raw_data}
                          </a>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-500 italic bg-slate-50 p-3 rounded-lg border">
                      No QR codes detected on document canvas.
                    </p>
                  )}
                </div>

                {/* Digital Signature Section */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <FileCheck className="h-5 w-5 text-purple-600" />
                    <span className="font-semibold text-sm text-slate-900">Cryptographic PDF Signature</span>
                  </div>
                  <div className="p-3 rounded-lg border bg-slate-50 text-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Digital Signature Status:</span>
                      {sigData.is_signed ? (
                        <Badge variant="success">Signed Authentic</Badge>
                      ) : sigData.has_signature_field ? (
                        <Badge variant="warning">Unsigned Field</Badge>
                      ) : (
                        <Badge variant="secondary">Not Applicable</Badge>
                      )}
                    </div>
                    {sigData.signer_name && (
                      <div>
                        <span className="text-slate-500 block text-[11px]">Signer Authority:</span>
                        <span className="font-semibold text-slate-800">{sigData.signer_name}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 7: Duplicate Detection */}
          <Card className="shadow-sm border-slate-200">
            <CardHeader className="border-b border-slate-100 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">Duplicate &amp; Template Forgery Detection</CardTitle>
                  <CardDescription>Visual perceptual hashing (pHash) and semantic text embedding similarity</CardDescription>
                </div>
                <Badge variant={dupResult?.status === 'PASS' ? 'success' : 'warning'}>
                  {dupResult?.finding_summary || 'Analyzed'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {Array.isArray(dupData.matches) && dupData.matches.length > 0 ? (
                <div className="space-y-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Matched File</TableHead>
                        <TableHead>Uploaded</TableHead>
                        <TableHead>Visual Similarity</TableHead>
                        <TableHead>Text Similarity</TableHead>
                        <TableHead>Classification</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dupData.matches.map((m: any, i: number) => {
                        const imgPct = (Number(m.img_similarity) || 0) * 100;
                        const txtPct = (Number(m.text_similarity) || 0) * 100;
                        const matchType = typeof m.match_type === 'string' ? m.match_type.replace(/_/g, ' ') : 'MATCH';
                        return (
                          <TableRow key={i}>
                            <TableCell className="font-medium text-xs text-slate-900">{m.filename || 'Unknown'}</TableCell>
                            <TableCell className="text-xs text-slate-500">{m.upload_date || '—'}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Progress value={imgPct} className="w-16" />
                                <span className="font-mono text-xs font-semibold">{imgPct.toFixed(0)}%</span>
                              </div>
                            </TableCell>
                            <TableCell className="font-mono text-xs">{txtPct.toFixed(0)}%</TableCell>
                            <TableCell>
                              <Badge variant={m.match_type === 'EXACT' ? 'destructive' : 'warning'}>
                                {matchType}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                  <p className="text-xs text-slate-400 italic">
                    Note: A template match does not always signify fraud (e.g. shared institutional certificate formats). Manual audit is recommended.
                  </p>
                </div>
              ) : (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
                  <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
                  <span>
                    No perceptual hash or text hash duplicates identified in the system repository. Document appears visually and semantically unique.
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};
