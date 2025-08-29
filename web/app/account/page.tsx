'use client';

import { useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { MainLayout } from "@/components/layout/main-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBar } from "@/components/check/confidence-bar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  CreditCard, 
  User, 
  BarChart3, 
  Settings, 
  Calendar,
  TrendingUp,
  Download,
  RefreshCw
} from "lucide-react";
import { getUserProfile, getUserUsage } from "@/lib/api";
import { useAuth } from "@clerk/nextjs";
import type { UserProfile, UserUsage } from "@shared/types";

export default function AccountPage() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");

  const { data: profile, isLoading: profileLoading, refetch: refetchProfile } = useQuery({
    queryKey: ["user", "profile"],
    queryFn: async () => {
      const token = await getToken();
      return getUserProfile(token!);
    },
    enabled: !!user,
  });

  const { data: usage, isLoading: usageLoading, refetch: refetchUsage } = useQuery({
    queryKey: ["user", "usage"],
    queryFn: async () => {
      const token = await getToken();
      return getUserUsage(token!);
    },
    enabled: !!user,
  });

  const isLoading = profileLoading || usageLoading;

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getSubscriptionStatusColor = (status: string | null) => {
    switch (status) {
      case 'active':
        return 'verdict-supported';
      case 'past_due':
        return 'verdict-uncertain';
      case 'cancelled':
        return 'verdict-contradicted';
      default:
        return 'outline';
    }
  };

  const getPlanDisplayName = (plan: string | null) => {
    if (!plan || plan === 'free') return 'Free Plan';
    return plan.charAt(0).toUpperCase() + plan.slice(1) + ' Plan';
  };

  const getUsagePercentage = () => {
    if (!usage?.subscription) return 0;
    const { creditsPerMonth } = usage.subscription;
    const used = usage.totalCreditsUsed;
    return creditsPerMonth > 0 ? (used / creditsPerMonth) * 100 : 0;
  };

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
      {/* Hero Section */}
      <div className="relative bg-gradient-to-br from-tru8-primary via-purple-600 to-pink-500 text-white">
        <div className="container py-12">
          <div className="flex items-center justify-between">
            <div className="space-y-4">
              <h1 className="text-5xl font-black">
                Account Management
              </h1>
              <p className="text-xl opacity-90">
                Manage your subscription, usage, and account settings
              </p>
            </div>
            
            <div className="hidden md:flex items-center space-x-4">
              <Button 
                variant="ghost" 
                className="text-white hover:bg-white/10"
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
        </div>
      </div>

      <div className="container py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-8">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="subscription" className="flex items-center gap-2">
              <CreditCard className="h-4 w-4" />
              Subscription
            </TabsTrigger>
            <TabsTrigger value="usage" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Usage
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Settings
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Credits Remaining Card */}
              <Card className="card-featured">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Credits Remaining</CardTitle>
                  <CreditCard className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{usage?.creditsRemaining || 0}</div>
                  <p className="text-xs text-muted-foreground">
                    of {usage?.subscription?.creditsPerMonth || 3} monthly credits
                  </p>
                  <div className="mt-3">
                    <ConfidenceBar
                      confidence={(usage?.creditsRemaining || 0) / (usage?.subscription?.creditsPerMonth || 3) * 100}
                      verdict="supported"
                      size="sm"
                      animated
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Total Checks Card */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Checks</CardTitle>
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{profile?.stats?.totalChecks || 0}</div>
                  <p className="text-xs text-muted-foreground">
                    {profile?.stats?.completedChecks || 0} completed, {profile?.stats?.failedChecks || 0} failed
                  </p>
                </CardContent>
              </Card>

              {/* Current Plan Card */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Current Plan</CardTitle>
                  <Badge className={getSubscriptionStatusColor(usage?.subscription?.plan || null)}>
                    {getPlanDisplayName(usage?.subscription?.plan || null)}
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {usage?.subscription?.creditsPerMonth || 3}
                  </div>
                  <p className="text-xs text-muted-foreground">credits per month</p>
                </CardContent>
              </Card>
            </div>

            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Account Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Email:</span>
                      <span className="font-medium">{profile?.email}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Member since:</span>
                      <span className="font-medium">{formatDate(profile?.createdAt || null)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Total credits used:</span>
                      <span className="font-medium">{profile?.totalCreditsUsed || 0}</span>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Success rate:</span>
                      <span className="font-medium">
                        {profile?.stats?.totalChecks ? 
                          Math.round((profile.stats.completedChecks / profile.stats.totalChecks) * 100) : 0}%
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Avg. processing time:</span>
                      <span className="font-medium">8.5s</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Subscription Tab */}
          <TabsContent value="subscription" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Current Subscription */}
              <div className="lg:col-span-2 space-y-6">
                <Card className="card-featured">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <CreditCard className="h-5 w-5" />
                      Current Subscription
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-semibold">
                        {getPlanDisplayName(profile?.subscription?.plan || null)}
                      </span>
                      <Badge className={getSubscriptionStatusColor(profile?.subscription?.status || null)}>
                        {profile?.subscription?.status || 'Free'}
                      </Badge>
                    </div>
                    
                    {profile?.subscription ? (
                      <div className="space-y-3">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Credits per month:</span>
                          <span className="font-medium">{profile.subscription.creditsPerMonth}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Current period ends:</span>
                          <span className="font-medium">{formatDate(profile.subscription.currentPeriodEnd)}</span>
                        </div>
                        
                        <div className="pt-4 border-t">
                          <Button variant="outline" className="w-full">
                            Manage Subscription
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <p className="text-gray-600">
                          You're currently on the free plan with 3 credits per week.
                        </p>
                        <Button className="btn-primary w-full">
                          Upgrade to Pro
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Plan Comparison */}
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Available Plans</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-3">
                      <div className="p-3 border rounded-lg">
                        <div className="font-semibold">Free Plan</div>
                        <div className="text-sm text-gray-600">3 credits/week</div>
                        <div className="text-sm font-medium">£0/month</div>
                      </div>
                      
                      <div className="p-3 border-2 rounded-lg" style={{ borderColor: 'var(--tru8-primary)', backgroundColor: 'var(--gray-50)' }}>
                        <div className="font-semibold">Starter Plan</div>
                        <div className="text-sm text-gray-600">120 credits/month</div>
                        <div className="text-sm font-medium">£6.99/month</div>
                        <Badge variant="outline" className="mt-1">Popular</Badge>
                      </div>
                      
                      <div className="p-3 border rounded-lg">
                        <div className="font-semibold">Pro Plan</div>
                        <div className="text-sm text-gray-600">300 credits/month</div>
                        <div className="text-sm font-medium">£12.99/month</div>
                      </div>
                    </div>
                    
                    <Button className="btn-primary w-full">
                      Change Plan
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Usage Tab */}
          <TabsContent value="usage" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2 space-y-6">
                {/* Usage Overview */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5" />
                      Usage Overview
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Current Period Usage</span>
                        <span className="font-semibold">
                          {usage?.totalCreditsUsed || 0} of {usage?.subscription?.creditsPerMonth || 3} credits
                        </span>
                      </div>
                      <ConfidenceBar
                        confidence={getUsagePercentage()}
                        verdict={getUsagePercentage() > 90 ? "uncertain" : "supported"}
                        size="lg"
                        animated
                      />
                      <div className="text-xs text-gray-500">
                        {usage?.subscription?.resetDate && 
                          `Resets on ${formatDate(usage.subscription.resetDate)}`
                        }
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 pt-4 border-t">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">{profile?.stats?.completedChecks || 0}</div>
                        <div className="text-xs text-gray-600">Completed</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600">{profile?.stats?.failedChecks || 0}</div>
                        <div className="text-xs text-gray-600">Failed</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-600">{usage?.creditsRemaining || 0}</div>
                        <div className="text-xs text-gray-600">Remaining</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Usage History Placeholder */}
                <Card>
                  <CardHeader>
                    <CardTitle>Usage History</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-8">
                      <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-600">Detailed usage analytics coming soon</p>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Usage Stats Sidebar */}
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Quick Stats</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">This month:</span>
                      <span className="font-medium">{usage?.totalCreditsUsed || 0} credits</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Average per check:</span>
                      <span className="font-medium">1.2 credits</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Peak usage day:</span>
                      <span className="font-medium">Monday</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Export Data</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-gray-600">
                      Download your usage data and check history.
                    </p>
                    <Button variant="outline" className="w-full">
                      <Download className="h-4 w-4 mr-2" />
                      Export Usage
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Account Settings */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <User className="h-5 w-5" />
                    Account Settings
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-700">Email</label>
                      <div className="text-sm text-gray-600 mt-1">{profile?.email}</div>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700">Name</label>
                      <div className="text-sm text-gray-600 mt-1">{user?.fullName || 'Not set'}</div>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t">
                    <Button variant="outline">Update Profile</Button>
                  </div>
                </CardContent>
              </Card>

              {/* Preferences */}
              <Card>
                <CardHeader>
                  <CardTitle>Preferences</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Email notifications</span>
                      <Badge variant="outline">Enabled</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Dark mode</span>
                      <Badge variant="outline">Coming soon</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">API access</span>
                      <Badge variant="outline">Pro only</Badge>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t">
                    <Button variant="outline">Update Preferences</Button>
                  </div>
                </CardContent>
              </Card>

              {/* Danger Zone */}
              <Card className="lg:col-span-2 border-red-200">
                <CardHeader>
                  <CardTitle className="text-red-600">Danger Zone</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Delete Account</div>
                      <div className="text-sm text-gray-600">
                        Permanently delete your account and all data. This cannot be undone.
                      </div>
                    </div>
                    <Button variant="outline" className="text-red-600 hover:bg-red-50 hover:border-red-300">
                      Delete Account
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}