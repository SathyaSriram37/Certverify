import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { AdminRoute, ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';

// Code-split page components with dynamic imports for zero-lag initial render
const AdminPage = lazy(() => import('./pages/AdminPage').then(m => ({ default: m.AdminPage })));
const BatchVerifyPage = lazy(() => import('./pages/BatchVerifyPage').then(m => ({ default: m.BatchVerifyPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const DeveloperPage = lazy(() => import('./pages/DeveloperPage').then(m => ({ default: m.DeveloperPage })));
const HistoryPage = lazy(() => import('./pages/HistoryPage').then(m => ({ default: m.HistoryPage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('./pages/RegisterPage').then(m => ({ default: m.RegisterPage })));
const UploadPage = lazy(() => import('./pages/UploadPage').then(m => ({ default: m.UploadPage })));
const VerificationResultPage = lazy(() => import('./pages/VerificationResultPage').then(m => ({ default: m.VerificationResultPage })));

const PageLoader = () => (
  <div className="h-96 w-full flex flex-col items-center justify-center space-y-2">
    <Loader2 className="h-7 w-7 animate-spin text-blue-600" />
    <span className="text-xs text-slate-500 font-medium">Loading page...</span>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 30, // 30 seconds cache to prevent repeated API calls
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected Workspace Routes */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/batch" element={<BatchVerifyPage />} />
              <Route path="/developer" element={<DeveloperPage />} />
              <Route path="/verify/:jobId" element={<VerificationResultPage />} />
              <Route path="/history" element={<HistoryPage />} />
            </Route>

            {/* Admin Protected Routes */}
            <Route
              element={
                <AdminRoute>
                  <AppLayout />
                </AdminRoute>
              }
            >
              <Route path="/admin" element={<AdminPage />} />
            </Route>

            {/* Root Redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
