import { describe, it, expect } from 'vitest';
import { TIERS, getTierPriceId, purchasableTiers, TierConfig } from '../tiers';

describe('TIERS configuration', () => {
  it('has exactly 5 tiers (2 retired)', () => {
    expect(TIERS).toHaveLength(5);
    expect(TIERS.filter((t) => t.retired)).toHaveLength(2);
  });

  it('tiers are in correct order', () => {
    expect(TIERS.map((t) => t.id)).toEqual([
      'free',
      'starter',
      'professional',
      'console',
      'enterprise',
    ]);
  });

  it('free tier has correct config', () => {
    const free = TIERS.find((t) => t.id === 'free')!;
    expect(free.name).toBe('Free Trial');
    expect(free.price).toBe(0);
    expect(free.credits).toBe(3);
    expect(free.highlighted).toBe(false);
    expect(free.priceEnvVar).toBeUndefined();
  });

  it('starter and professional are retired from sale', () => {
    const starter = TIERS.find((t) => t.id === 'starter')!;
    const pro = TIERS.find((t) => t.id === 'professional')!;
    expect(starter.retired).toBe(true);
    expect(pro.retired).toBe(true);
    // kept renderable for existing subscribers
    expect(starter.price).toBe(7);
    expect(pro.price).toBe(29);
  });

  it('console tier is £20/mo (£200/yr) with 200 credits and highlighted', () => {
    const console_ = TIERS.find((t) => t.id === 'console')!;
    expect(console_.price).toBe(20);
    expect(console_.period).toBe('month');
    expect(console_.credits).toBe(200);
    expect(console_.annualPrice).toBe(200);
    expect(console_.highlighted).toBe(true);
    expect(console_.retired).toBeUndefined();
    expect(console_.priceEnvVar).toBe('NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE');
    expect(console_.annualPriceEnvVar).toBe(
      'NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE_ANNUAL'
    );
  });

  it('enterprise (Teams) tier has no price and a contact URL', () => {
    const ent = TIERS.find((t) => t.id === 'enterprise')!;
    expect(ent.name).toBe('Teams');
    expect(ent.price).toBeNull();
    expect(ent.credits).toBeNull();
    expect(ent.contactUrl).toBe('/contact');
  });

  it('every tier has required fields', () => {
    for (const tier of TIERS) {
      expect(tier.id).toBeTruthy();
      expect(tier.name).toBeTruthy();
      expect(tier.description).toBeTruthy();
      expect(tier.cta).toBeTruthy();
      expect(tier.features.length).toBeGreaterThan(0);
    }
  });

  it('exactly one tier is highlighted, and it is console', () => {
    const highlighted = TIERS.filter((t) => t.highlighted);
    expect(highlighted).toHaveLength(1);
    expect(highlighted[0].id).toBe('console');
  });
});

describe('purchasableTiers', () => {
  it('excludes retired tiers for free users', () => {
    expect(purchasableTiers('free').map((t) => t.id)).toEqual([
      'free',
      'console',
      'enterprise',
    ]);
  });

  it('keeps a retired tier visible for its existing subscriber', () => {
    expect(purchasableTiers('starter').map((t) => t.id)).toEqual([
      'free',
      'starter',
      'console',
      'enterprise',
    ]);
    expect(purchasableTiers('professional').map((t) => t.id)).toEqual([
      'free',
      'professional',
      'console',
      'enterprise',
    ]);
  });

  it('never offers the other retired tier', () => {
    expect(purchasableTiers('starter').map((t) => t.id)).not.toContain(
      'professional'
    );
  });
});

describe('getTierPriceId', () => {
  it('returns null for free tier (no priceEnvVar)', () => {
    const free = TIERS.find((t) => t.id === 'free')!;
    expect(getTierPriceId(free)).toBeNull();
  });

  it('returns null for enterprise tier (no priceEnvVar)', () => {
    const ent = TIERS.find((t) => t.id === 'enterprise')!;
    expect(getTierPriceId(ent)).toBeNull();
  });

  it('returns null when env var is not set', () => {
    // In test env, no NEXT_PUBLIC_STRIPE_PRICE_ID_* is set
    const console_ = TIERS.find((t) => t.id === 'console')!;
    expect(getTierPriceId(console_)).toBeNull();
    expect(getTierPriceId(console_, 'year')).toBeNull();
  });

  it('year interval resolves via annualPriceEnvVar only', () => {
    const starter = TIERS.find((t) => t.id === 'starter')!;
    // starter has no annual price — year must not fall back to monthly
    expect(getTierPriceId(starter, 'year')).toBeNull();
  });

  it('returns null for tier with no priceEnvVar property', () => {
    const tier: TierConfig = {
      id: 'test',
      name: 'Test',
      price: 0,
      period: null,
      credits: null,
      description: 'Test',
      features: [],
      cta: 'Test',
      highlighted: false,
    };
    expect(getTierPriceId(tier)).toBeNull();
  });
});
