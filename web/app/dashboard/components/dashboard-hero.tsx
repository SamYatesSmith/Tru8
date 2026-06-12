'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Upload, GitBranch, ClipboardCheck, ChevronDown, ChevronUp, X } from 'lucide-react';
import { UserStats } from '@/lib/api';

const SUBSCRIPTIONS_ENABLED = process.env.NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED === 'true';
const HERO_COLLAPSED_KEY = 'tru8_dashboard_hero_collapsed';
const UPGRADE_DISMISSED_KEY = 'tru8_upgrade_strip_dismissed';

const PROCESS_STEPS = [
  {
    icon: Upload,
    number: '01',
    label: 'Submit',
    title: 'Submit an Article or Claim',
    description: 'Paste a news article, headline, claim, or URL.',
  },
  {
    icon: GitBranch,
    number: '02',
    label: 'Research',
    title: 'Evidence Gathered',
    description:
      'Government data, news, academic papers, and official records — classified by tier and type.',
  },
  {
    icon: ClipboardCheck,
    number: '03',
    label: 'Explore',
    title: 'Explore the Landscape',
    description:
      'Six views of the same evidence. See the shape, browse, focus, watch, trace, or surface unknowns.',
  },
];

interface DashboardHeroProps {
  userName: string | null;
  stats: UserStats;
  usage: { periodCreditsUsed: number; creditsPerPeriod: number };
  isFreeUser: boolean;
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function formatMemberSince(dateStr: string | null): string {
  if (!dateStr) return '\u2014';
  return new Date(dateStr).toLocaleDateString('en-GB', {
    month: 'short',
    year: 'numeric',
  });
}

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white/70 border border-zinc-200 px-4 py-3">
      <div className="text-lg md:text-xl font-mono font-light text-zinc-900">
        {value}
      </div>
      <div className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mt-0.5">
        {label}
      </div>
    </div>
  );
}

function ProcessSteps() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12">
      {PROCESS_STEPS.map((step) => {
        const Icon = step.icon;
        return (
          <div key={step.number} className="flex flex-col">
            <div className="flex items-center gap-3 mb-4">
              <Icon className="text-zinc-300 flex-shrink-0" size={24} />
              <div className="h-[1px] flex-grow bg-zinc-200" />
              <span className="font-mono text-[10px] text-zinc-400">
                {step.number}
              </span>
            </div>
            <span className="font-mono text-[10px] tracking-widest uppercase text-accent mb-1">
              {step.label}
            </span>
            <h3 className="text-sm font-bold uppercase tracking-wide text-zinc-900 mb-2">
              {step.title}
            </h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              {step.description}
            </p>
          </div>
        );
      })}
    </div>
  );
}

