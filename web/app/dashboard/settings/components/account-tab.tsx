'use client';

import { useState, useEffect } from 'react';
import { useClerk } from '@clerk/nextjs';
import Image from 'next/image';
import { User, Shield, Trash2, Check, X, Pencil, BarChart3 } from 'lucide-react';
import { apiClient, UserStats } from '@/lib/api';
import { useAuth, useUser } from '@clerk/nextjs';

interface AccountTabProps {
  clerkUser: any;
  userData: any;
}

export function AccountTab({ clerkUser, userData }: AccountTabProps) {
  const clerk = useClerk();
  const { signOut } = clerk;
  const { getToken } = useAuth();
  const { user: clerkUserHook } = useUser();
  const [deleting, setDeleting] = useState(false);

  // User stats state
  const [stats, setStats] = useState<UserStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Name editing state
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameValue, setNameValue] = useState(clerkUser?.fullName || userData?.name || '');
  const [savingName, setSavingName] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  // Fetch user stats on mount
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = await getToken();
        const userStats = await apiClient.getUserStats(token);
        setStats(userStats);
      } catch (error) {
        console.error('Failed to fetch user stats:', error);
      } finally {
        setStatsLoading(false);
      }
    };
    fetchStats();
  }, [getToken]);

  const handleSaveName = async () => {
    if (!nameValue.trim()) {
      setNameError('Name cannot be empty');
      return;
    }

    setSavingName(true);
    setNameError(null);

    try {
      const token = await getToken();

      // Update name in our backend database
      const result = await apiClient.updateUserProfile({ name: nameValue.trim() }, token);
      setIsEditingName(false);

      // Refresh the page to update navbar with new name
      window.location.reload();
    } catch (error: any) {
      console.error('Failed to update name:', error);
      setNameError(error?.message || 'Failed to save name. Please try again.');
      setSavingName(false);
    }
  };

  const handleCancelEdit = () => {
    setNameValue(clerkUser?.fullName || userData?.name || '');
    setIsEditingName(false);
    setNameError(null);
  };

  const handleChangePassword = () => {
    // Open Clerk's user profile modal with security settings
    clerk.openUserProfile({
      appearance: {
        elements: {
          rootBox: { width: '100%' }
        }
      }
    });
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
      alert('Failed to delete account. Please contact support at hello@trueight.com');
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
      <section className="bg-white border border-zinc-200 p-6">
        <h3 className="text-lg font-bold text-zinc-900 mb-6 flex items-center gap-2">
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
              <div className="w-20 h-20 rounded-full bg-zinc-200 flex items-center justify-center text-zinc-600 text-2xl font-bold">
                {initials}
              </div>
            )}
          </div>

          {/* Name - Inline editable */}
          <div>
            <label className="block font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-2">
              Name
            </label>
            {isEditingName ? (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={nameValue}
                    onChange={(e) => setNameValue(e.target.value)}
                    placeholder="Enter your name"
                    className="flex-1 px-4 py-3 bg-white border-2 border-black text-zinc-900 focus:outline-none"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveName();
                      if (e.key === 'Escape') handleCancelEdit();
                    }}
                  />
                  <button
                    onClick={handleSaveName}
                    disabled={savingName}
                    className="px-4 py-3 bg-zinc-900 hover:bg-zinc-800 disabled:bg-zinc-300 text-white transition-colors"
                    title="Save"
                  >
                    {savingName ? (
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <Check size={20} />
                    )}
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    disabled={savingName}
                    className="px-4 py-3 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 transition-colors"
                    title="Cancel"
                  >
                    <X size={20} />
                  </button>
                </div>
                {nameError && (
                  <p className="text-sm text-red-600">{nameError}</p>
                )}
              </div>
            ) : (
              <button
                onClick={() => setIsEditingName(true)}
                className="w-full px-4 py-3 bg-white border border-zinc-200 text-zinc-900 text-left hover:border-black transition-colors group"
              >
                <span className="flex items-center justify-between">
                  <span>{nameValue || 'Click to add your name'}</span>
                  <Pencil size={16} className="text-zinc-400 group-hover:text-zinc-900" />
                </span>
              </button>
            )}
          </div>

          {/* Email */}
          <div>
            <label className="block font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-2">
              Email
            </label>
            <input
              type="email"
              value={clerkUser?.primaryEmailAddress?.emailAddress || ''}
              disabled
              className="w-full px-4 py-3 bg-zinc-50 border border-zinc-200 text-zinc-400 cursor-not-allowed"
            />
            <p className="text-xs text-zinc-400 mt-1">
              Email is managed by your authentication provider
            </p>
          </div>

        </div>
      </section>

      {/* Activity Section */}
      <section className="bg-white border border-zinc-200 p-6">
        <h3 className="text-lg font-bold text-zinc-900 mb-6 flex items-center gap-2">
          <BarChart3 size={20} />
          Your Activity
        </h3>

        {statsLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-zinc-400 border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-zinc-400">Loading stats...</span>
          </div>
        ) : stats ? (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-zinc-50 p-4 text-center">
                <div className="text-2xl font-bold text-zinc-900">{stats.totalChecks}</div>
                <div className="font-mono text-[10px] text-zinc-400 mt-1">Total Checks</div>
              </div>
              <div className="bg-zinc-50 p-4 text-center">
                <div className="text-2xl font-bold text-zinc-900">{stats.totalSourcesAnalyzed}</div>
                <div className="font-mono text-[10px] text-zinc-400 mt-1">Sources Analysed</div>
              </div>
              <div className="bg-zinc-50 p-4 text-center">
                <div className="text-2xl font-bold text-zinc-900">{stats.totalClaimsAnalyzed ?? 0}</div>
                <div className="font-mono text-[10px] text-zinc-400 mt-1">Claims Analysed</div>
              </div>
            </div>

            {/* Claim Type Breakdown */}
            {stats.claimTypeBreakdown && Object.keys(stats.claimTypeBreakdown).length > 0 && (
              <div className="space-y-3">
                <h4 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400">Claim Types</h4>
                <div className="flex items-center gap-6 text-sm flex-wrap">
                  {Object.entries(stats.claimTypeBreakdown).sort(([,a],[,b]) => b - a).map(([type, count]) => (
                    <div key={type} className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-zinc-400" />
                      <span className="text-zinc-900 font-mono">{count}</span>
                      <span className="text-zinc-500 capitalize">{type}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Member Since */}
            <div className="pt-4 border-t border-zinc-100 text-sm text-zinc-400">
              Member since {stats.memberSince
                ? new Date(stats.memberSince).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })
                : 'Unknown'}
            </div>
          </div>
        ) : (
          <p className="text-zinc-400 text-sm">Unable to load activity stats</p>
        )}
      </section>

      {/* Security Section */}
      <section className="bg-white border border-zinc-200 p-6">
        <h3 className="text-lg font-bold text-zinc-900 mb-6 flex items-center gap-2">
          <Shield size={20} />
          Security
        </h3>

        <div className="space-y-4">
          {/* Password */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-700">Password</p>
              <p className="text-xs text-zinc-400">••••••••</p>
            </div>
            <button
              onClick={handleChangePassword}
              className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
            >
              Change Password
            </button>
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="border border-red-100 bg-red-50/30 p-6">
        <h3 className="text-lg font-bold text-red-700 mb-4 flex items-center gap-2">
          <Trash2 size={20} />
          Danger Zone
        </h3>

        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-red-700">Delete Account</p>
            <p className="text-xs text-red-600/70 mt-1">
              Once you delete your account, there is no going back. Please be certain.
            </p>
          </div>

          <button
            onClick={handleDeleteAccount}
            disabled={deleting}
            className="px-6 py-3 border border-red-500 text-red-500 hover:bg-red-500 hover:text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {deleting ? 'Deleting...' : 'Delete Account'}
          </button>
        </div>
      </section>

    </div>
  );
}
