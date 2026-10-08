import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import AppShell from "@/components/AppShell";
import { apiGet } from "@/lib/api";
import type { User } from "@/lib/types";
import Home from "@/pages/Home";
import Auth from "@/pages/Auth";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import Accounts from "@/pages/Accounts";
import Transactions from "@/pages/Transactions";
import Budget from "@/pages/Budget";
import Goals from "@/pages/Goals";
import WhatIf from "@/pages/WhatIf";

function ProtectedPage({ children, bare = false }: { children: ReactNode; bare?: boolean }) {
  const location = useLocation();
  const { data: user, isLoading, isError } = useQuery({ queryKey: ["session"], queryFn: () => apiGet<User>("/auth/me"), retry: false });
  if (isLoading) return <div className="grid min-h-screen place-items-center bg-[#070a10] text-sm text-slate-500" data-testid="session-loading-state">Securing your Wealth workspace…</div>;
  if (isError || !user) return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  if (!user.onboarded && !bare) return <Navigate to="/onboarding" replace />;
  if (user.onboarded && bare) return <Navigate to="/dashboard" replace />;
  return bare ? children : <AppShell user={user}>{children}</AppShell>;
}

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <>
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/sign-in" element={<Auth />} />
      <Route path="/sign-up" element={<Auth />} />
      <Route path="/onboarding" element={<ProtectedPage bare><Onboarding /></ProtectedPage>} />
      <Route path="/dashboard" element={<ProtectedPage><Dashboard /></ProtectedPage>} />
      <Route path="/accounts" element={<ProtectedPage><Accounts /></ProtectedPage>} />
      <Route path="/transactions" element={<ProtectedPage><Transactions /></ProtectedPage>} />
      <Route path="/budget" element={<ProtectedPage><Budget /></ProtectedPage>} />
      <Route path="/goals" element={<ProtectedPage><Goals /></ProtectedPage>} />
      <Route path="/what-if" element={<ProtectedPage><WhatIf /></ProtectedPage>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    <Toaster richColors />
    </>
  );
}
