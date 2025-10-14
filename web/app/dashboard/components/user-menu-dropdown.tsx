'use client';

import Link from 'next/link';
import { useClerk } from '@clerk/nextjs';
import { User, CreditCard, Bell, LogOut } from 'lucide-react';

interface UserMenuDropdownProps {
  user: {
    name: string | null;
    email: string;
  };
  onClose: () => void;
}

export function UserMenuDropdown({ user, onClose }: UserMenuDropdownProps) {
  const { signOut } = useClerk();

  const handleSignOut = async () => {
    await signOut();
    window.location.href = '/';
  };

  const menuItems = [
    {
      icon: User,
      label: 'Account',
      href: '/dashboard/settings?tab=account',
    },
    {
      icon: CreditCard,
      label: 'Subscription',
      href: '/dashboard/settings?tab=subscription',
    },
    {
      icon: Bell,
      label: 'Notifications',
      href: '/dashboard/settings?tab=notifications',
    },
  ];

  return (
    <div className="w-60 bg-[#1a1f2e] border border-slate-700 rounded-xl shadow-2xl overflow-hidden">
      {/* User Info Header */}
      <div className="px-4 py-3 border-b border-slate-700">
        <p className="text-white font-semibold truncate">
          {user.name || 'User'}
        </p>
        <p className="text-slate-400 text-sm truncate">
          {user.email}
        </p>
      </div>

      {/* Menu Items */}
      <div className="py-2">
        {menuItems.map(item => (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClose}
            className="flex items-center gap-3 px-4 py-2 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>

      {/* Sign Out */}
      <div className="border-t border-slate-700 py-2">
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-4 py-2 w-full text-red-400 hover:bg-slate-800 hover:text-red-300 transition-colors"
        >
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}
