'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { Plus } from 'lucide-react';
import { UserMenuDropdown } from './user-menu-dropdown';

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

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#1a1f2e]/95 backdrop-blur-sm border-b border-slate-800">
      <div className="container mx-auto px-6 max-w-7xl">
        <div className="flex items-center justify-between h-16">
          {/* Left: Logo */}
          <Link href="/dashboard" className="flex-shrink-0">
            <Image
              src="/logo.proper.png"
              alt="Tru8"
              width={50}
              height={50}
              className="object-contain"
            />
          </Link>

          {/* Center: Tabs */}
          <div className="flex items-center gap-8">
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

          {/* Right: New Check + Avatar */}
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard/new-check"
              className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              <Plus size={18} />
              <span className="font-medium">New Check</span>
            </Link>

            {/* User Avatar */}
            <div className="relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="w-10 h-10 rounded-full bg-slate-600 flex items-center justify-center text-white font-bold hover:bg-slate-500 transition-colors"
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
  );
}
