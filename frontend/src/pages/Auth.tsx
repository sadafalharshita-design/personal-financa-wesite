import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, BadgeIndianRupee, CheckCircle2, LockKeyhole } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiPost } from "@/lib/api";
import { friendlyError } from "@/lib/format";
import { beginSession } from "@/lib/session";
import type { AuthResponse } from "@/lib/types";

export default function Auth() {
  const isSignup = useLocation().pathname === "/sign-up";
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState(isSignup ? "" : "rahul@wealth.demo");
  const [password, setPassword] = useState(isSignup ? "" : "WealthDemo123!");
  const mutation = useMutation({
    mutationFn: () => apiPost<AuthResponse>(isSignup ? "/auth/signup" : "/auth/login", { email, password, name: isSignup ? name : null }),
    onSuccess: async ({ user }) => { await beginSession(); toast.success(isSignup ? "Your workspace is ready" : `Welcome back, ${user.name.split(" ")[0]}`); navigate(user.onboarded ? "/dashboard" : "/onboarding"); },
    onError: (error) => toast.error(friendlyError(error)),
  });
  return (
    <div className="grid min-h-screen bg-[#070a10] text-slate-50 lg:grid-cols-[1.1fr_.9fr]">
      <section className="relative hidden overflow-hidden border-r border-white/8 p-12 lg:flex lg:flex-col lg:justify-between" data-testid="auth-brand-panel"><div className="absolute -left-20 top-1/3 h-80 w-80 rounded-full bg-cyan-400/8 blur-[120px]" /><Link to="/" className="relative flex items-center gap-3" data-testid="auth-logo-link"><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#00f5a0] text-[#07110c]"><BadgeIndianRupee /></span><span className="font-heading text-xl font-bold">Wealth</span></Link><div className="relative max-w-xl"><p className="section-kicker" data-testid="auth-kicker">Financial decision intelligence</p><h1 className="mt-5 font-heading text-5xl font-bold leading-tight tracking-tight" data-testid="auth-heading">Build conviction before you change your money.</h1><div className="mt-10 space-y-4">{["Real financial data, persisted securely", "Scenario calculations that AI cannot alter", "Built around Indian money habits"].map((text, index) => <p key={text} className="flex items-center gap-3 text-sm text-slate-300" data-testid={`auth-benefit-${index}`}><CheckCircle2 size={18} className="text-[#00f5a0]" />{text}</p>)}</div></div><p className="relative text-xs text-slate-600">Decision support, not financial advice.</p></section>
      <section className="flex items-center justify-center p-5 sm:p-10">
        <Card className="w-full max-w-md border-white/10 bg-[#0f1420] text-slate-50 shadow-2xl" data-testid="auth-card"><CardHeader className="space-y-3"><div className="mb-3 grid h-11 w-11 place-items-center rounded-xl border border-[#00f5a0]/20 bg-[#00f5a0]/10 text-[#00f5a0]"><LockKeyhole size={20} /></div><CardTitle className="font-heading text-3xl">{isSignup ? "Create your Wealth space" : "Welcome back"}</CardTitle><p className="text-sm text-slate-400" data-testid="auth-description">{isSignup ? "Start with your real financial baseline." : "Continue to your financial command center."}</p></CardHeader><CardContent>
          <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); mutation.mutate(); }} data-testid="auth-form">
            {isSignup && <div className="space-y-2"><Label htmlFor="name">Full name</Label><Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Aarav Mehta" required data-testid="auth-name-input" /></div>}
            <div className="space-y-2"><Label htmlFor="email">Email address</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="auth-email-input" /></div>
            <div className="space-y-2"><Label htmlFor="password">Password</Label><Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required data-testid="auth-password-input" /></div>
            {!isSignup && <div className="rounded-xl border border-cyan-400/15 bg-cyan-400/[.04] p-3 text-xs text-slate-400" data-testid="demo-credentials-note">Demo credentials are pre-filled. Sign in to explore a data-rich account.</div>}
            <Button type="submit" disabled={mutation.isPending} className="h-11 w-full bg-[#00f5a0] text-[#07110c] hover:bg-[#3fffb8]" data-testid="auth-submit-button">{mutation.isPending ? "Securing session…" : isSignup ? "Create account" : "Sign in to Wealth"}<ArrowRight size={16} /></Button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-500" data-testid="auth-switch-copy">{isSignup ? "Already have an account?" : "New to Wealth?"} <Link to={isSignup ? "/sign-in" : "/sign-up"} className="font-semibold text-[#00f5a0] hover:underline" data-testid="auth-switch-link">{isSignup ? "Sign in" : "Create account"}</Link></p>
        </CardContent></Card>
      </section>
    </div>
  );
}