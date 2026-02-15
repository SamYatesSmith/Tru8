'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Bell, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/api';

interface NotificationPreferences {
  emailNotificationsEnabled: boolean;
  checkCompletion: boolean;
  checkFailure: boolean;
  weeklyDigest: boolean;
  marketing: boolean;
}

const defaultPreferences: NotificationPreferences = {
  emailNotificationsEnabled: true,
  checkCompletion: true,
  checkFailure: true,
  weeklyDigest: false,
  marketing: false,
};

export function NotificationsTab() {
  const { getToken } = useAuth();
  const [preferences, setPreferences] = useState<NotificationPreferences>(defaultPreferences);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  // Load preferences from API on mount
  useEffect(() => {
    const fetchPreferences = async () => {
      try {
        setLoading(true);
        setError(null);
        const token = await getToken();
        const data = await apiClient.getEmailPreferences(token);
        setPreferences({
          emailNotificationsEnabled: data.emailNotificationsEnabled,
          checkCompletion: data.checkCompletion,
          checkFailure: data.checkFailure,
          weeklyDigest: data.weeklyDigest,
          marketing: data.marketing,
        });
        // Save to localStorage as backup
        if (typeof window !== 'undefined') {
          localStorage.setItem('notificationPrefs', JSON.stringify(data));
        }
      } catch (err) {
        console.error('Failed to fetch notification preferences:', err);
        // Fall back to localStorage if API fails
        if (typeof window !== 'undefined') {
          const saved = localStorage.getItem('notificationPrefs');
          if (saved) {
            try {
              const parsed = JSON.parse(saved);
              setPreferences({
                emailNotificationsEnabled: parsed.emailNotificationsEnabled ?? parsed.emailEnabled ?? true,
                checkCompletion: parsed.checkCompletion ?? true,
                checkFailure: parsed.checkFailure ?? true,
                weeklyDigest: parsed.weeklyDigest ?? false,
                marketing: parsed.marketing ?? false,
              });
            } catch {
              // Use defaults
            }
          }
        }
        setError('Unable to load preferences from server. Using local settings.');
      } finally {
        setLoading(false);
      }
    };

    fetchPreferences();
  }, [getToken]);

  // Save preferences to API
  const savePreferences = useCallback(async (updated: NotificationPreferences) => {
    try {
      setSaving(true);
      setError(null);
      const token = await getToken();
      await apiClient.updateEmailPreferences({
        email_notifications_enabled: updated.emailNotificationsEnabled,
        email_check_completion: updated.checkCompletion,
        email_check_failure: updated.checkFailure,
        email_weekly_digest: updated.weeklyDigest,
        email_marketing: updated.marketing,
      }, token);
      // Update localStorage backup
      if (typeof window !== 'undefined') {
        localStorage.setItem('notificationPrefs', JSON.stringify(updated));
      }
      setLastSaved(new Date());
    } catch (err) {
      console.error('Failed to save notification preferences:', err);
      setError('Failed to save preferences. Please try again.');
    } finally {
      setSaving(false);
    }
  }, [getToken]);

  // Update preference with optimistic update
  const updatePreference = (key: keyof NotificationPreferences, value: boolean) => {
    let updated = { ...preferences, [key]: value };

    // If master toggle is disabled, disable all others
    if (key === 'emailNotificationsEnabled' && !value) {
      updated = {
        ...updated,
        checkCompletion: false,
        checkFailure: false,
        weeklyDigest: false,
        marketing: false,
      };
    }

    // Optimistic update
    setPreferences(updated);
    // Save to backend
    savePreferences(updated);
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <section className="bg-white border border-zinc-200 p-6">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-zinc-400 animate-spin" />
            <span className="ml-3 text-zinc-400">Loading preferences...</span>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="bg-white border border-zinc-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
            <Bell size={20} />
            Email Notifications
          </h3>
          {saving && (
            <span className="flex items-center text-xs text-zinc-400">
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              Saving...
            </span>
          )}
          {!saving && lastSaved && (
            <span className="flex items-center text-xs text-emerald-500">
              <CheckCircle className="w-3 h-3 mr-1" />
              Saved
            </span>
          )}
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
            <p className="text-xs text-red-600">{error}</p>
          </div>
        )}

        <div className="space-y-6">
          {/* Master Toggle */}
          <div className="flex items-center justify-between pb-6 border-b border-zinc-100">
            <div>
              <p className="text-sm font-medium text-zinc-900">Email Notifications</p>
              <p className="text-xs text-zinc-500 mt-1">
                Receive notifications via email
              </p>
            </div>
            <button
              onClick={() => updatePreference('emailNotificationsEnabled', !preferences.emailNotificationsEnabled)}
              disabled={saving}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.emailNotificationsEnabled ? 'bg-zinc-900' : 'bg-zinc-200'
              } ${saving ? 'opacity-50' : ''}`}
              aria-label="Toggle email notifications"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.emailNotificationsEnabled ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Check Completion */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-900">Check Completion</p>
              <p className="text-xs text-zinc-500 mt-1">
                Get notified when your analyses are complete
              </p>
            </div>
            <button
              onClick={() => updatePreference('checkCompletion', !preferences.checkCompletion)}
              disabled={!preferences.emailNotificationsEnabled || saving}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.checkCompletion && preferences.emailNotificationsEnabled
                  ? 'bg-zinc-900'
                  : 'bg-zinc-200'
              } ${!preferences.emailNotificationsEnabled || saving ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-label="Toggle check completion notifications"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.checkCompletion && preferences.emailNotificationsEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Check Failures */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-900">Check Failures</p>
              <p className="text-xs text-zinc-500 mt-1">
                Get notified if an analysis encounters an issue
              </p>
            </div>
            <button
              onClick={() => updatePreference('checkFailure', !preferences.checkFailure)}
              disabled={!preferences.emailNotificationsEnabled || saving}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.checkFailure && preferences.emailNotificationsEnabled
                  ? 'bg-zinc-900'
                  : 'bg-zinc-200'
              } ${!preferences.emailNotificationsEnabled || saving ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-label="Toggle check failure notifications"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.checkFailure && preferences.emailNotificationsEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Weekly Digest */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-900">Weekly Digest</p>
              <p className="text-xs text-zinc-500 mt-1">
                Receive a weekly summary of your activity
              </p>
            </div>
            <button
              onClick={() => updatePreference('weeklyDigest', !preferences.weeklyDigest)}
              disabled={!preferences.emailNotificationsEnabled || saving}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.weeklyDigest && preferences.emailNotificationsEnabled
                  ? 'bg-zinc-900'
                  : 'bg-zinc-200'
              } ${!preferences.emailNotificationsEnabled || saving ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-label="Toggle weekly digest"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.weeklyDigest && preferences.emailNotificationsEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Marketing Emails */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-900">Marketing Emails</p>
              <p className="text-xs text-zinc-500 mt-1">
                Receive updates about new features and offers
              </p>
            </div>
            <button
              onClick={() => updatePreference('marketing', !preferences.marketing)}
              disabled={!preferences.emailNotificationsEnabled || saving}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.marketing && preferences.emailNotificationsEnabled
                  ? 'bg-zinc-900'
                  : 'bg-zinc-200'
              } ${!preferences.emailNotificationsEnabled || saving ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-label="Toggle marketing emails"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.marketing && preferences.emailNotificationsEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200">
          <p className="text-xs text-emerald-700">
            <CheckCircle className="w-3 h-3 inline mr-1" />
            Your notification preferences are synced across all devices.
          </p>
        </div>
      </section>
    </div>
  );
}
