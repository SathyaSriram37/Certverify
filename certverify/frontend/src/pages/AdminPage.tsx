import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import {
  AlertTriangle,
  Clock,
  ExternalLink,
  FileText,
  LineChart as LineChartIcon,
  Loader2,
  Search,
  Shield,
  Users,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { format } from 'date-fns';
import {
  getAdminCertificatesApi,
  getAdminStatsApi,
  getAdminUsersApi,
  updateAdminUserApi,
} from '../api/admin';
import { useAuthStore } from '../store/authStore';
import { AdminCertificateItem, AdminStats, AdminUserItem } from '../types';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

export const AdminPage: React.FC = () => {
  const { user } = useAuthStore();
  const [tab, setTab] = useState('overview');

  // Stats state
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  // Users tab state
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [usersPage, setUsersPage] = useState(1);
  const [usersTotalPages, setUsersTotalPages] = useState(1);
  const [searchUser, setSearchUser] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState('');
  const [loadingUsers, setLoadingUsers] = useState(false);

  // Certificates tab state
  const [certs, setCerts] = useState<AdminCertificateItem[]>([]);
  const [certsPage, setCertsPage] = useState(1);
  const [certsTotalPages, setCertsTotalPages] = useState(1);
  const [verdictFilter, setVerdictFilter] = useState('');
  const [loadingCerts, setLoadingCerts] = useState(false);

  // Restrict access
  if (user?.role !== 'ADMIN' && user?.role !== 'HR_VERIFIER') {
    return <Navigate to="/dashboard" replace />;
  }

  // Fetch stats on mount
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getAdminStatsApi();
        setStats(data);
      } catch (err) {
        console.error('Failed to load admin stats:', err);
      } finally {
        setLoadingStats(false);
      }
    };
    fetchStats();
  }, []);

  // Fetch users when tab/filters change
  useEffect(() => {
    if (tab !== 'users') return;
    const fetchUsers = async () => {
      setLoadingUsers(true);
      try {
        const res = await getAdminUsersApi(
          usersPage,
          10,
          searchUser || undefined,
          userRoleFilter || undefined
        );
        setUsers(res.items);
        setUsersTotalPages(res.pages);
      } catch (err) {
        console.error('Failed to load users:', err);
      } finally {
        setLoadingUsers(false);
      }
    };

    const timer = setTimeout(() => {
      fetchUsers();
    }, 300);

    return () => clearTimeout(timer);
  }, [tab, usersPage, searchUser, userRoleFilter]);

  // Fetch certificates when certs tab changes
  useEffect(() => {
    if (tab !== 'certificates') return;
    const fetchCerts = async () => {
      setLoadingCerts(true);
      try {
        const res = await getAdminCertificatesApi(
          certsPage,
          10,
          verdictFilter || undefined
        );
        setCerts(res.items);
        setCertsTotalPages(res.pages);
      } catch (err) {
        console.error('Failed to load certificates:', err);
      } finally {
        setLoadingCerts(false);
      }
    };
    fetchCerts();
  }, [tab, certsPage, verdictFilter]);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await updateAdminUserApi(userId, { role: newRole });
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole as any } : u))
      );
    } catch (err) {
      console.error('Failed to update role:', err);
    }
  };

  const handleActiveToggle = async (userId: string, newActive: boolean) => {
    try {
      await updateAdminUserApi(userId, { is_active: newActive });
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: newActive } : u))
      );
    } catch (err) {
      console.error('Failed to update user active status:', err);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <Shield className="h-6 w-6 text-purple-600" />
          Enterprise Administration Panel
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage system users, view system-wide verification metrics, and inspect flagged credentials
        </p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-slate-200/60 p-1 rounded-lg">
          <TabsTrigger value="overview">System Overview</TabsTrigger>
          <TabsTrigger value="users">User Management</TabsTrigger>
          <TabsTrigger value="certificates">All Certificates &amp; Audits</TabsTrigger>
        </TabsList>

        {/* TAB 1: OVERVIEW */}
        <TabsContent value="overview" className="space-y-6 mt-6">
          {loadingStats ? (
            <div className="h-64 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <Card>
                  <CardContent className="p-6 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                        Registered Accounts
                      </p>
                      <h3 className="text-3xl font-bold text-slate-900">{stats?.total_users || 0}</h3>
                      <p className="text-xs text-slate-400 mt-1">Platform wide</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                      <Users className="h-6 w-6" />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                        Total Certificates
                      </p>
                      <h3 className="text-3xl font-bold text-slate-900">{stats?.total_certificates || 0}</h3>
                      <p className="text-xs text-slate-400 mt-1">Stored in database</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                      <FileText className="h-6 w-6" />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                        Suspicious This Week
                      </p>
                      <h3 className="text-3xl font-bold text-red-600">{stats?.suspicious_this_week || 0}</h3>
                      <p className="text-xs text-slate-400 mt-1">Flagged for inspection</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
                      <AlertTriangle className="h-6 w-6" />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                        Avg Pipeline Duration
                      </p>
                      <h3 className="text-3xl font-bold text-slate-900">
                        {stats?.avg_processing_seconds || 0}s
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">Throughput speed</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                      <Clock className="h-6 w-6" />
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* 30 Days Line Chart */}
              <Card>
                <CardHeader className="border-b border-slate-100 pb-4">
                  <div className="flex items-center gap-2">
                    <LineChartIcon className="h-5 w-5 text-purple-600" />
                    <div>
                      <CardTitle className="text-base font-semibold">System Upload Trajectory (30 Days)</CardTitle>
                      <CardDescription>Daily verified document volume across all enterprise organizations</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={stats?.daily_uploads_30d || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="date" tickLine={false} axisLine={{ stroke: '#e2e8f0' }} tick={{ fontSize: 11, fill: '#64748b' }} />
                        <YAxis allowDecimals={false} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} tick={{ fontSize: 11, fill: '#64748b' }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1e293b',
                            borderRadius: '8px',
                            border: 'none',
                            color: '#ffffff',
                            fontSize: '12px',
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="count"
                          name="Daily Certs"
                          stroke="#8b5cf6"
                          strokeWidth={2.5}
                          dot={{ r: 3, fill: '#8b5cf6' }}
                          activeDot={{ r: 6 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* TAB 2: USERS */}
        <TabsContent value="users" className="space-y-4 mt-6">
          <Card>
            <CardHeader className="border-b border-slate-100 pb-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <CardTitle className="text-base font-semibold">User Directory &amp; RBAC Control</CardTitle>
                  <CardDescription>Grant staff privileges and toggle user account access</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <Input
                      placeholder="Search name or email..."
                      value={searchUser}
                      onChange={(e) => setSearchUser(e.target.value)}
                      className="pl-8 h-8 text-xs w-48 sm:w-60"
                    />
                  </div>
                  <select
                    value={userRoleFilter}
                    onChange={(e) => setUserRoleFilter(e.target.value)}
                    className="h-8 rounded-md border border-slate-300 bg-white px-2.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-purple-500"
                  >
                    <option value="">All Roles</option>
                    <option value="USER">USER</option>
                    <option value="ADMIN">ADMIN</option>
                    <option value="HR_VERIFIER">HR_VERIFIER</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {loadingUsers ? (
                <div className="h-48 flex items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-purple-600" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>User</TableHead>
                      <TableHead>Assigned Role</TableHead>
                      <TableHead>Active Status</TableHead>
                      <TableHead>Uploads</TableHead>
                      <TableHead>Registered</TableHead>
                      <TableHead className="text-right">Change Role</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((u) => (
                      <TableRow key={u.id}>
                        <TableCell>
                          <div>
                            <span className="font-semibold text-slate-900 block text-xs">{u.full_name}</span>
                            <span className="text-[11px] text-slate-500 font-mono">{u.email}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              u.role === 'ADMIN' ? 'purple' : u.role === 'HR_VERIFIER' ? 'blue' : 'secondary'
                            }
                          >
                            {u.role}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={u.is_active}
                              onCheckedChange={(checked) => handleActiveToggle(u.id, checked)}
                            />
                            <span className="text-xs text-slate-600">
                              {u.is_active ? 'Active' : 'Deactivated'}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{u.upload_count}</TableCell>
                        <TableCell className="text-xs text-slate-500">
                          {format(new Date(u.created_at), 'dd MMM yyyy')}
                        </TableCell>
                        <TableCell className="text-right">
                          <select
                            value={u.role}
                            onChange={(e) => handleRoleChange(u.id, e.target.value)}
                            className="h-7 text-xs rounded border border-slate-300 bg-white px-2 text-slate-700"
                          >
                            <option value="USER">USER</option>
                            <option value="HR_VERIFIER">HR_VERIFIER</option>
                            <option value="ADMIN">ADMIN</option>
                          </select>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}

              {usersTotalPages > 1 && (
                <div className="border-t border-slate-100 p-4 flex items-center justify-between">
                  <span className="text-xs text-slate-500">
                    Page {usersPage} of {usersTotalPages}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={usersPage <= 1}
                      onClick={() => setUsersPage((p) => p - 1)}
                      className="text-xs"
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={usersPage >= usersTotalPages}
                      onClick={() => setUsersPage((p) => p + 1)}
                      className="text-xs"
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: ALL CERTIFICATES */}
        <TabsContent value="certificates" className="space-y-4 mt-6">
          <Card>
            <CardHeader className="border-b border-slate-100 pb-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <CardTitle className="text-base font-semibold">Master Certificate Audit Ledger</CardTitle>
                  <CardDescription>All certificates uploaded by users across the application</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={verdictFilter}
                    onChange={(e) => setVerdictFilter(e.target.value)}
                    className="h-8 rounded-md border border-slate-300 bg-white px-2.5 text-xs text-slate-700 focus:outline-none"
                  >
                    <option value="">All Verdicts</option>
                    <option value="VERIFIED">VERIFIED</option>
                    <option value="SUSPICIOUS">SUSPICIOUS (Alerts)</option>
                    <option value="UNABLE_TO_VERIFY">UNABLE_TO_VERIFY</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {loadingCerts ? (
                <div className="h-48 flex items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-purple-600" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Filename</TableHead>
                      <TableHead>Account Owner</TableHead>
                      <TableHead>Format</TableHead>
                      <TableHead>Uploaded</TableHead>
                      <TableHead>Risk Score</TableHead>
                      <TableHead>Verdict</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {certs.map((c) => (
                      <TableRow
                        key={c.id}
                        className={
                          c.is_suspicious ? 'bg-red-50/60 border-l-4 border-l-red-500' : ''
                        }
                      >
                        <TableCell className="font-semibold text-xs text-slate-900 max-w-[180px] truncate">
                          {c.original_filename}
                        </TableCell>
                        <TableCell className="text-xs text-slate-600 font-mono">
                          {c.user_email}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-slate-100 border">
                            {c.file_type}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs text-slate-500">
                          {format(new Date(c.created_at), 'dd MMM yyyy')}
                        </TableCell>
                        <TableCell className="font-mono text-xs font-bold">
                          {c.risk_score !== null && c.risk_score !== undefined
                            ? `${c.risk_score}/100`
                            : '—'}
                        </TableCell>
                        <TableCell>
                          {c.final_verdict === 'VERIFIED' ? (
                            <Badge variant="success">Verified</Badge>
                          ) : c.final_verdict === 'SUSPICIOUS' ? (
                            <Badge variant="destructive">Suspicious</Badge>
                          ) : (
                            <Badge variant="secondary">In Progress</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {c.job_id && (
                            <Link to={`/verify/${c.job_id}`}>
                              <Button variant="outline" size="sm" className="h-7 text-xs">
                                Inspect <ExternalLink className="h-3 w-3 ml-1" />
                              </Button>
                            </Link>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}

              {certsTotalPages > 1 && (
                <div className="border-t border-slate-100 p-4 flex items-center justify-between">
                  <span className="text-xs text-slate-500">
                    Page {certsPage} of {certsTotalPages}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={certsPage <= 1}
                      onClick={() => setCertsPage((p) => p - 1)}
                      className="text-xs"
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={certsPage >= certsTotalPages}
                      onClick={() => setCertsPage((p) => p + 1)}
                      className="text-xs"
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

