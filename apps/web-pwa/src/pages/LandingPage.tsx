import { LoginForm } from "@/features/auth/LoginForm";
import { homeForRoles } from "@/lib/role-routing";
import { useAuthStore } from "@splashh/api-client";
import {
  ArrowRight,
  Button,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock,
  CreditCard,
  LogIn,
  MapPin,
  Receipt,
  Waves,
  X,
  brand,
} from "@splashh/ui";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

type Mode = "customer" | "staff";

export function LandingPage() {
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<Mode>("customer");
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  const open = (mode: Mode) => {
    setAuthMode(mode);
    setAuthOpen(true);
  };
  const close = () => setAuthOpen(false);

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Top nav — Klook-inspired: brand left, links + CTAs right */}
      <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <Link
            to="/"
            className="inline-flex items-center gap-2 transition-opacity hover:opacity-80"
          >
            <Waves
              className="h-6 w-6 text-primary animate-swim-bob motion-reduce:animate-none"
              aria-hidden="true"
            />
            <span className="text-lg font-bold tracking-tight text-foreground">{brand.name}</span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            <NavLink to="#how">How it works</NavLink>
            <NavLink to="#pricing">Pricing</NavLink>
            <NavLink to="#help">Help</NavLink>
          </nav>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => open("customer")}>
              Log in
            </Button>
            <Button size="sm" onClick={() => open("customer")} className="group">
              Book a lane
              <ArrowRight className="h-4 w-4 transition-transform duration-250 ease-swim group-hover:translate-x-0.5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Hero — full bleed, dramatic, with carousel arrows */}
      <section className="relative overflow-hidden">
        {/* Background gradients */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(60% 60% at 85% 0%, color-mix(in oklab, var(--color-accent-cool) 24%, transparent), transparent 60%)," +
              "radial-gradient(40% 40% at 5% 100%, color-mix(in oklab, var(--color-accent-warm) 14%, transparent), transparent 70%)",
          }}
        />
        {/* Decorative blob shapes (Klook-inspired) */}
        <div
          aria-hidden
          className="pointer-events-none absolute -left-32 top-20 h-72 w-72 rounded-full bg-accent-warm/15 blur-3xl animate-swim-bob motion-reduce:animate-none"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute right-0 top-40 h-80 w-80 rounded-full bg-primary/20 blur-3xl animate-swim-bob motion-reduce:animate-none [animation-delay:-1.5s]"
        />
        {/* Subtle horizontal lane lines at bottom */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 bottom-0 h-24 opacity-[0.06]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg, hsl(199 73% 42%) 0 1px, transparent 1px 14px)",
          }}
        />

        <div className="relative mx-auto flex max-w-7xl flex-col px-6 pb-24 pt-16 sm:pb-28 sm:pt-20 lg:flex-row lg:items-center lg:gap-16 lg:pb-36 lg:pt-28">
          {/* Copy */}
          <div className="flex-1 text-center lg:text-left">
            <div className="mb-6 inline-flex items-center gap-2 rounded-none border-2 border-border bg-card px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground animate-rise-up motion-reduce:animate-none">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-volt opacity-60" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-volt" />
              </span>
              Sports club management platform
            </div>
            <h1 className="font-display text-[clamp(3rem,8vw,7rem)] font-bold leading-[0.92] tracking-tight animate-rise-up motion-reduce:animate-none [animation-delay:80ms]">
              <span className="block text-foreground">Run your club.</span>
              <span className="block text-muted-foreground/70">Not your</span>
              <span className="block text-volt">spreadsheet.</span>
            </h1>
            <p className="mt-7 max-w-xl text-pretty text-base text-muted-foreground sm:text-lg animate-rise-up motion-reduce:animate-none [animation-delay:240ms]">
              Manage bookings, memberships, payments, attendance, and operations from one powerful
              platform built specifically for sports clubs.
            </p>

            {/* CTAs */}
            <div className="mt-9 flex flex-col items-center gap-3 sm:flex-row sm:justify-center lg:justify-start animate-rise-up motion-reduce:animate-none [animation-delay:320ms]">
              <Button size="lg" onClick={() => open("customer")} className="group">
                Book a demo
                <ArrowRight className="h-4 w-4 transition-transform duration-250 ease-swim group-hover:translate-x-0.5" />
              </Button>
              <Button size="lg" variant="outline" onClick={() => open("staff")}>
                Explore platform
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Visual: floating UI cards (reference-style) */}
          <div className="mt-16 hidden flex-1 lg:block">
            <HeroFloatingCards />
          </div>
        </div>

        {/* Carousel arrows (Klook-inspired) */}
        <button
          type="button"
          aria-label="Previous"
          className="absolute left-4 top-1/2 hidden -translate-y-1/2 rounded-full bg-card/80 p-3 shadow-volt-sm backdrop-blur transition-all duration-250 ease-swim hover:scale-110 hover:bg-card lg:flex"
        >
          <ChevronRight className="h-5 w-5 rotate-180" />
        </button>
        <button
          type="button"
          aria-label="Next"
          className="absolute right-4 top-1/2 hidden -translate-y-1/2 rounded-full bg-card/80 p-3 shadow-volt-sm backdrop-blur transition-all duration-250 ease-swim hover:scale-110 hover:bg-card lg:flex"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </section>

      {/* Trust strip — grayscale sport icons, de-emphasized by default */}
      <section className="border-y border-border bg-charcoal-950 px-6 py-10">
        <div className="mx-auto max-w-6xl">
          <p className="text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-6">
            Built for the way sports clubs actually work
          </p>
          <ul className="flex flex-wrap items-center justify-center gap-3 sm:gap-4">
            {[
              { name: "Swimming", emoji: "🏊" },
              { name: "Badminton", emoji: "🏸" },
              { name: "Tennis", emoji: "🎾" },
              { name: "Gym", emoji: "🏋️" },
              { name: "Football", emoji: "⚽" },
              { name: "Cricket", emoji: "🏏" },
            ].map((s) => (
              <li
                key={s.name}
                className="group inline-flex items-center gap-2 rounded-none border-2 border-border bg-card/50 px-3 py-1.5 grayscale opacity-60 transition-all duration-300 hover:grayscale-0 hover:opacity-100"
              >
                <span aria-hidden className="text-base">
                  {s.emoji}
                </span>
                <span className="font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground group-hover:text-foreground">
                  {s.name}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Value props — three cards, each with its own illustration treatment */}
      <section id="how" className="border-t border-border bg-secondary/30 px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-2xl">
            <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              One platform, three jobs done well.
            </h2>
            <p className="mt-3 text-pretty text-muted-foreground">
              Bookings, front-desk check-ins, and money — wired to the same record so nothing
              drifts.
            </p>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            <FeatureCard
              tone="primary"
              eyebrow="Real-time"
              title="Lane, court, and pool availability."
              body="Members see open slots the moment a booking lands. No phone calls, no double-bookings."
              stat="< 1s"
              statLabel="slot refresh"
              illustration={<PoolIllustration />}
            />
            <FeatureCard
              tone="accent"
              eyebrow="Self-serve"
              title="Members book at midnight."
              body="Your front desk arrives to a tidy schedule, not a stack of voicemails."
              stat="24/7"
              statLabel="booking window"
              illustration={<CalendarIllustration />}
            />
            <FeatureCard
              tone="ink"
              eyebrow="One ledger"
              title="Every invoice accounted for."
              body="GST-ready invoices, Razorpay payments, refunds, and exports — one source of truth."
              stat="100%"
              statLabel="invoice trail"
              illustration={<LedgerIllustration />}
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            From booking to payment in three taps.
          </h2>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            Members open the app, pick a lane, and pay. You watch the books update in real time.
          </p>
          <ol className="mt-12 grid gap-8 md:grid-cols-3">
            <Step n={1} icon={<CalendarDays className="h-5 w-5" />} title="Member picks a slot">
              Members see open lanes and courts live. No more phone tag with the front desk.
            </Step>
            <Step n={2} icon={<CheckCircle2 className="h-5 w-5" />} title="They confirm in one tap">
              A clean booking record lands instantly. Front desk walks in to a tidy schedule.
            </Step>
            <Step n={3} icon={<CreditCard className="h-5 w-5" />} title="Money flows to one ledger">
              Razorpay takes the payment, GST-ready invoices generate, refunds and exports included.
            </Step>
          </ol>
        </div>
      </section>

      {/* Facility overview — bento grid showing every part of the club the platform covers */}
      <section className="border-t border-border bg-charcoal-950 px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-2xl">
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
              One platform. <span className="text-volt">Every part of your club.</span>
            </h2>
            <p className="mt-3 text-pretty text-muted-foreground">
              From the front desk to the back courts — manage your entire facility blueprint through
              a single unified system.
            </p>
          </div>

          <div className="grid auto-rows-[minmax(120px,auto)] grid-cols-1 gap-3 sm:grid-cols-4 sm:auto-rows-[120px]">
            {/* Swimming Pool — primary, spans 2 cols × 2 rows */}
            <FacilityCell
              colSpan="sm:col-span-2 sm:row-span-2"
              tone="volt"
              eyebrow="Swimming pool"
              title="42 / 50"
              subtitle="Active lane capacity"
              detail="3 sessions live"
              icon={<Waves className="h-5 w-5" />}
              delay={0}
            />
            {/* Badminton Courts — accent, 1 col × 2 rows */}
            <FacilityCell
              colSpan="sm:col-span-1 sm:row-span-2"
              tone="warm"
              eyebrow="Badminton"
              title="100%"
              subtitle="Booked tonight"
              detail="Peak hour pricing on"
              icon={<MapPin className="h-5 w-5" />}
              delay={80}
            />
            {/* Reception — 1 col × 1 row */}
            <FacilityCell
              colSpan="sm:col-span-1"
              tone="ink"
              eyebrow="Reception"
              title="Check-in"
              subtitle="QR + walk-in"
              delay={160}
            />
            {/* Cafe POS — 1 col × 1 row */}
            <FacilityCell
              colSpan="sm:col-span-1"
              tone="ink"
              eyebrow="Cafe POS"
              title="Orders"
              subtitle="Synced to ledger"
              delay={240}
            />
            {/* Gym & Academy Floor — full width strip */}
            <FacilityCell
              colSpan="sm:col-span-4"
              tone="ink"
              eyebrow="Gym & Academy Floor"
              title="124 members present"
              subtitle="Live across the building"
              accent="volt"
              delay={320}
            />
          </div>
        </div>
      </section>

      {/* Command Center — dashboard mockup with browser chrome + bar chart */}
      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <p className="font-display text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Command Center
            </p>
            <h2 className="mt-3 font-display text-[clamp(2rem,5vw,3.5rem)] font-bold leading-[0.95] tracking-tight">
              <span className="block text-foreground">Your entire business.</span>
              <span className="block text-muted-foreground/70">At a glance.</span>
            </h2>
          </div>

          {/* Browser-chrome window */}
          <div className="rounded-none border-2 border-border bg-card shadow-volt-md">
            {/* Window chrome */}
            <div className="flex items-center justify-between rounded-t-xl border-b border-border bg-charcoal-950 px-4 py-2.5">
              <div className="flex items-center gap-1.5">
                <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-destructive/70" />
                <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-warning/70" />
                <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-success/70" />
              </div>
              <div className="rounded-none bg-background/60 px-3 py-0.5 font-mono text-[10px] text-muted-foreground">
                splashh.app/dashboard
              </div>
              <div className="w-12" />
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-2 gap-3 border-b border-border p-4 sm:grid-cols-4">
              <DashStat label="Today's Revenue" value="�48,250" delta="↑ 14.2%" tone="volt" />
              <DashStat label="Occupancy" value="82%" delta="Peak hours" tone="muted" />
              <DashStat label="Renewals" value="24" delta="This week" tone="muted" />
              <DashStat label="Active Members" value="1,284" delta="+12 New" tone="volt" />
            </div>

            {/* Revenue chart + Upcoming list */}
            <div className="grid gap-4 p-4 md:grid-cols-[2fr_1fr]">
              {/* Revenue trend bar chart */}
              <div className="rounded-none border-2 border-border bg-charcoal-900 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                    Revenue trend
                  </span>
                  <span className="font-mono text-[10px] text-volt">Last 10 days</span>
                </div>
                <RevenueBars />
              </div>
              {/* Upcoming list */}
              <div className="rounded-none border-2 border-border bg-charcoal-900 p-4">
                <p className="mb-3 font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  Upcoming
                </p>
                <ul className="space-y-2.5">
                  {[
                    { name: "Court 1", time: "18:00" },
                    { name: "Pool Batch A", time: "18:30" },
                    { name: "Court 3", time: "19:00" },
                  ].map((row) => (
                    <li
                      key={row.name}
                      className="flex items-center justify-between border-b border-border/60 pb-2.5 last:border-0 last:pb-0"
                    >
                      <span className="text-xs text-foreground">{row.name}</span>
                      <span className="font-mono text-[10px] text-volt">{row.time}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Volt section — full bleed, dark text on volt green */}
      <section className="bg-volt px-6 py-24 text-black">
        <div className="mx-auto grid max-w-6xl items-center gap-12 md:grid-cols-2">
          <div>
            <h2 className="font-display text-[clamp(2.5rem,6vw,4.5rem)] font-bold leading-[0.9] tracking-tight">
              Your club.
              <br />
              Everywhere.
            </h2>
            <p className="mt-6 max-w-md text-base text-black/80 sm:text-lg">
              A premium, installable PWA for your customers. They can book, pay, check-in via QR,
              and manage memberships right from their phones.
            </p>
            <ul className="mt-8 space-y-3 text-sm">
              {[
                "Installable app (PWA)",
                "QR code check-in",
                "Instant bookings",
                "Digital membership ID",
              ].map((item) => (
                <li
                  key={item}
                  className="inline-flex items-center gap-3 font-display text-[11px] uppercase tracking-[0.18em]"
                >
                  <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-black" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          {/* Phone mockup */}
          <div className="mx-auto w-full max-w-sm">
            <PhoneMockup />
          </div>
        </div>
      </section>

      {/* Stats — closing pitch with three big tiles */}
      <section className="border-t border-border px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="mb-12 text-center font-display text-[clamp(2rem,5vw,3.5rem)] font-bold leading-[0.95] tracking-tight">
            <span className="block text-foreground">Know your club.</span>
            <span className="block text-muted-foreground/70">Grow your club.</span>
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            <StatTile value="32%" label="Growth in peak revenue" tone="volt" />
            <StatTile value="14h" label="Admin time saved weekly" tone="white" />
            <StatTile value="94%" label="Court utilization rate" tone="volt" />
          </div>
        </div>
      </section>

      {/* Final CTA — dark, photo backdrop, two buttons */}
      <section className="relative isolate overflow-hidden border-t border-border">
        {/* Photo backdrop — gradient overlay so we don't need an external image */}
        <div
          aria-hidden
          className="absolute inset-0 -z-10"
          style={{
            backgroundImage:
              "linear-gradient(180deg, rgba(10,10,11,0.4), rgba(10,10,11,0.95))," +
              "radial-gradient(70% 60% at 50% 40%, color-mix(in oklab, var(--color-accent-warm) 8%, transparent), transparent 60%)",
          }}
        />
        <div
          className="absolute inset-0 -z-10 opacity-[0.08]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(135deg, color-mix(in oklab, var(--color-volt) 50%, transparent) 0 1px, transparent 1px 18px)",
          }}
        />

        <div className="mx-auto max-w-3xl px-6 py-28 text-center">
          <h2 className="font-display text-[clamp(2.5rem,7vw,5rem)] font-bold leading-[0.9] tracking-tight">
            <span className="block text-foreground">Ready to run a</span>
            <span className="block text-volt">better club?</span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-pretty text-base text-muted-foreground sm:text-lg">
            Bring bookings, memberships, payments, and operations into one platform built
            specifically for sports.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button size="lg" onClick={() => open("customer")}>
              Book a demo
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button size="lg" variant="outline" onClick={() => open("staff")}>
              Talk to us
            </Button>
          </div>
        </div>
      </section>

      {/* Footer — 3-column: brand + Product + Company + social */}
      <footer className="border-t border-border bg-black text-foreground">
        <div className="mx-auto max-w-6xl px-6 py-12">
          <div className="grid gap-10 md:grid-cols-3">
            {/* Brand */}
            <div>
              <Link to="/" className="inline-flex items-center gap-2 font-bold text-lg">
                <Waves
                  className="h-5 w-5 text-volt animate-swim-bob motion-reduce:animate-none"
                  aria-hidden="true"
                />
                {brand.name}
              </Link>
              <p className="mt-3 max-w-xs text-sm text-muted-foreground">
                The operating system for modern sports clubs. Designed for the way sports actually
                work.
              </p>
            </div>

            {/* Product */}
            <div>
              <p className="font-display text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Product
              </p>
              <ul className="mt-4 space-y-2 text-sm">
                <li>
                  <a
                    href="#platform"
                    className="text-foreground transition-colors duration-250 hover:text-volt"
                  >
                    Platform
                  </a>
                </li>
                <li>
                  <a
                    href="#features"
                    className="text-foreground transition-colors duration-250 hover:text-volt"
                  >
                    Features
                  </a>
                </li>
                <li>
                  <a
                    href="#sports"
                    className="text-foreground transition-colors duration-250 hover:text-volt"
                  >
                    Sports
                  </a>
                </li>
                <li>
                  <a
                    href="#pricing"
                    className="text-foreground transition-colors duration-250 hover:text-volt"
                  >
                    Pricing
                  </a>
                </li>
              </ul>
            </div>

            {/* Company */}
            <div>
              <p className="font-display text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Company
              </p>
              <ul className="mt-4 space-y-2 text-sm">
                <li>
                  <a
                    href="#about"
                    className="text-foreground transition-colors duration-250 hover:text-volt"
                  >
                    About
                  </a>
                </li>
                <li>
                  <a
                    href="#contact"
                    className="text-foreground transition-colors duration-250 hover:text-volt"
                  >
                    Contact
                  </a>
                </li>
                <li>
                  <a
                    href="#privacy"
                    className="text-foreground transition-colors duration-250 hover:text-volt"
                  >
                    Privacy policy
                  </a>
                </li>
                <li>
                  <a
                    href="#terms"
                    className="text-foreground transition-colors duration-250 hover:text-volt"
                  >
                    Terms of service
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row">
            <p>
              © {new Date().getFullYear()} {brand.name} Sports. All rights reserved.
            </p>
            <div className="flex items-center gap-2">
              <a
                aria-label="X (Twitter)"
                href="#x"
                className="inline-flex h-8 w-8 items-center justify-center rounded-full border-2 border-border transition-all duration-250 hover:border-volt hover:text-volt"
              >
                <span className="text-xs font-bold">X</span>
              </a>
              <a
                aria-label="LinkedIn"
                href="#linkedin"
                className="inline-flex h-8 w-8 items-center justify-center rounded-full border-2 border-border transition-all duration-250 hover:border-volt hover:text-volt"
              >
                <span className="text-xs font-bold">in</span>
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* Auth modal (Klook-style: opens over landing page) */}
      {authOpen && <AuthModal mode={authMode} onClose={close} onSwitch={setAuthMode} />}
    </div>
  );
}

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <a
      href={to}
      className="rounded-none px-3 py-2 text-sm text-muted-foreground transition-all duration-250 ease-swim hover:bg-secondary hover:text-foreground"
    >
      {children}
    </a>
  );
}

