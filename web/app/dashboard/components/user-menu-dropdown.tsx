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
    <div className="w-60 bg-white border border-zinc-200 shadow-lg overflow-hidden">
      {/* User Info Header */}
      <div className="px-4 py-3 border-b border-zinc-100">
        <p className="text-zinc-900 font-semibold truncate">
          {user.name || 'User'}
        </p>
        <p className="text-zinc-500 text-sm truncate">
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
            className="flex items-center gap-3 px-4 py-2 text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 transition-colors"
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>

      {/* Sign Out */}
      <div className="border-t border-zinc-100 py-2">
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-4 py-2 w-full text-red-600 hover:bg-red-50 hover:text-red-700 transition-colors"
        >
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}
