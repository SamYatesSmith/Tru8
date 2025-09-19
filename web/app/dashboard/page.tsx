'use client';

import { useUser, useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { MainLayout } from "@/components/layout/main-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, Clock, CheckCircle, XCircle, ArrowRight, RefreshCw } from "lucide-react";
import Link from "next/link";
import { getUserProfile, getUserUsage, getChecks } from "@/lib/api";
import type { UserProfile, UserUsage } from "@shared/types";

export default function DashboardPage() {
  const { user } = useUser();
  const { getToken } = useAuth();

  const { data: profile, isLoading: profileLoading, refetch: refetchProfile, error: profileError } = useQuery({
    queryKey: ["user", "profile"],
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error('No authentication token available');
      return getUserProfile(token);
    },
    enabled: !!user,
    retry: false,
  });

  const { data: usage, isLoading: usageLoading, refetch: refetchUsage, error: usageError } = useQuery({
    queryKey: ["user", "usage"],
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error('No authentication token available');
      return getUserUsage(token);
    },
    enabled: !!user,
    retry: false,
  });

  const { data: checksData, isLoading: checksLoading, error: checksError } = useQuery({
    queryKey: ["checks", "recent"],
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error('No authentication token available');
      return getChecks(token, 0, 5); // Get 5 most recent checks
    },
    enabled: !!user,
    retry: false,
  });

  const isLoading = profileLoading || usageLoading || checksLoading;
  const recentChecks = checksData?.checks || [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="verdict-supported">Completed</Badge>;
      case 'processing':
        return <Badge className="verdict-uncertain">Processing</Badge>;
      case 'failed':
        return <Badge className="verdict-contradicted">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return 'Just now';
  };

  // Show errors if any
  const hasErrors = profileError || usageError || checksError;
  if (hasErrors) {
    return (
      <MainLayout>
        <div className="container py-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-900 mb-4">Authentication Error</h2>
            <div className="space-y-2 text-sm text-red-700">
              {profileError && <p>Profile error: {profileError.message}</p>}
              {usageError && <p>Usage error: {usageError.message}</p>}
              {checksError && <p>Checks error: {checksError.message}</p>}
            </div>
            <p className="mt-4 text-sm text-red-600">
              Please try signing out and signing back in to refresh your authentication.
            </p>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (isLoading) {
    return (
      <MainLayout>
        <div className="container py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-48 bg-gray-200 rounded"></div>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="container py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Welcome back, {user?.firstName || 'there'}!
            </h1>
            <p className="text-xl text-gray-600">
              Your fact-checking dashboard
            </p>
          </div>
          <div className="hidden md:flex items-center space-x-4">
            <Button 
              variant="ghost" 
              onClick={() => {
                refetchProfile();
                refetchUsage();
              }}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Quick Check Card */}
            <div className="card card-featured">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-semibold text-gray-900">
                  Start New Check
                </h2>
                <Plus className="h-6 w-6" style={{color: 'var(--tru8-primary)'}} />
              </div>
              <p className="text-gray-600 mb-6">
                Quickly verify claims from URLs, images, videos, or text content.
              </p>
              <Button className="btn-primary w-full" size="lg" asChild>
                <Link href="/checks/new">
                  Create Fact-Check
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Link>
              </Button>
            </div>

            {/* Recent Checks */}
            <div className="card">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-semibold text-gray-900">
                  Recent Checks
                </h2>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/checks">View All</Link>
                </Button>
              </div>

              {recentChecks.length > 0 ? (
                <div className="space-y-4">
                  {recentChecks.map((check) => (
                    <div 
                      key={check.id}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <Badge variant="outline" className="capitalize">
                            {check.inputType}
                          </Badge>
                          {getStatusBadge(check.status)}
                          <span className="text-sm text-gray-500">
                            {check.claimsCount || check.claims?.length || 0} claim{(check.claimsCount || check.claims?.length || 0) !== 1 ? 's' : ''}
                          </span>
                        </div>
                        
                        <div className="text-sm text-gray-600">
                          {check.inputUrl ? (
                            <span className="truncate block max-w-md">
                              {check.inputUrl}
                            </span>
                          ) : (
                            <span>Text content check</span>
                          )}
                        </div>
                        
                        <div className="text-xs text-gray-500 mt-1">
                          {formatTimeAgo(check.createdAt)}
                          {check.processingTimeMs && (
                            <span className="ml-2">
                              • {(check.processingTimeMs / 1000).toFixed(1)}s processing
                            </span>
                          )}
                        </div>
                      </div>

                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/checks/${check.id}`}>
                          View
                          <ArrowRight className="h-3 w-3 ml-1" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <CheckCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 mb-4">No checks yet</p>
                  <Button className="btn-primary" asChild>
                    <Link href="/checks/new">Create Your First Check</Link>
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Usage Stats */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Usage Statistics
              </h3>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-gray-600">Credits Remaining</span>
                    <span className="font-semibold text-gray-900">
                      {usage?.creditsRemaining || 0}
                    </span>
                  </div>
                  <div className="confidence-bar">
                    <div 
                      className="confidence-fill" 
                      style={{ 
                        width: `${((usage?.creditsRemaining || 0) / (usage?.subscription?.creditsPerMonth || 3)) * 100}%` 
                      }} 
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-200">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Plan</span>
                    <span className="font-medium capitalize">{usage?.subscription?.plan || 'free'}</span>
                  </div>
                  <div className="flex justify-between text-sm mt-2">
                    <span className="text-gray-600">Monthly Limit</span>
                    <span className="font-medium">{usage?.subscription?.creditsPerMonth || 3}</span>
                  </div>
                  <div className="flex justify-between text-sm mt-2">
                    <span className="text-gray-600">Used This Month</span>
                    <span className="font-medium">{usage?.totalCreditsUsed || 0}</span>
                  </div>
                </div>

                <Button className="w-full" variant="outline" asChild>
                  <Link href="/account">Manage Subscription</Link>
                </Button>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Quick Stats
              </h3>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-gray-600">Completed</span>
                  </div>
                  <span className="font-medium">{profile?.stats?.completedChecks || 0}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-amber-600" />
                    <span className="text-sm text-gray-600">Processing</span>
                  </div>
                  <span className="font-medium">{recentChecks.filter(c => c.status === 'processing').length}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <XCircle className="h-4 w-4 text-red-600" />
                    <span className="text-sm text-gray-600">Failed</span>
                  </div>
                  <span className="font-medium">{profile?.stats?.failedChecks || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}