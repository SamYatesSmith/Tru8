import { loadStripe } from '@stripe/stripe-js';

// This is your publishable key from the Stripe Dashboard
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export { stripePromise };

export const PRICING_PLANS = {
  starter: {
    name: 'Starter Plan',
    price: 6.99,
    priceId: process.env.NODE_ENV === 'production' 
      ? 'price_starter_prod' 
      : 'price_starter_test',
    credits: 120,
    description: '120 checks per month',
    features: [
      '120 fact-checks per month',
      'Real-time verification',
      'Multiple evidence sources',
      'Export results',
      'Email support'
    ]
  },
  pro: {
    name: 'Pro Plan',
    price: 12.99,
    priceId: process.env.NODE_ENV === 'production'
      ? 'price_pro_prod'
      : 'price_pro_test',
    credits: 300,
    description: '300 checks per month + Deep mode',
    features: [
      '300 fact-checks per month',
      'Deep mode analysis',
      'Priority processing',
      'Advanced analytics',
      'API access (coming soon)',
      'Priority support'
    ]
  }
} as const;

export type PricingPlan = keyof typeof PRICING_PLANS;