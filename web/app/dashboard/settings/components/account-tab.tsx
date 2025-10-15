'use client';

import { useState } from 'react';
import { useClerk } from '@clerk/nextjs';
import Image from 'next/image';
import { User, Shield, Trash2 } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useAuth } from '@clerk/nextjs';

interface AccountTabProps {
  clerkUser: any;
  userData: any;
}

export function AccountTab({ clerkUser, userData }: AccountTabProps) {
  const { openUserProfile, signOut } = useClerk();
  const { getToken } = useAuth();
  const [deleting, setDeleting] = useState(false);

  const handleUpdateProfile = () => {
    // Open Clerk's built-in profile modal
    openUserProfile();
  };

  const handleChangePassword = () => {
    // Open Clerk's security modal
    openUserProfile({ page: 'security' } as any);
  };

  const handleDeleteAccount = async () => {
    const confirmed = confirm(
      'Are you absolutely sure? This action cannot be undone. All your checks, data, and subscription will be permanently deleted.'
    );

    if (!confirmed) return;

    const doubleConfirm = confirm(
      'This is your last chance. Type DELETE in the next prompt to confirm.'
    );

    if (!doubleConfirm) return;

    const typedConfirmation = prompt('Type DELETE to confirm account deletion:');

    if (typedConfirmation !== 'DELETE') {
      alert('Account deletion cancelled.');
      return;
    }

    setDeleting(true);

    try {
      // Delete from backend first
      const token = await getToken();
      await apiClient.deleteUser(userData.id, token);

      // Delete from Clerk
      await clerkUser?.delete();

      // Sign out and redirect
      await signOut();
      window.location.href = '/';
    } catch (error) {
      console.error('Failed to delete account:', error);
      alert('Failed to delete account. Please contact support at support@tru8.com');
      setDeleting(false);
    }
  };

  const initials = clerkUser?.fullName
    ?.split(' ')
    .map((n: string) => n[0])
    .join('')
    .toUpperCase() || 'U';

  return (
    <div className="space-y-8">
      {/* Profile Section */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <User size={20} />
          Profile Information
        </h3>

        <div className="space-y-6">
          {/* Avatar */}
          <div className="flex justify-center">
            {clerkUser?.imageUrl ? (
              <Image
                src={clerkUser.imageUrl}
                alt="Profile"
                width={80}
                height={80}
                className="rounded-full"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-slate-600 flex items-center justify-center text-white text-2xl font-bold">
                {initials}
              </div>
            )}
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Name
            </label>
            <input
              type="text"
              value={clerkUser?.fullName || ''}
              disabled
              className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white cursor-not-allowed opacity-75"
            />
            <p className="text-xs text-slate-400 mt-1">
              Click &quot;Update Profile&quot; below to change your name
            </p>
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Email
            </label>
            <input
              type="email"
              value={clerkUser?.primaryEmailAddress?.emailAddress || ''}
              disabled
              className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-slate-500 cursor-not-allowed"
            />
            <p className="text-xs text-slate-400 mt-1">
              Email is managed by your authentication provider
            </p>
          </div>

          <button
            onClick={handleUpdateProfile}
            className="w-full px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all"
          >
            Update Profile
          </button>
        </div>
      </section>

      {/* Security Section */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Shield size={20} />
          Security
        </h3>

        <div className="space-y-4">
          {/* Password */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-300">Password</p>
              <p className="text-xs text-slate-400">••••••••</p>
            </div>
            <button
              onClick={handleChangePassword}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
            >
              Change Password
            </button>
          </div>

          {/* 2FA */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-300">
                Two-Factor Authentication
              </p>
              <p className="text-xs text-slate-400">
                Status:{' '}
                {clerkUser?.twoFactorEnabled ? (
                  <span className="text-emerald-400 font-medium">Enabled</span>
                ) : (
                  <span className="text-slate-500 font-medium">Disabled</span>
                )}
              </p>
            </div>
            <button
              onClick={handleChangePassword}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
            >
              Configure 2FA
            </button>
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="bg-red-900/10 border border-red-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-red-400 mb-4 flex items-center gap-2">
          <Trash2 size={20} />
          Danger Zone
        </h3>

        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-slate-300">Delete Account</p>
            <p className="text-xs text-slate-400 mt-1">
              Once you delete your account, there is no going back. Please be certain.
            </p>
          </div>

          <button
            onClick={handleDeleteAccount}
            disabled={deleting}
            className="px-6 py-3 bg-red-900/30 hover:bg-red-900/50 text-red-400 border border-red-700 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {deleting ? 'Deleting...' : 'Delete Account'}
          </button>
        </div>
      </section>
    </div>
  );
}
