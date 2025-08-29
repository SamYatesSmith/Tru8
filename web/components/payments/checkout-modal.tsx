'use client';

import { useState, ReactNode } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, CreditCard, Shield, Check } from 'lucide-react';
import { PRICING_PLANS, PricingPlan, stripePromise } from '@/lib/stripe';
import { useAuth } from '@clerk/nextjs';

// Create checkout session function
async function createCheckoutSession(priceId: string, plan: string, token: string) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/payments/create-checkout-session`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      price_id: priceId, // Use snake_case for backend
      plan: plan,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

interface CheckoutModalProps {
  children: ReactNode;
  plan: PricingPlan;
}

export function CheckoutModal({ children, plan }: CheckoutModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { getToken } = useAuth();
  const planData = PRICING_PLANS[plan];

  const handleCheckout = async () => {
    setIsLoading(true);
    
    try {
      const token = await getToken();
      
      // Call backend to create Stripe Checkout session
      const { session_id, url } = await createCheckoutSession(
        planData.priceId,
        plan,
        token!
      );

      if (url) {
        // For hosted Stripe Checkout, redirect directly
        window.location.href = url;
      } else if (session_id) {
        // For embedded Stripe Checkout
        const stripe = await stripePromise;
        if (stripe) {
          const { error } = await stripe.redirectToCheckout({ sessionId: session_id });
          if (error) {
            console.error('Stripe checkout error:', error);
          }
        }
      }
    } catch (error) {
      console.error('Checkout failed:', error);
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center text-2xl font-bold">
            Upgrade to {planData.name}
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* Plan Summary */}
          <Card className="card-featured">
            <CardHeader className="text-center pb-4">
              <div className="flex items-center justify-center gap-2 mb-2">
                <CardTitle className="text-xl">{planData.name}</CardTitle>
                <Badge className="verdict-supported">Upgrade</Badge>
              </div>
              <div>
                <span className="text-3xl font-black">£{planData.price}</span>
                <span className="text-gray-600 ml-2">/month</span>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-3">
              {planData.features.slice(0, 3).map((feature, index) => (
                <div key={index} className="flex items-center gap-3">
                  <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                  <span className="text-sm">{feature}</span>
                </div>
              ))}
              {planData.features.length > 3 && (
                <p className="text-xs text-gray-500">
                  +{planData.features.length - 3} more features
                </p>
              )}
            </CardContent>
          </Card>

          {/* Security & Payment Info */}
          <div className="space-y-3">
            <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
              <Shield className="h-4 w-4" />
              <span>Secured by Stripe</span>
            </div>
            
            <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
              <CreditCard className="h-4 w-4" />
              <span>Cancel anytime</span>
            </div>
          </div>

          {/* Checkout Button */}
          <Button
            onClick={handleCheckout}
            disabled={isLoading}
            className="btn-primary w-full"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <CreditCard className="h-4 w-4 mr-2" />
                Continue to Payment
              </>
            )}
          </Button>
          
          <p className="text-xs text-center text-gray-500">
            You'll be redirected to Stripe to complete your payment securely.
            No payment information is stored on our servers.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}