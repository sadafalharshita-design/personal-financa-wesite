import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { ArrowRight, BadgeIndianRupee, BrainCircuit, ChartSpline, Check, FileScan, ShieldCheck, Sparkles, Target } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { formatINR } from "@/lib/format";

const features = [
  { icon: BrainCircuit, title: "Behavior intelligence", copy: "Understand the patterns behind your spending—not just category totals." },
  { icon: ChartSpline, title: "What-If engine", copy: "Turn a plain-language decision into deterministic 1, 3, 6 and 12-month projections." },
  { icon: Target, title: "Goal acceleration", copy: "See exactly how a habit change can bring your next milestone closer." },
  { icon: FileScan, title: "Structured finance", copy: "One secure place for accounts, transactions, budgets and long-term goals." },
];

export default function Home() {
  return (
    <div className="min-h-screen overflow-hidden bg-[#070a10] text-slate-50">
      <nav className="fixed inset-x-0 top-0 z-50 border-b border-white/8 bg-[#070a10]/80 backdrop-blur-xl" data-testid="landing-navigation">
        <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-5 lg:px-8">
          <Link to="/" className="flex items-center gap-3" data-testid="landing-logo-link"><span className="grid h-9 w-9 place-items-center rounded-xl bg-[#00f5a0] text-[#07110c]"><BadgeIndianRupee size={21} /></span><span className="font-heading text-xl font-bold">Wealth</span></Link>
          <div className="flex items-center gap-2"><Link to="/sign-in" className={buttonVariants({ variant: "ghost" })} data-testid="landing-sign-in-link">Sign in</Link><Link to="/sign-up" className={buttonVariants({ variant: "default" }) + " bg-[#00f5a0] text-[#07110c] hover:bg-[#3fffb8]"} data-testid="landing-hero-cta">Get started <ArrowRight size={16} /></Link></div>
        </div>
      </nav>

      <main>
        <section className="relative mx-auto grid min-h-[780px] max-w-7xl items-center gap-16 px-5 pb-20 pt-32 lg:grid-cols-[1.05fr_.95fr] lg:px-8">
          <div className="pointer-events-none absolute left-[58%] top-32 h-96 w-96 rounded-full bg-[#00f5a0]/8 blur-[110px]" />
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .6 }} className="relative z-10 text-left">
            <div className="eyebrow" data-testid="landing-eyebrow"><Sparkles size={14} /> AI-powered financial decision support</div>
            <h1 className="mt-7 max-w-3xl font-heading text-5xl font-bold leading-[.97] tracking-[-.05em] sm:text-6xl lg:text-7xl" data-testid="landing-headline">Understand your money.<br /><span className="text-[#00f5a0]">Simulate your future.</span></h1>
            <p className="mt-7 max-w-xl text-base leading-8 text-slate-300 sm:text-lg" data-testid="landing-supporting-copy">Wealth connects your real financial activity to the decisions ahead—so you can test a change before you live with it.</p>
            <div className="mt-9 flex flex-wrap gap-3"><Link to="/sign-in" className={buttonVariants({ size: "lg" }) + " bg-[#00f5a0] text-[#07110c] hover:bg-[#3fffb8]"} data-testid="landing-demo-signin-button">Try the live demo <ArrowRight size={17} /></Link><a href="#how-it-works" className={buttonVariants({ size: "lg", variant: "outline" }) + " border-white/15 bg-white/[.03]"} data-testid="landing-learn-more-link">See how it works</a></div>
            <div className="mt-9 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-400" data-testid="landing-trust-row"><span className="flex items-center gap-2"><ShieldCheck size={15} className="text-[#00f5a0]" /> Secure ownership controls</span><span className="flex items-center gap-2"><Check size={15} className="text-[#00f5a0]" /> Deterministic calculations</span></div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: .7, delay: .15 }} className="relative z-10" data-testid="landing-product-preview">
            <div className="simulator-frame">
              <div className="flex items-center justify-between border-b border-white/8 pb-4"><div><p className="eyebrow !border-0 !bg-transparent !p-0"><Sparkles size={13} /> Ask Wealth</p><p className="mt-2 text-sm text-slate-400">Scenario decision engine</p></div><span className="status-dot">Live preview</span></div>
              <div className="mt-5 rounded-xl border border-[#00f5a0]/25 bg-[#00f5a0]/[.05] p-4 font-medium" data-testid="landing-preview-query">What if I save ₹3,000 more every month?</div>
              <div className="my-6 grid grid-cols-[1fr_auto_1fr] items-center gap-4"><div><p className="metric-label">Current savings</p><p className="money-value text-2xl" data-testid="landing-current-savings">{formatINR(13000)}</p></div><ArrowRight className="text-slate-600" /><div><p className="metric-label">What-If savings</p><p className="money-value text-2xl text-[#00f5a0]" data-testid="landing-simulated-savings">{formatINR(16000)}</p></div></div>
              <div className="chart-mock" data-testid="landing-projection-chart"><svg viewBox="0 0 500 150" className="h-full w-full" preserveAspectRatio="none"><path d="M0 134 C120 118 260 92 500 52" fill="none" stroke="#475569" strokeWidth="3" strokeDasharray="6 7"/><path d="M0 134 C130 110 280 66 500 12" fill="none" stroke="#00f5a0" strokeWidth="4"/><defs><linearGradient id="g" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#00f5a0" stopOpacity=".2"/><stop offset="1" stopColor="#00f5a0" stopOpacity="0"/></linearGradient></defs><path d="M0 134 C130 110 280 66 500 12 L500 150 L0 150Z" fill="url(#g)"/></svg></div>
              <div className="mt-5 flex items-center justify-between rounded-xl bg-white/[.04] p-4"><div><p className="metric-label">12-month impact</p><p className="money-value text-xl text-cyan-300">+₹36,000</p></div><div className="text-right"><p className="metric-label">Goal closer by</p><p className="font-heading text-xl font-semibold">2 months</p></div></div>
            </div>
          </motion.div>
        </section>

        <section id="how-it-works" className="border-y border-white/8 bg-[#0a0e17] py-24">
          <div className="mx-auto max-w-7xl px-5 lg:px-8"><div className="max-w-2xl"><p className="section-kicker" data-testid="landing-platform-kicker">From records to decisions</p><h2 className="mt-4 font-heading text-3xl font-bold tracking-tight sm:text-5xl" data-testid="landing-platform-heading">Not another expense tracker.</h2><p className="mt-5 text-slate-400" data-testid="landing-platform-copy">Every feature feeds a decision layer that helps you understand what changes next.</p></div><div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">{features.map(({ icon: Icon, title, copy }, index) => <article key={title} className={`feature-card ${index === 1 ? "md:translate-y-6" : ""}`} data-testid={`landing-feature-${index}`}><Icon className="mb-8 text-[#00f5a0]" size={24} /><p className="text-xs font-mono text-slate-600">0{index + 1}</p><h3 className="mt-3 font-heading text-xl font-semibold">{title}</h3><p className="mt-3 text-sm leading-6 text-slate-400">{copy}</p></article>)}</div></div>
        </section>
      </main>
      <footer className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-10 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between lg:px-8" data-testid="landing-footer"><p>© 2026 Wealth. Built for better financial decisions.</p><p>Projections are estimates. Actual results may differ.</p></footer>
    </div>
  );
}