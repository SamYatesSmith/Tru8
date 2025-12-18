'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import { MessageSquare, X, Send, Loader2, CheckCircle, AlertTriangle } from 'lucide-react';
import { apiClient } from '@/lib/api';

interface Claim {
  position: number;
  text: string;
  verdict?: string;
}

const FEEDBACK_TYPES = [
  { value: 'fact-check', label: 'A fact-check result', icon: '📊' },
  { value: 'ui', label: 'The design / UI', icon: '🎨' },
  { value: 'bug', label: "Something's broken", icon: '🐛' },
  { value: 'suggestion', label: 'Feature suggestion', icon: '💡' },
  { value: 'other', label: 'Other', icon: '❓' },
];

export function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState('');
  const [selectedClaim, setSelectedClaim] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-fetched check data for claim selection
  const [currentCheckId, setCurrentCheckId] = useState<string | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);

  const pathname = usePathname();
  const { getToken } = useAuth();
  const { user } = useUser();

  // Detect check page and reset claims when navigating
  useEffect(() => {
    const checkMatch = pathname.match(/\/dashboard\/check\/([a-zA-Z0-9-]+)/);
    const detectedCheckId = checkMatch ? checkMatch[1] : null;

    // Reset claims when checkId changes
    if (detectedCheckId !== currentCheckId) {
      setClaims([]);
      setCurrentCheckId(detectedCheckId);
    }
  }, [pathname, currentCheckId]);

  // Fetch check claims when modal opens on a check page
  useEffect(() => {
    if (isOpen && currentCheckId && claims.length === 0) {
      const fetchCheckData = async () => {
        try {
          const token = await getToken();
          const checkData = await apiClient.getCheckById(currentCheckId, token);
          if (checkData?.claims && Array.isArray(checkData.claims)) {
            setClaims(checkData.claims.map((c: any) => ({
              position: c.position,
              text: c.claimText || c.text || '',
              verdict: c.verdict,
            })));
          }
        } catch (err) {
          console.error('Failed to fetch check data for feedback:', err);
        }
      };
      fetchCheckData();
    }
  }, [isOpen, currentCheckId, getToken, claims.length]);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      // Delay reset to allow close animation
      const timer = setTimeout(() => {
        setFeedbackType('');
        setSelectedClaim('');
        setMessage('');
        setError(null);
        setIsSubmitted(false);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (!message.trim()) {
      setError('Please enter your feedback');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const token = await getToken();

      await apiClient.submitFeedback({
        type: feedbackType || 'other',
        message: message.trim(),
        checkId: currentCheckId || null,
        claimPosition: selectedClaim ? parseInt(selectedClaim) : null,
        claimText: selectedClaim && claims.length > 0
          ? claims.find(c => c.position === parseInt(selectedClaim))?.text || null
          : null,
        pageUrl: pathname,
        userEmail: user?.primaryEmailAddress?.emailAddress || null,
      }, token);

      setIsSubmitted(true);

      // Auto-close after success
      setTimeout(() => {
        setIsOpen(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
      setError('Failed to send feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isOnCheckPage = currentCheckId && claims.length > 0;
  const showClaimSelector = feedbackType === 'fact-check' && isOnCheckPage;

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 bg-[#f57a07] hover:bg-[#e06a00] text-white p-4 rounded-full shadow-lg transition-all hover:scale-105 flex items-center gap-2 group"
        aria-label="Send feedback"
      >
        <MessageSquare size={20} />
        <span className="max-w-0 overflow-hidden group-hover:max-w-xs transition-all duration-300 whitespace-nowrap">
          Feedback
        </span>
      </button>

      {/* Modal Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={(e) => e.target === e.currentTarget && setIsOpen(false)}
        >
          {/* Modal Content */}
          <div className="w-full max-w-md bg-[#1a1f2e] border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <MessageSquare size={20} className="text-[#f57a07]" />
                Send Feedback
              </h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-white transition-colors p-1"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-5 space-y-5">
              {isSubmitted ? (
                // Success State
                <div className="text-center py-8">
                  <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-white mb-2">Thank you!</h3>
                  <p className="text-slate-400">Your feedback has been sent.</p>
                </div>
              ) : (
                <>
                  {/* Testing Period Notice */}
                  <div className="bg-amber-900/20 border border-amber-700/50 rounded-lg px-4 py-3 flex items-start gap-3">
                    <AlertTriangle size={18} className="text-amber-400 flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-amber-300/90">
                      <span className="font-semibold">Testing Period*</span> — This feedback form is for beta testing only and will not be part of the final production release.
                    </p>
                  </div>

                  {/* Feedback Type Dropdown */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      What's this about?
                    </label>
                    <select
                      value={feedbackType}
                      onChange={(e) => {
                        setFeedbackType(e.target.value);
                        setSelectedClaim(''); // Reset claim when type changes
                      }}
                      className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#f57a07]/50 focus:border-[#f57a07] appearance-none cursor-pointer"
                    >
                      <option value="" className="text-slate-400">Select one...</option>
                      {FEEDBACK_TYPES.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.icon} {type.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Claim Selector (conditional) */}
                  {showClaimSelector && (
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Which claim?
                      </label>
                      <select
                        value={selectedClaim}
                        onChange={(e) => setSelectedClaim(e.target.value)}
                        className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#f57a07]/50 focus:border-[#f57a07] appearance-none cursor-pointer"
                      >
                        <option value="">Overall check result</option>
                        {claims.map((claim) => (
                          <option key={claim.position} value={claim.position}>
                            Claim {claim.position}: {claim.text.slice(0, 50)}...
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Message */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Your feedback
                    </label>
                    <textarea
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      placeholder="Tell us what's on your mind..."
                      rows={4}
                      className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#f57a07]/50 focus:border-[#f57a07] resize-none"
                    />
                  </div>

                  {/* Error Message */}
                  {error && (
                    <p className="text-sm text-red-400">{error}</p>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            {!isSubmitted && (
              <div className="px-6 py-4 border-t border-slate-700 bg-slate-900/30">
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || !message.trim()}
                  className="w-full bg-[#f57a07] hover:bg-[#e06a00] disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-bold py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send size={18} />
                      Send Feedback
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
