'use client';

import { useState } from "react";
import { useUser, useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { MainLayout } from "@/components/layout/main-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PricingCard } from "@/components/payments/pricing-card";
import { CheckoutModal } from "@/components/payments/checkout-modal";
import { 
  Check, 
  Zap,
  Shield,
  Clock,
  CreditCard,
  HeadphonesIcon,
  ArrowRight 
} from "lucide-react";
import Link from "next/link";
import { PRICING_PLANS, PricingPlan } from "@/lib/stripe";
import { getUserUsage } from "@/lib/api";
import type { UserUsage } from "@shared/types";

export default function PricingPage() {
  const { user } = useUser();
  const { getToken } = useAuth();

  const { data: usage } = useQuery({
    queryKey: ["user", "usage"],
    queryFn: async () => {
      const token = await getToken();
      return getUserUsage(token!);
    },
    enabled: !!user,
  });

  const currentPlan = usage?.subscription?.plan || 'free';

  const handleUpgrade = async (plan: PricingPlan) => {
    // The CheckoutModal component will handle the actual upgrade flow
    console.log(`Upgrading to ${plan}`);
  };

  return (
    <MainLayout>
      {/* Hero Section */}
      <div className="relative bg-gradient-to-br from-tru8-primary via-purple-600 to-pink-500 text-white">
        <div className="container py-16 text-center">
          <h1 className="text-5xl font-black mb-6">
            Choose Your Plan
          </h1>
          <p className="text-xl opacity-90 mb-8 max-w-2xl mx-auto">
            Get instant fact-checking with dated evidence. Upgrade for more checks and advanced features.
          </p>
          
          {user && (
            <div className="inline-flex items-center gap-2 bg-white/10 rounded-full px-4 py-2">
              <span className="text-sm">Current plan:</span>
              <Badge className="capitalize bg-white text-gray-900">
                {currentPlan === 'free' ? 'Free' : PRICING_PLANS[currentPlan as PricingPlan]?.name}
              </Badge>
            </div>
          )}
        </div>
      </div>

      <div className="container py-16">
        {/* Free Plan */}
        <div className="mb-12">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-4">Start for Free</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Try Tru8 with our free plan. Perfect for occasional fact-checking needs.
            </p>
          </div>
          
          <div className="max-w-md mx-auto">
            <Card className={`${currentPlan === 'free' ? 'card-featured border-2' : ''}`}>
              <CardHeader className="text-center pb-4">
                <CardTitle className="text-2xl font-bold">Free Plan</CardTitle>
                <div className="mt-2">
                  <span className="text-4xl font-black">£0</span>
                  <span className="text-gray-600 ml-2">/month</span>
                </div>
                <p className="text-gray-600 text-sm mt-2">3 checks per week</p>
              </CardHeader>
              
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="text-sm">3 fact-checks per week</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="text-sm">Basic verification</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="text-sm">Evidence sources</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="text-sm">Export results</span>
                  </div>
                </div>
                
                <div className="pt-4 border-t">
                  {user ? (
                    currentPlan === 'free' ? (
                      <Button variant="outline" className="w-full" disabled>
                        Current Plan
                      </Button>
                    ) : (
                      <Link href="/account">
                        <Button variant="outline" className="w-full">
                          Manage Subscription
                        </Button>
                      </Link>
                    )
                  ) : (
                    <Link href="/sign-up">
                      <Button className="btn-primary w-full">
                        Get Started Free
                      </Button>
                    </Link>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Paid Plans */}
        <div className="mb-12">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-4">Upgrade for More</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Get more checks and unlock advanced features with our premium plans.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <CheckoutModal plan="starter">
              <PricingCard
                plan="starter"
                isCurrentPlan={currentPlan === 'starter'}
                isPopular
                onUpgrade={handleUpgrade}
              />
            </CheckoutModal>
            
            <CheckoutModal plan="pro">
              <PricingCard
                plan="pro"
                isCurrentPlan={currentPlan === 'pro'}
                onUpgrade={handleUpgrade}
              />
            </CheckoutModal>
          </div>
        </div>

        {/* Features Comparison */}
        <div className="mb-12">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-4">Feature Comparison</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full border-collapse border border-gray-200 rounded-lg">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-200 p-4 text-left font-semibold">Feature</th>
                  <th className="border border-gray-200 p-4 text-center font-semibold">Free</th>
                  <th className="border border-gray-200 p-4 text-center font-semibold">Starter</th>
                  <th className="border border-gray-200 p-4 text-center font-semibold">Pro</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="border border-gray-200 p-4">Monthly checks</td>
                  <td className="border border-gray-200 p-4 text-center">12</td>
                  <td className="border border-gray-200 p-4 text-center">120</td>
                  <td className="border border-gray-200 p-4 text-center">300</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="border border-gray-200 p-4">Processing speed</td>
                  <td className="border border-gray-200 p-4 text-center">Standard</td>
                  <td className="border border-gray-200 p-4 text-center">Standard</td>
                  <td className="border border-gray-200 p-4 text-center">Priority</td>
                </tr>
                <tr>
                  <td className="border border-gray-200 p-4">Deep mode analysis</td>
                  <td className="border border-gray-200 p-4 text-center">❌</td>
                  <td className="border border-gray-200 p-4 text-center">❌</td>
                  <td className="border border-gray-200 p-4 text-center">✅</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="border border-gray-200 p-4">Export formats</td>
                  <td className="border border-gray-200 p-4 text-center">PDF</td>
                  <td className="border border-gray-200 p-4 text-center">PDF, JSON</td>
                  <td className="border border-gray-200 p-4 text-center">PDF, JSON, MD</td>
                </tr>
                <tr>
                  <td className="border border-gray-200 p-4">Support</td>
                  <td className="border border-gray-200 p-4 text-center">Community</td>
                  <td className="border border-gray-200 p-4 text-center">Email</td>
                  <td className="border border-gray-200 p-4 text-center">Priority</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Trust & Security */}
        <div className="bg-gray-50 rounded-2xl p-8 mb-12">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-4">Trust & Security</h2>
            <p className="text-gray-600">Your security and privacy are our top priorities.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <Shield className="h-12 w-12 text-tru8-primary mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Secure Payments</h3>
              <p className="text-gray-600">All payments processed securely through Stripe</p>
            </div>
            <div className="text-center">
              <Clock className="h-12 w-12 text-tru8-primary mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Cancel Anytime</h3>
              <p className="text-gray-600">No long-term commitments. Cancel with one click</p>
            </div>
            <div className="text-center">
              <HeadphonesIcon className="h-12 w-12 text-tru8-primary mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">24/7 Support</h3>
              <p className="text-gray-600">Get help when you need it</p>
            </div>
          </div>
        </div>

        {/* FAQ */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold mb-4">Frequently Asked Questions</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">How accurate is the fact-checking?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Our AI analyzes multiple sources and provides confidence scores. We prioritize recent, 
                credible sources and show you the evidence so you can make informed decisions.
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Can I cancel my subscription?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Yes, you can cancel anytime from your account settings. You'll retain access 
                to paid features until the end of your billing period.
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">What types of content can I check?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                You can fact-check URLs, text content, images with text, and short videos. 
                We support multiple languages and various content formats.
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Do unused credits roll over?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                No, credits reset at the beginning of each billing cycle. We recommend 
                choosing a plan that matches your monthly usage.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* CTA */}
        <div className="text-center mt-16 p-8 bg-gradient-to-br from-tru8-primary to-purple-600 rounded-2xl text-white">
          <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
          <p className="text-xl opacity-90 mb-6">
            Join thousands of users who trust Tru8 for accurate fact-checking.
          </p>
          {user ? (
            <Link href="/checks/new">
              <Button className="bg-white text-gray-900 hover:bg-gray-100" size="lg">
                Start Fact-Checking
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          ) : (
            <Link href="/sign-up">
              <Button className="bg-white text-gray-900 hover:bg-gray-100" size="lg">
                Sign Up Free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          )}
        </div>
      </div>
    </MainLayout>
  );
}