export function DashboardHero({ userName, stats, usage, isFreeUser }: DashboardHeroProps) {
  const isNewUser = stats.totalChecks < 3;

  const [isCollapsed, setIsCollapsed] = useState(!isNewUser);
  const [isUpgradeDismissed, setIsUpgradeDismissed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(HERO_COLLAPSED_KEY);
    if (stored !== null) {
      setIsCollapsed(stored === 'true');
    }
    if (localStorage.getItem(UPGRADE_DISMISSED_KEY) === 'true') {
      setIsUpgradeDismissed(true);
    }
  }, []);

  const toggleCollapsed = () => {
    const next = !isCollapsed;
    setIsCollapsed(next);
    localStorage.setItem(HERO_COLLAPSED_KEY, String(next));
  };

  const dismissUpgrade = () => {
    setIsUpgradeDismissed(true);
    localStorage.setItem(UPGRADE_DISMISSED_KEY, 'true');
  };

  const showUpgradeStrip = SUBSCRIPTIONS_ENABLED && isFreeUser && !isUpgradeDismissed;

  return (
    <div className="bg-grid-dot border-b border-zinc-200 -mx-4 md:-mx-6 px-4 md:px-6 py-6 md:py-10 mb-6 md:mb-8">
      {/* Micro-label */}
      <h1 className="font-mono text-2xl md:text-3xl tracking-[0.15em] uppercase text-zinc-400 mb-4">
        News Evidence Research Platform
      </h1>

      {isNewUser ? (
        /* ── State A: New User ── */
        <>
          <div className="flex items-start justify-between mb-6">
            <h2 className="text-xl md:text-2xl font-bold text-zinc-900">
              How Tru8 works
            </h2>
            <button
              onClick={toggleCollapsed}
              className="text-zinc-400 hover:text-zinc-900 p-1 transition-colors"
              aria-label={isCollapsed ? 'Expand guide' : 'Collapse guide'}
            >
              {isCollapsed ? <ChevronDown size={20} /> : <ChevronUp size={20} />}
            </button>
          </div>

          {isCollapsed ? (
            <p className="text-sm text-zinc-500 mb-6">
              Submit a news article or claim, evidence is gathered, explore six views.
            </p>
          ) : (
            <div className="mb-8">
              <ProcessSteps />
            </div>
          )}

          <Link
            href="/dashboard/new-check"
            className="relative inline-flex items-center gap-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] h-11 px-6 transition-colors"
          >
            Start Your First Check
            <div className="w-2.5 h-2.5 bg-accent absolute right-0 top-1/2 -translate-y-1/2 translate-x-1 rotate-45" />
          </Link>
        </>
      ) : (
        /* ── State B: Returning User ── */
        <>
          <h2 className="text-xl md:text-2xl font-bold text-zinc-900 mb-6">
            Welcome back, {userName || 'User'}
          </h2>

          {/* Stats row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <StatCell label="Checks" value={formatNumber(stats.totalChecks)} />
            <StatCell label="Sources Analysed" value={formatNumber(stats.totalSourcesAnalyzed)} />
            <StatCell label="Claims Mapped" value={formatNumber(stats.totalClaimsAnalyzed)} />
            <StatCell label="Member Since" value={formatMemberSince(stats.memberSince)} />
          </div>

          {/* Top domain */}
          {stats.topDomain && (
            <p className="text-xs text-zinc-500 mb-6">
              Most researched:{' '}
              <span className="font-medium text-zinc-700">{stats.topDomain}</span>
            </p>
          )}

          {/* CTA + process toggle */}
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard/new-check"
              className="relative inline-flex items-center gap-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] h-11 px-6 transition-colors"
            >
              New Check
              <div className="w-2.5 h-2.5 bg-accent absolute right-0 top-1/2 -translate-y-1/2 translate-x-1 rotate-45" />
            </Link>
            <button
              onClick={toggleCollapsed}
              className="text-xs text-zinc-400 hover:text-zinc-900 flex items-center gap-1 transition-colors"
            >
              How it works
              {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            </button>
          </div>

          {/* Expandable process explainer */}
          {!isCollapsed && (
            <div className="mt-8 pt-6 border-t border-zinc-200">
              <ProcessSteps />
            </div>
          )}
        </>
      )}

      {/* Upgrade Strip */}
      {showUpgradeStrip && (
        <div className="flex items-center justify-between gap-3 mt-6 pt-4 border-t border-zinc-200">
          <p className="text-xs text-zinc-500">
            You&apos;ve used{' '}
            <span className="font-medium text-zinc-700">{usage.periodCreditsUsed}</span> of{' '}
            <span className="font-medium text-zinc-700">{usage.creditsPerPeriod}</span> checks
            this month.{' '}
            <Link
              href="/dashboard/settings?tab=subscription"
              className="text-accent hover:underline font-medium"
            >
              Unlock 40/month &rarr;
            </Link>
          </p>
          <button
            onClick={dismissUpgrade}
            className="text-zinc-400 hover:text-zinc-900 p-1 transition-colors flex-shrink-0"
            aria-label="Dismiss upgrade notice"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
