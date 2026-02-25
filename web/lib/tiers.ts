export interface TierConfig {
  id: string;
  name: string;
  price: number | null;
  period: string | null;
  credits: number | null;
  description: string;
  features: string[];
  cta: string;
  highlighted: boolean;
  priceEnvVar?: string;
  contactUrl?: string;
}

export const TIERS: TierConfig[] = [
  {
    id: "free",
    name: "Free Trial",
    price: 0,
    period: "lifetime",
    credits: 3,
    description: "Try Tru8 with 3 free checks",
    features: ["3 evidence checks", "All source types", "All six views"],
    cta: "Get Started",
    highlighted: false,
  },
  {
    id: "pro",
    name: "Professional",
    price: 7,
    period: "month",
    credits: 40,
    description: "For regular research",
    features: ["40 checks per month", "All source types", "Priority processing", "Export reports"],
    cta: "Upgrade",
    highlighted: false,
    priceEnvVar: "NEXT_PUBLIC_STRIPE_PRICE_ID_PRO",
  },
  {
    id: "developer",
    name: "Developer",
    price: 29,
    period: "month",
    credits: 200,
    description: "For AI agents and API integrations",
    features: ["200 checks per month", "Full API & MCP access", "Priority processing", "Export reports"],
    cta: "Upgrade",
    highlighted: true,
    priceEnvVar: "NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: null,
    period: null,
    credits: null,
    description: "Custom volume, SLA, and support",
    features: ["Custom check volume", "Dedicated support", "SLA guarantee", "Custom integrations"],
    cta: "Contact Us",
    highlighted: false,
    contactUrl: "mailto:hello@trueight.com",
  },
];

/** Map of env var names to their runtime values */
const PRICE_ENV_MAP: Record<string, string | undefined> = {
  NEXT_PUBLIC_STRIPE_PRICE_ID_PRO: process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_PRO,
  NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER: process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER,
};

/** Resolve a tier's Stripe price ID from its env var */
export function getTierPriceId(tier: TierConfig): string | null {
  if (!tier.priceEnvVar) return null;
  return PRICE_ENV_MAP[tier.priceEnvVar] || null;
}
