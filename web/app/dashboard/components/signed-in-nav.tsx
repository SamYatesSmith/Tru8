'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { Plus, LayoutDashboard, Clock, Settings } from 'lucide-react';
import { UserMenuDropdown } from './user-menu-dropdown';
import { BetaBadge } from '@/components/layout/beta-banner';

interface SignedInNavProps {
  user: {
    id: string;
    name: string | null;
    email: string;
    credits: number;
  };
}

export function SignedInNav({ user }: SignedInNavProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const pathname = usePathname();

  // Use backend user data (name is stored in our database, not Clerk)
  const displayName = user.name;
  const displayEmail = user.email;

  // Calculate user initials
  const initials = displayName
    ?.split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase() || 'U';

  const tabs = [
    { label: 'DASHBOARD', href: '/dashboard' },
    { label: 'HISTORY', href: '/dashboard/history' },
    { label: 'SETTINGS', href: '/dashboard/settings' },
  ];

  // Mobile nav items with icons
  const mobileNavItems = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'History', href: '/dashboard/history', icon: Clock },
    { label: 'New', href: '/dashboard/new-check', icon: Plus, highlight: true },
    { label: 'Settings', href: '/dashboard/settings', icon: Settings },
  ];

  return (
    <>
      {/* Top Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#1a1f2e]/95 backdrop-blur-sm border-b border-slate-800">
        <div className="container mx-auto px-4 md:px-6 max-w-7xl">
          <div className="flex items-center justify-between h-14 md:h-16">
            {/* Left: Logo + Beta Badge */}
            <Link href="/dashboard" className="flex-shrink-0 flex items-center gap-2">
              <Image
                src="/logo.proper.png"
                alt="Tru8"
                width={40}
                height={40}
                className="object-contain md:w-[50px] md:h-[50px]"
              />
              <BetaBadge />
            </Link>

            {/* Center: Tabs - Hidden on mobile */}
            <div className="hidden md:flex items-center gap-8">
              {tabs.map(tab => {
                const isActive = pathname === tab.href ||
                                (tab.href === '/dashboard/settings' && pathname.startsWith('/dashboard/settings'));

                return (
                  <Link
                    key={tab.href}
                    href={tab.href}
                    className={`text-sm font-bold tracking-wide transition-colors pb-1 border-b-2 ${
                      isActive
                        ? 'text-[#f57a07] border-[#f57a07]'
                        : 'text-slate-300 border-transparent hover:text-white'
                    }`}
                  >
                    {tab.label}
                  </Link>
                );
              })}
            </div>

            {/* Right: New Check (desktop only) + Avatar */}
            <div className="flex items-center gap-3 md:gap-4">
              {/* New Check button - Desktop only */}
              <Link
                href="/dashboard/new-check"
                className="hidden md:flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors"
              >
                <Plus size={18} />
                <span className="font-medium">New Check</span>
              </Link>

              {/* User Avatar */}
              <div className="relative">
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-slate-600 flex items-center justify-center text-white font-bold hover:bg-slate-500 transition-colors text-sm md:text-base"
                  aria-label="User menu"
                >
                  {initials}
                </button>

                {dropdownOpen && (
                  <>
                    {/* Backdrop */}
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setDropdownOpen(false)}
                    />

                    {/* Dropdown Menu */}
                    <div className="absolute top-full right-0 mt-2 z-50">
                      <UserMenuDropdown
                        user={{
                          ...user,
                          name: displayName,
                          email: displayEmail,
                        }}
                        onClose={() => setDropdownOpen(false)}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#1a1f2e] border-t border-slate-700" aria-label="Mobile navigation">
        <div className="grid grid-cols-4 h-16">
          {mobileNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href ||
                            (item.href === '/dashboard/settings' && pathname.startsWith('/dashboard/settings'));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center justify-center gap-1 relative ${
                  item.highlight ? 'text-[#f57a07]' : ''
                }`}
                aria-label={item.label}
                aria-current={isActive ? 'page' : undefined}
              >
                {/* Active indicator (orange top border) */}
                {isActive && (
                  <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#f57a07]" aria-hidden="true" />
                )}

                {/* Icon */}
                <Icon
                  className={`w-5 h-5 ${
                    isActive ? 'text-[#f57a07]' : item.highlight ? 'text-[#f57a07]' : 'text-slate-400'
                  }`}
                  aria-hidden="true"
                />

                {/* Label */}
                <span
                  className={`text-xs ${
                    isActive ? 'text-[#f57a07]' : item.highlight ? 'text-[#f57a07]' : 'text-slate-400'
                  }`}
                >
                  {item.label}
                </span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
