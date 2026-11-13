import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  Loader2,
  UploadCloud,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { getDashboardStatsApi } from '../api/dashboard';
import { DashboardStats } from '../types';
import { StatCard } from '../components/dashboard/StatCard';
import { UploadsChart } from '../components/dashboard/UploadsChart';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getDashboardStatsApi();
        setStats(data);
      } catch (err) {
        console.error('Failed to load dashboard statistics:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge variant="success">Completed</Badge>;
      case 'PROCESSING':
      case 'PENDING':
        return <Badge variant="warning">In Progress</Badge>;
      case 'FAILED':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">Unknown</Badge>;
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
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Workspace Overview</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time analytics and certificate verification activity
          </p>
        </div>
        <Link to="/upload">
          <Button className="bg-blue-600 hover:bg-blue-700 shadow-sm shadow-blue-500/20">
            <UploadCloud className="h-4 w-4 mr-2" />
            Upload Certificate &rarr;
          </Button>
        </Link>
      </div>

      {/* Row 1: 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Total Uploads"
          value={stats?.total_uploads || 0}
          icon={FileText}
          colorClass="bg-blue-50 text-blue-600"
          subtitle="Processed in account"
        />
        <StatCard
          title="Verified Authentic"
          value={stats?.verified_count || 0}
          icon={CheckCircle2}
          colorClass="bg-emerald-50 text-emerald-600"
          subtitle="Low forensic risk"
        />
        <StatCard
          title="Suspicious Flags"
          value={stats?.suspicious_count || 0}
          icon={AlertTriangle}
          colorClass="bg-red-50 text-red-600"
          subtitle="Requires human audit"
        />
        <StatCard
          title="In Verification"
          value={stats?.processing_count || 0}
          icon={Clock}
          colorClass="bg-amber-50 text-amber-600"
          subtitle="Active pipeline queue"
        />
      </div>

      {/* Row 2: Chart */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base font-semibold">Upload Activity</CardTitle>
              <CardDescription>Daily certificate volume over the past 7 days</CardDescription>
            </div>
            <div className="text-xs text-slate-500 font-medium">
              Average Risk Score: <span className="font-bold text-slate-800">{stats?.avg_risk_score || 0}/100</span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <UploadsChart data={stats?.uploads_by_day || []} />
        </CardContent>
      </Card>

      {/* Row 3: Recent Uploads */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-4 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold">Recent Verifications</CardTitle>
            <CardDescription>Most recent documents submitted for AI verification</CardDescription>
          </div>
          <Link to="/history">
            <Button variant="ghost" size="sm" className="text-xs text-blue-600 hover:text-blue-700">
              View All History <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          {stats?.recent_uploads && stats.recent_uploads.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filename</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Submitted</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Verdict</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats.recent_uploads.map((cert) => (
                  <TableRow key={cert.certificate_id}>
                    <TableCell className="font-medium text-slate-900 max-w-[200px] truncate">
                      {cert.filename}
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-700 border">
                        {cert.file_type}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {formatDistanceToNow(new Date(cert.created_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell>{getStatusBadge(cert.status)}</TableCell>
                    <TableCell>{getVerdictBadge(cert.final_verdict)}</TableCell>
                    <TableCell className="text-right">
                      {cert.job_id && (
                        <Link
                          to={`/verify/${cert.job_id}`}
                          className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-2.5 h-7 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
                        >
                          Inspect <ExternalLink className="h-3 w-3 ml-1" />
                        </Link>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="py-12 text-center">
              <UploadCloud className="h-10 w-10 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-600">No verification jobs submitted yet</p>
              <p className="text-xs text-slate-400 mt-1 mb-4">
                Upload your first certificate document to run AI forgery and validation checks.
              </p>
              <Link to="/upload">
                <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                  Upload Document Now
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

