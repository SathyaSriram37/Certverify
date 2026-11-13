import React from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Code2,
  History,
  Layers,
  LayoutDashboard,
  LogOut,
  Shield,
  ShieldCheck,
  UploadCloud,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';

export const AppLayout: React.FC = () => {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearAuth();
    navigate('/login');
  };

  const getRoleBadgeVariant = (role?: string) => {
    if (role === 'ADMIN') return 'purple';
    if (role === 'HR_VERIFIER') return 'blue';
    return 'secondary';
  };

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Upload Certificate', path: '/upload', icon: UploadCloud },
    { label: 'Batch Verification', path: '/batch', icon: Layers },
    { label: 'Developer & B2B API', path: '/developer', icon: Code2 },
    { label: 'Verification History', path: '/history', icon: History },
  ];

  const isStaff = user?.role === 'ADMIN' || user?.role === 'HR_VERIFIER';

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-200 bg-white flex flex-col justify-between shrink-0">
        <div>
          {/* Brand header */}
          <div className="h-16 flex items-center px-6 border-b border-slate-100 gap-3">
            <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <span className="font-bold text-slate-900 tracking-tight block text-base">CertVerify AI</span>
              <span className="text-[10px] uppercase font-semibold text-blue-600 tracking-wider">Production SaaS</span>
            </div>
          </div>

          {/* Navigation links */}
          <nav className="p-4 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-50 text-blue-700 font-semibold'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    }`
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            })}

            {isStaff && (
              <>
                <div className="pt-4 pb-1 px-3">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Staff Administration
                  </span>
                </div>
                <NavLink
                  to="/admin"
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-purple-50 text-purple-700 font-semibold'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    }`
                  }
                >
                  <Shield className="h-4 w-4 text-purple-600" />
                  Admin Panel
                </NavLink>
              </>
            )}
          </nav>
        </div>

        {/* User Card at bottom of sidebar */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50 m-2 rounded-xl border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-900 truncate block max-w-[130px]">
              {user?.full_name || 'User'}
            </span>
            <Badge variant={getRoleBadgeVariant(user?.role)}>
              {user?.role || 'USER'}
            </Badge>
          </div>
          <span className="text-[11px] text-slate-500 truncate block mb-3">
            {user?.email}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="w-full text-xs h-8 text-slate-600 hover:text-red-600 hover:border-red-200"
          >
            <LogOut className="h-3.5 w-3.5 mr-2" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <header className="h-16 border-b border-slate-200 bg-white px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-500">Universal AI Certificate Verification</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/upload">
              <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-xs">
                <UploadCloud className="h-3.5 w-3.5 mr-1.5" />
                New Verification
              </Button>
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

