import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowLeftRight, BadgeIndianRupee, ChartNoAxesCombined, ChevronRight,
  CircleGauge, Landmark, LogOut, Menu, ScanLine, Sparkles, Target, WalletCards, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { endSession } from "@/lib/session";
import type { User } from "@/lib/types";

const NAV = [
  { to: "/dashboard", label: "Overview", icon: CircleGauge, testId: "nav-overview-link" },
  { to: "/accounts", label: "Accounts", icon: Landmark, testId: "nav-accounts-link" },
  { to: "/transactions", label: "Transactions", icon: ArrowLeftRight, testId: "nav-transactions-link" },
  { to: "/budget", label: "Budget", icon: WalletCards, testId: "nav-budgets-link" },
  { to: "/goals", label: "Goals", icon: Target, testId: "nav-goals-link" },
  { to: "/scan", label: "Receipt Scanner", icon: ScanLine, testId: "nav-receipt-scanner-link" },
  { to: "/what-if", label: "What-If Simulator", icon: Sparkles, testId: "nav-what-if-link" },
];

function NavContent({ close }: { close?: () => void }) {
  return (
    <nav className="space-y-1" data-testid="primary-navigation">
      {NAV.map(({ to, label, icon: Icon, testId }) => (
        <NavLink key={to} to={to} onClick={close} data-testid={testId} className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}>
          <Icon size={18} /><span>{label}</span>{label === "What-If Simulator" && <span className="ml-auto h-2 w-2 rounded-full bg-[#00f5a0] shadow-[0_0_10px_#00f5a0]" />}
        </NavLink>
      ))}
    </nav>
  );
}

export default function AppShell({ user, children }: { user: User; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const active = NAV.find((item) => location.pathname.startsWith(item.to))?.label ?? "Wealth";

  async function logout() {
    await endSession();
    navigate("/");
  }

  return (
    <div className="min-h-screen bg-[#070a10] text-slate-50">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-white/8 bg-[#0a0e17] p-5 lg:flex lg:flex-col">
        <NavLink to="/dashboard" className="mb-10 flex items-center gap-3" data-testid="sidebar-wealth-logo">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#00f5a0] text-[#07110c]"><BadgeIndianRupee size={23} /></span>
          <span><span className="block font-heading text-xl font-bold">Wealth</span><span className="block text-[10px] uppercase tracking-[.2em] text-slate-500">Decision intelligence</span></span>
        </NavLink>
        <NavContent />
        <div className="mt-auto border-t border-white/8 pt-5">
          <div className="mb-3 flex items-center gap-3 px-2" data-testid="sidebar-user-profile">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-cyan-400/10 font-semibold text-cyan-300">{user.name.charAt(0)}</span>
            <span className="min-w-0"><span className="block truncate text-sm font-semibold">{user.name}</span><span className="block truncate text-xs text-slate-500">{user.email}</span></span>
          </div>
          <button onClick={logout} className="nav-link w-full" data-testid="sign-out-button"><LogOut size={17} /> Sign out</button>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/8 bg-[#070a10]/85 px-4 backdrop-blur-xl sm:px-7">
          <div className="flex items-center gap-3">
            <button onClick={() => setOpen(true)} className="icon-button lg:hidden" data-testid="mobile-menu-button" aria-label="Open navigation"><Menu size={20} /></button>
            <div><p className="text-[10px] uppercase tracking-[.2em] text-slate-500" data-testid="header-section-label">Command center</p><h1 className="font-heading text-base font-semibold" data-testid="header-active-page">{active}</h1></div>
          </div>
          <Button onClick={() => navigate("/transactions?new=1")} className="bg-[#00f5a0] text-[#07110c] hover:bg-[#3fffb8]" data-testid="header-add-transaction-button">Add transaction <ChevronRight size={16} /></Button>
        </header>
        <main className="mx-auto max-w-[1500px] p-4 sm:p-7">{children}</main>
      </div>

      <AnimatePresence>
        {open && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm lg:hidden" onClick={() => setOpen(false)} data-testid="mobile-navigation-overlay">
          <motion.aside initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} className="h-full w-72 border-r border-white/10 bg-[#0a0e17] p-5" onClick={(event) => event.stopPropagation()}>
            <div className="mb-8 flex items-center justify-between"><span className="font-heading text-xl font-bold">Wealth</span><button onClick={() => setOpen(false)} className="icon-button" data-testid="mobile-menu-close-button" aria-label="Close navigation"><X size={20} /></button></div>
            <NavContent close={() => setOpen(false)} />
          </motion.aside>
        </motion.div>}
      </AnimatePresence>
    </div>
  );
}