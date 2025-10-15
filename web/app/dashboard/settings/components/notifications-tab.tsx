'use client';

import { useState, useEffect } from 'react';
import { Bell } from 'lucide-react';

interface NotificationPreferences {
  emailEnabled: boolean;
  checkCompletion: boolean;
  weeklyDigest: boolean;
  marketing: boolean;
}

export function NotificationsTab() {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    emailEnabled: true,
    checkCompletion: true,
    weeklyDigest: false,
    marketing: false,
  });

  // Load from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const saved = localStorage.getItem('notificationPrefs');
    if (saved) {
      try {
        setPreferences(JSON.parse(saved));
      } catch (error) {
        console.error('Failed to parse notification preferences:', error);
      }
    }
  }, []);

  // Save to localStorage on change
  const updatePreference = (key: keyof NotificationPreferences, value: boolean) => {
    const updated = { ...preferences, [key]: value };

    // If master toggle is disabled, disable all others
    if (key === 'emailEnabled' && !value) {
      updated.checkCompletion = false;
      updated.weeklyDigest = false;
      updated.marketing = false;
    }

    setPreferences(updated);
    if (typeof window !== 'undefined') {
      localStorage.setItem('notificationPrefs', JSON.stringify(updated));
    }
  };

  return (
    <div className="space-y-8">
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Bell size={20} />
          Email Notifications
        </h3>

        <div className="space-y-6">
          {/* Master Toggle */}
          <div className="flex items-center justify-between pb-6 border-b border-slate-700">
            <div>
              <p className="text-sm font-medium text-white">Email Notifications</p>
              <p className="text-xs text-slate-400 mt-1">
                Receive notifications via email
              </p>
            </div>
            <button
              onClick={() => updatePreference('emailEnabled', !preferences.emailEnabled)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.emailEnabled ? 'bg-[#f57a07]' : 'bg-slate-600'
              }`}
              aria-label="Toggle email notifications"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.emailEnabled ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Check Completion */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Check Completion</p>
              <p className="text-xs text-slate-400 mt-1">
                Get notified when your fact-checks are complete
              </p>
            </div>
            <button
              onClick={() =>
                updatePreference('checkCompletion', !preferences.checkCompletion)
              }
              disabled={!preferences.emailEnabled}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.checkCompletion && preferences.emailEnabled
                  ? 'bg-[#f57a07]'
                  : 'bg-slate-600'
              } ${!preferences.emailEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-label="Toggle check completion notifications"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.checkCompletion && preferences.emailEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Weekly Digest */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Weekly Digest</p>
              <p className="text-xs text-slate-400 mt-1">
                Receive a weekly summary of your activity
              </p>
            </div>
            <button
              onClick={() => updatePreference('weeklyDigest', !preferences.weeklyDigest)}
              disabled={!preferences.emailEnabled}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.weeklyDigest && preferences.emailEnabled
                  ? 'bg-[#f57a07]'
                  : 'bg-slate-600'
              } ${!preferences.emailEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-label="Toggle weekly digest"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.weeklyDigest && preferences.emailEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Marketing Emails */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Marketing Emails</p>
              <p className="text-xs text-slate-400 mt-1">
                Receive updates about new features and offers
              </p>
            </div>
            <button
              onClick={() => updatePreference('marketing', !preferences.marketing)}
              disabled={!preferences.emailEnabled}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.marketing && preferences.emailEnabled
                  ? 'bg-[#f57a07]'
                  : 'bg-slate-600'
              } ${!preferences.emailEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-label="Toggle marketing emails"
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.marketing && preferences.emailEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        <div className="mt-6 p-4 bg-blue-900/20 border border-blue-700 rounded-lg">
          <p className="text-xs text-blue-300">
            ℹ️ <strong>Note:</strong> Notification preferences are currently stored locally.
            Backend sync coming in Phase 2.
          </p>
        </div>
      </section>
    </div>
  );
}
