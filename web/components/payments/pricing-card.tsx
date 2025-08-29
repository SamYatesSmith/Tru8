'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Check, Zap } from 'lucide-react';
import { PRICING_PLANS, PricingPlan } from '@/lib/stripe';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

interface PricingCardProps {
  plan: PricingPlan;
  isCurrentPlan?: boolean;
  isPopular?: boolean;
  onUpgrade?: (plan: PricingPlan) => void;
}

export function PricingCard({ plan, isCurrentPlan, isPopular, onUpgrade }: PricingCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const { getToken } = useAuth();
  const router = useRouter();
  const planData = PRICING_PLANS[plan];

  const handleUpgrade = async () => {
    if (isCurrentPlan || !onUpgrade) return;
    
    setIsLoading(true);
    try {
      await onUpgrade(plan);
    } catch (error) {
      console.error('Upgrade failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className={`relative ${isPopular ? 'card-featured border-2' : ''} ${isCurrentPlan ? 'opacity-75' : ''}`}>
      {isPopular && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <Badge className="verdict-supported px-3 py-1">
            <Zap className="h-3 w-3 mr-1" />
            Popular
          </Badge>
        </div>
      )}
      
      <CardHeader className="text-center pb-4">
        <CardTitle className="text-2xl font-bold">{planData.name}</CardTitle>
        <div className="mt-2">
          <span className="text-4xl font-black">£{planData.price}</span>
          <span className="text-gray-600 ml-2">/month</span>
        </div>
        <p className="text-gray-600 text-sm mt-2">{planData.description}</p>
      </CardHeader>
      
      <CardContent className="space-y-6">
        <div className="space-y-3">
          {planData.features.map((feature, index) => (
            <div key={index} className="flex items-center gap-3">
              <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
              <span className="text-sm text-gray-700">{feature}</span>
            </div>
          ))}
        </div>
        
        <div className="pt-4 border-t">
          <Button
            className={`w-full ${isPopular ? 'btn-primary' : ''}`}
            variant={isPopular ? 'default' : 'outline'}
            onClick={handleUpgrade}
            disabled={isCurrentPlan || isLoading}
          >
            {isLoading ? (
              'Processing...'
            ) : isCurrentPlan ? (
              'Current Plan'
            ) : (
              `Upgrade to ${planData.name}`
            )}
          </Button>
          
          {isCurrentPlan && (
            <p className="text-xs text-center text-gray-500 mt-2">
              Your current subscription
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}