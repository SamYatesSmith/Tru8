'use client';

import { useState } from "react";
import { useUser, useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { MainLayout } from "@/components/layout/main-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { 
  User, 
  Bell, 
  Shield, 
  CreditCard,
  Key,
  Trash2,
  Settings as SettingsIcon,
  Eye,
  Download,
  Moon,
  Sun
} from "lucide-react";
import { getUserProfile } from "@/lib/api";
import type { UserProfile } from "@shared/types";

export default function SettingsPage() {
  const { user } = useUser();
  const { getToken } = useAuth();
  
  // Local state for settings
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [publicProfile, setPublicProfile] = useState(false);

  const { data: profile } = useQuery({
    queryKey: ["user", "profile"],
    queryFn: async () => {
      const token = await getToken();
      return getUserProfile(token!);
    },
    enabled: !!user,
  });

  const handleSaveProfile = () => {
    // TODO: Implement profile update API call
    console.log('Saving profile...');
  };

  const handleExportData = () => {
    // TODO: Implement data export
    console.log('Exporting user data...');
  };

  const handleDeleteAccount = () => {
    // TODO: Implement account deletion
    console.log('Deleting account...');
  };

  return (
    <MainLayout>
      {/* Header */}
      <div className="relative bg-gradient-to-br from-gray-50 to-gray-100 border-b">
        <div className="container py-8">
          <div className="flex items-center gap-4">
            <SettingsIcon className="h-8 w-8 text-gray-600" />
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Settings</h1>
              <p className="text-lg text-gray-600 mt-1">
                Manage your account preferences and settings
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="container py-8">
        <Tabs defaultValue="profile" className="space-y-8">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="profile" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Profile
            </TabsTrigger>
            <TabsTrigger value="notifications" className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              Notifications
            </TabsTrigger>
            <TabsTrigger value="privacy" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Privacy
            </TabsTrigger>
            <TabsTrigger value="billing" className="flex items-center gap-2">
              <CreditCard className="h-4 w-4" />
              Billing
            </TabsTrigger>
            <TabsTrigger value="account" className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              Account
            </TabsTrigger>
          </TabsList>

          {/* Profile Settings */}
          <TabsContent value="profile" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Profile Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First Name</Label>
                    <Input
                      id="firstName"
                      placeholder="Enter your first name"
                      defaultValue={user?.firstName || ''}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input
                      id="lastName"
                      placeholder="Enter your last name"
                      defaultValue={user?.lastName || ''}
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    defaultValue={profile?.email || user?.emailAddresses[0]?.emailAddress || ''}
                    disabled
                  />
                  <p className="text-xs text-gray-500">
                    Email changes must be made through your account provider.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <select
                    id="timezone"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="UTC">UTC (GMT+0)</option>
                    <option value="Europe/London" selected>London (GMT+0/+1)</option>
                    <option value="America/New_York">New York (GMT-5/-4)</option>
                    <option value="America/Los_Angeles">Los Angeles (GMT-8/-7)</option>
                  </select>
                </div>

                <div className="pt-4 border-t">
                  <Button onClick={handleSaveProfile}>
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Display Preferences</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-base font-medium">Theme</Label>
                    <p className="text-sm text-gray-600">Choose your preferred theme</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Sun className="h-4 w-4" />
                    <Switch
                      checked={darkMode}
                      onCheckedChange={setDarkMode}
                      disabled
                    />
                    <Moon className="h-4 w-4" />
                  </div>
                </div>
                <p className="text-xs text-gray-500">Dark mode coming soon!</p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notification Settings */}
          <TabsContent value="notifications" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  Email Notifications
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-base font-medium">Fact-check complete</Label>
                    <p className="text-sm text-gray-600">Get notified when your checks finish processing</p>
                  </div>
                  <Switch
                    checked={emailNotifications}
                    onCheckedChange={setEmailNotifications}
                  />
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-base font-medium">Weekly usage summary</Label>
                    <p className="text-sm text-gray-600">Receive weekly reports about your usage</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-base font-medium">Product updates</Label>
                    <p className="text-sm text-gray-600">Stay informed about new features and improvements</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-base font-medium">Marketing emails</Label>
                    <p className="text-sm text-gray-600">Tips, guides, and promotional content</p>
                  </div>
                  <Switch />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Push Notifications</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-base font-medium">Browser notifications</Label>
                    <p className="text-sm text-gray-600">Show notifications in your browser</p>
                  </div>
                  <Switch
                    checked={pushNotifications}
                    onCheckedChange={setPushNotifications}
                  />
                </div>
                
                <p className="text-xs text-gray-500">
                  Browser notifications require permission. You'll be prompted when enabling.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Privacy Settings */}
          <TabsContent value="privacy" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Data & Privacy
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-base font-medium">Analytics</Label>
                    <p className="text-sm text-gray-600">Help us improve by sharing anonymous usage data</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-base font-medium">Public profile</Label>
                    <p className="text-sm text-gray-600">Make your profile visible to other users</p>
                  </div>
                  <Switch
                    checked={publicProfile}
                    onCheckedChange={setPublicProfile}
                  />
                </div>

                <Separator />

                <div className="space-y-3">
                  <Label className="text-base font-medium">Data retention</Label>
                  <p className="text-sm text-gray-600">
                    Your uploaded files are automatically deleted after 30 days. 
                    Fact-check results are kept indefinitely unless you delete them.
                  </p>
                  <Button variant="outline" onClick={handleExportData}>
                    <Download className="h-4 w-4 mr-2" />
                    Export My Data
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Billing Settings */}
          <TabsContent value="billing" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5" />
                  Subscription & Billing
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <div className="font-medium">Current Plan</div>
                    <div className="text-sm text-gray-600">
                      {profile?.subscription?.plan ? (
                        <>
                          {profile.subscription.plan.charAt(0).toUpperCase() + profile.subscription.plan.slice(1)} Plan
                          <Badge className="ml-2 verdict-supported">{profile.subscription.status}</Badge>
                        </>
                      ) : (
                        "Free Plan"
                      )}
                    </div>
                  </div>
                  <Button variant="outline" asChild>
                    <a href="/pricing">Change Plan</a>
                  </Button>
                </div>

                {profile?.subscription && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <Label className="font-medium">Credits per month</Label>
                      <div className="text-gray-600">{profile.subscription.creditsPerMonth}</div>
                    </div>
                    <div>
                      <Label className="font-medium">Next billing date</Label>
                      <div className="text-gray-600">
                        {profile.subscription.currentPeriodEnd ? 
                          new Date(profile.subscription.currentPeriodEnd).toLocaleDateString() : 
                          'N/A'
                        }
                      </div>
                    </div>
                  </div>
                )}

                <div className="pt-4 border-t space-y-3">
                  <Button variant="outline" className="w-full">
                    <CreditCard className="h-4 w-4 mr-2" />
                    Manage Payment Methods
                  </Button>
                  <Button variant="outline" className="w-full">
                    <Download className="h-4 w-4 mr-2" />
                    Download Receipts
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Account Settings */}
          <TabsContent value="account" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  Account Security
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <Label className="text-base font-medium">Password</Label>
                  <p className="text-sm text-gray-600">
                    Your account is secured through your authentication provider. 
                    To change your password, visit your provider's settings.
                  </p>
                  <Button variant="outline">
                    Manage Authentication
                  </Button>
                </div>

                <Separator />

                <div className="space-y-3">
                  <Label className="text-base font-medium">Two-Factor Authentication</Label>
                  <p className="text-sm text-gray-600">
                    Add an extra layer of security to your account.
                  </p>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">Not configured</Badge>
                    <Button variant="outline" size="sm">
                      Set up 2FA
                    </Button>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <Label className="text-base font-medium">API Access</Label>
                  <p className="text-sm text-gray-600">
                    Generate API keys to access Tru8 programmatically.
                  </p>
                  <Badge variant="outline">Pro feature - Coming soon</Badge>
                </div>
              </CardContent>
            </Card>

            {/* Danger Zone */}
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-red-600 flex items-center gap-2">
                  <Trash2 className="h-5 w-5" />
                  Danger Zone
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                  <div className="flex items-start justify-between">
                    <div className="space-y-2">
                      <Label className="text-base font-medium text-red-900">Delete Account</Label>
                      <p className="text-sm text-red-700">
                        Permanently delete your account and all associated data. 
                        This action cannot be undone.
                      </p>
                    </div>
                    <Button 
                      variant="outline" 
                      className="text-red-600 hover:bg-red-50 hover:border-red-300 ml-4"
                      onClick={handleDeleteAccount}
                    >
                      Delete Account
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}