function FeatureCard({
  tone,
  eyebrow,
  title,
  body,
  stat,
  statLabel,
  illustration,
}: {
  tone: "primary" | "accent" | "ink";
  eyebrow: string;
  title: string;
  body: string;
  stat: string;
  statLabel: string;
  illustration: React.ReactNode;
}) {
  const toneClasses = {
    primary: "bg-primary/5 border-primary/20 hover:border-primary/50",
    accent: "bg-accent/5 border-accent/20 hover:border-accent/50",
    ink: "bg-foreground/[0.03] border-foreground/10 hover:border-foreground/30",
  }[tone];
  return (
    <div
      className={`group relative flex flex-col overflow-hidden rounded-none border-2 p-6 transition-all duration-350 ease-swim hover:-translate-y-1 hover:shadow-volt-sm ${toneClasses}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {eyebrow}
          </span>
          <h3 className="mt-2 text-balance text-lg font-semibold text-foreground">{title}</h3>
        </div>
        <div className="shrink-0 opacity-90 transition-transform duration-350 ease-swim group-hover:scale-110">
          {illustration}
        </div>
      </div>
      <p className="mt-3 text-pretty text-sm text-muted-foreground">{body}</p>
      <div className="mt-6 flex items-baseline gap-2 border-t border-current/10 pt-4">
        <span className="text-2xl font-bold tracking-tight text-foreground">{stat}</span>
        <span className="text-xs text-muted-foreground">{statLabel}</span>
      </div>
    </div>
  );
}

/** Bento cell — used in the facility-overview grid. */
function FacilityCell({
  colSpan,
  tone,
  eyebrow,
  title,
  subtitle,
  detail,
  icon,
  accent,
  delay = 0,
}: {
  colSpan: string;
  tone: "volt" | "warm" | "ink";
  eyebrow: string;
  title: string;
  subtitle?: string;
  detail?: string;
  icon?: React.ReactNode;
  accent?: "volt";
  delay?: number;
}) {
  const toneClasses = {
    volt: "bg-volt/10 border-volt/30 hover:border-volt/60",
    warm: "bg-accent-warm/10 border-accent-warm/30 hover:border-accent-warm/60",
    ink: "bg-charcoal-900 border-charcoal-700 hover:border-charcoal-500",
  }[tone];

  const titleColor =
    accent === "volt"
      ? "text-volt"
      : tone === "volt"
        ? "text-volt"
        : tone === "warm"
          ? "text-accent-warm"
          : "text-foreground";

  return (
    <div
      className={`group relative flex flex-col justify-between overflow-hidden rounded-none border-2 p-5 transition-all duration-350 ease-swim hover:-translate-y-0.5 hover:shadow-volt-sm ${colSpan} ${toneClasses} animate-rise-up motion-reduce:animate-none`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-display text-xs uppercase tracking-[0.18em] text-muted-foreground">
          {eyebrow}
        </span>
        {icon && (
          <span
            className={
              tone === "volt"
                ? "text-volt"
                : tone === "warm"
                  ? "text-accent-warm"
                  : "text-muted-foreground"
            }
          >
            {icon}
          </span>
        )}
      </div>
      <div className="mt-auto pt-4">
        <p className={`font-display text-2xl font-bold leading-tight ${titleColor}`}>{title}</p>
        {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
        {detail && (
          <p className="mt-0.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground/80">
            {detail}
          </p>
        )}
      </div>
    </div>
  );
}

function Step({
  n,
  icon,
  title,
  children,
}: {
  n: number;
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <li className="relative pl-12">
      <div className="absolute left-0 top-0 flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
        {icon}
      </div>
      <div className="absolute left-4 top-9 h-[calc(100%-2.25rem)] w-px bg-gradient-to-b from-primary/30 to-transparent" />
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Step {n}</p>
      <h3 className="mt-1 text-lg font-semibold text-foreground">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{children}</p>
    </li>
  );
}

function HeroFloatingCards() {
  // Reference-style floating UI cards: Court 02 / Revenue Today / Booked slot.
  return (
    <div className="relative mx-auto h-[520px] w-full max-w-md">
      {/* Backdrop glow */}
      <div
        aria-hidden
        className="absolute inset-0 rounded-full opacity-50 blur-3xl"
        style={{
          backgroundImage:
            "radial-gradient(60% 60% at 50% 50%, color-mix(in oklab, var(--color-volt) 18%, transparent), transparent 70%)",
        }}
      />

      {/* Player silhouette — abstract athletic shape built from a CSS gradient + circle */}
      <div
        aria-hidden
        className="absolute right-6 top-12 h-80 w-72 rounded-none border-2 border-border bg-card/40 bg-cover bg-center"
        style={{
          backgroundImage:
            "linear-gradient(180deg, rgba(10,10,11,0.4) 0%, rgba(10,10,11,0.8) 100%)," +
            "radial-gradient(40% 60% at 60% 35%, color-mix(in oklab, var(--color-accent-cool) 30%, transparent), transparent 70%)," +
            "radial-gradient(50% 50% at 50% 90%, color-mix(in oklab, var(--color-accent-warm) 20%, transparent), transparent 70%)",
        }}
      >
        <div className="absolute bottom-4 left-4 right-4 font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground/80">
          Court 02 · Live
        </div>
      </div>

      {/* Card 1 — Court occupancy */}
      <div className="absolute left-2 top-16 w-56 rounded-none border-2 border-border bg-card p-4 shadow-volt-md animate-rise-up motion-reduce:animate-none">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className="flex h-8 w-8 items-center justify-center rounded-none bg-volt text-black"
          >
            <Waves className="h-4 w-4" />
          </span>
          <div>
            <p className="font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Court 02
            </p>
            <p className="font-display text-sm font-bold text-foreground">87% OCCUPANCY</p>
          </div>
        </div>
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-charcoal-900">
          <div className="h-full w-[87%] rounded-full bg-volt" />
        </div>
      </div>

      {/* Card 2 — Revenue (VOLT green, dark text — reference highlight) */}
      <div className="absolute right-0 top-44 w-48 rounded-none bg-volt p-4 text-black shadow-volt-md animate-rise-up motion-reduce:animate-none [animation-delay:120ms]">
        <p className="font-display text-[10px] uppercase tracking-[0.18em]">Revenue Today</p>
        <p className="mt-1 font-display text-2xl font-bold">₹42,500</p>
      </div>

      {/* Card 3 — Booked slot */}
      <div className="absolute bottom-8 right-2 w-60 rounded-none border-2 border-border bg-card p-4 shadow-volt-md animate-score-pop motion-reduce:animate-none [animation-delay:280ms]">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="flex h-10 w-10 items-center justify-center rounded-none bg-foreground text-background"
          >
            <Clock className="h-4 w-4" />
          </span>
          <div>
            <p className="font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              7:00 PM Slot
            </p>
            <p className="font-display text-base font-bold text-foreground">BOOKED</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function DashStat({
  label,
  value,
  delta,
  tone,
}: {
  label: string;
  value: string;
  delta: string;
  tone: "volt" | "muted";
}) {
  const isVolt = tone === "volt";
  return (
    <div
      className={`rounded-none border p-3 ${isVolt ? "border-volt/30 bg-volt/5" : "border-border bg-charcoal-900"}`}
    >
      <p className="font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p
        className={`mt-1 font-display text-2xl font-bold ${isVolt ? "text-volt" : "text-foreground"}`}
      >
        {value}
      </p>
      <p
        className={`mt-0.5 font-mono text-[10px] ${isVolt ? "text-volt" : "text-muted-foreground"}`}
      >
        {delta}
      </p>
    </div>
  );
}

function RevenueBars() {
  // Synthetic 10-day revenue bars, ascending trend, volt green.
  const heights = [40, 55, 35, 70, 80, 45, 95, 75, 90, 100];
  return (
    <div className="flex h-40 items-end gap-2" role="img" aria-label="Revenue trend bar chart">
      {heights.map((h, i) => (
        <div
          key={`bar-${h}`}
          className="flex-1 rounded-t bg-gradient-to-t from-volt-hover to-volt animate-rise-up motion-reduce:animate-none"
          style={{ height: `${h}%`, animationDelay: `${i * 40}ms` }}
          aria-hidden
        />
      ))}
    </div>
  );
}

function PhoneMockup() {
  return (
    <div className="relative">
      <div className="rounded-[2.5rem] border-2 border-black/20 bg-black p-2 shadow-volt-md">
        <div className="rounded-[2rem] bg-white p-4 text-black">
          {/* Status bar */}
          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest">
            <span>SPLASHH</span>
            <span className="h-2 w-2 rounded-full bg-black/20" />
          </div>

          {/* Digital pass card */}
          <div className="mt-4 rounded-none bg-black p-4 text-white">
            <p className="text-[10px] uppercase tracking-widest text-white/60">Digital pass</p>
            <p className="mt-1 text-volt font-bold uppercase tracking-widest">Pro Membership</p>
            <div className="mt-4 flex h-20 items-center justify-center rounded-none border border-dashed border-white/30">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/60">
                Scan to enter
              </span>
            </div>
          </div>

          {/* Upcoming */}
          <p className="mt-5 text-[10px] uppercase tracking-widest text-black/60">Upcoming</p>
          <div className="mt-2 rounded-none bg-black/5 p-3">
            <p className="text-xs font-semibold">Badminton Court 2</p>
            <p className="text-[10px] text-black/60">Today, 7:00 PM</p>
          </div>
        </div>
      </div>
      <div
        className="absolute inset-x-0 bottom-0 mx-auto h-1 w-32 -translate-y-3 rounded-b-2xl bg-black/30 blur-sm"
        aria-hidden
      />
    </div>
  );
}

function StatTile({
  value,
  label,
  tone,
}: {
  value: string;
  label: string;
  tone: "volt" | "white";
}) {
  const valueColor = tone === "volt" ? "text-volt" : "text-foreground";
  return (
    <div className="rounded-none border-2 border-border bg-card p-6 text-center transition-all duration-350 ease-swim hover:-translate-y-0.5 hover:border-volt/40 hover:shadow-volt-sm">
      <p className={`font-display text-5xl font-bold tracking-tight ${valueColor}`}>{value}</p>
      <p className="mt-3 font-display text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        {label}
      </p>
    </div>
  );
}

function PoolIllustration() {
  return (
    <svg viewBox="0 0 80 80" className="h-16 w-16" aria-hidden="true">
      <rect x="6" y="14" width="68" height="52" rx="8" fill="var(--color-volt-soft)" />
      <path
        d="M6 36 Q20 30 34 36 T62 36 T80 36"
        stroke="var(--color-volt)"
        strokeWidth="2"
        fill="none"
      />
      <path
        d="M6 50 Q20 44 34 50 T62 50 T80 50"
        stroke="var(--color-volt-hover)"
        strokeOpacity="0.6"
        strokeWidth="2"
        fill="none"
      />
      <path
        d="M0 36 Q14 30 28 36 T56 36 T74 36"
        stroke="var(--color-volt)"
        strokeOpacity="0.4"
        strokeWidth="1.5"
        fill="none"
        strokeDasharray="3 3"
      />
    </svg>
  );
}

function CalendarIllustration() {
  return (
    <svg viewBox="0 0 80 80" className="h-16 w-16" aria-hidden="true">
      <rect x="10" y="16" width="60" height="54" rx="6" fill="var(--color-accent-warm-soft)" />
      <rect x="10" y="16" width="60" height="12" rx="6" fill="var(--color-accent-warm)" />
      <circle cx="22" cy="14" r="3" fill="var(--color-accent-warm)" />
      <circle cx="58" cy="14" r="3" fill="var(--color-accent-warm)" />
      <rect
        x="18"
        y="36"
        width="10"
        height="10"
        rx="2"
        fill="var(--color-accent-warm)"
        fillOpacity="0.5"
      />
      <rect x="35" y="36" width="10" height="10" rx="2" fill="#ffffff" fillOpacity="0.15" />
      <rect x="52" y="36" width="10" height="10" rx="2" fill="#ffffff" fillOpacity="0.15" />
      <rect x="18" y="52" width="10" height="10" rx="2" fill="#ffffff" fillOpacity="0.15" />
      <rect
        x="35"
        y="52"
        width="10"
        height="10"
        rx="2"
        fill="var(--color-accent-warm)"
        fillOpacity="0.5"
      />
    </svg>
  );
}

function LedgerIllustration() {
  return (
    <svg viewBox="0 0 80 80" className="h-16 w-16" aria-hidden="true">
      <rect x="12" y="14" width="56" height="52" rx="4" fill="#ffffff" fillOpacity="0.06" />
      <rect x="18" y="22" width="44" height="6" rx="2" fill="#ffffff" fillOpacity="0.5" />
      <rect x="18" y="34" width="28" height="4" rx="2" fill="#ffffff" fillOpacity="0.25" />
      <rect x="18" y="42" width="36" height="4" rx="2" fill="#ffffff" fillOpacity="0.25" />
      <rect x="18" y="50" width="24" height="4" rx="2" fill="#ffffff" fillOpacity="0.25" />
      <circle cx="58" cy="58" r="8" fill="var(--color-volt)" />
      <path
        d="M54 58 L57 61 L62 55"
        stroke="#000000"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function AuthModal({
  mode,
  onClose,
  onSwitch,
}: {
  mode: Mode;
  onClose: () => void;
  onSwitch: (m: Mode) => void;
}) {
  const navigate = useNavigate();
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    emailRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    // biome-ignore lint/a11y/useSemanticElements: native <dialog> not used to preserve styling/animation
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4 backdrop-blur-sm animate-rise-up motion-reduce:animate-none"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-none border-2 border-border bg-card p-6 shadow-volt-md animate-score-pop motion-reduce:animate-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 id="auth-modal-title" className="text-xl font-semibold text-foreground">
            {mode === "staff" ? "Staff log in" : "Customer log in"}
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-full p-1.5 text-muted-foreground transition-all duration-250 ease-swim hover:bg-secondary hover:text-foreground active:scale-95"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Book a lane, settle a bill, or check your court. We'll know what you can see.
        </p>

        {/* Tabs */}
        <div role="tablist" aria-label="Login type" className="mt-5 flex border-b border-border">
          {(["customer", "staff"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => onSwitch(m)}
              className={`flex-1 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-all duration-250 ease-swim ${
                mode === m
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {m === "customer" ? "Member" : "Staff"}
            </button>
          ))}
        </div>

        <div className="mt-5">
          <LoginForm
            mode={mode}
            headingLevel="h3"
            emailRef={emailRef}
            onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
          />
        </div>

        <div className="mt-5 border-t border-border pt-4 text-center text-xs text-muted-foreground">
          Need help? Contact your club.
        </div>
      </div>
    </div>
  );
}

// Unused but kept available for future use; suppress TS unused warnings.
const _unused = { LogIn, MapPin, Clock, Receipt };
void _unused;
