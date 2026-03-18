import { describe, it, expect } from 'vitest';
import { TIERS, getTierPriceId, TierConfig } from '../tiers';

describe('TIERS configuration', () => {
  it('has exactly 4 tiers', () => {
    expect(TIERS).toHaveLength(4);
  });

  it('tiers are in correct order', () => {
    expect(TIERS.map((t) => t.id)).toEqual(['free', 'starter', 'professional', 'enterprise']);
  });

  it('free tier has correct config', () => {
    const free = TIERS.find((t) => t.id === 'free')!;
    expect(free.name).toBe('Free Trial');
    expect(free.price).toBe(0);
    expect(free.credits).toBe(3);
    expect(free.highlighted).toBe(false);
    expect(free.priceEnvVar).toBeUndefined();
  });

  it('starter tier is £7/mo with 40 credits', () => {
    const starter = TIERS.find((t) => t.id === 'starter')!;
    expect(starter.price).toBe(7);
    expect(starter.period).toBe('month');
    expect(starter.credits).toBe(40);
    expect(starter.priceEnvVar).toBe('NEXT_PUBLIC_STRIPE_PRICE_ID_PRO');
  });

  it('professional tier is £29/mo with 200 credits and highlighted', () => {
    const pro = TIERS.find((t) => t.id === 'professional')!;
    expect(pro.price).toBe(29);
    expect(pro.period).toBe('month');
    expect(pro.credits).toBe(200);
    expect(pro.highlighted).toBe(true);
    expect(pro.priceEnvVar).toBe('NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER');
  });

  it('enterprise tier has no price and a contact URL', () => {
    const ent = TIERS.find((t) => t.id === 'enterprise')!;
    expect(ent.price).toBeNull();
    expect(ent.credits).toBeNull();
    expect(ent.contactUrl).toContain('mailto:');
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

  it('exactly one tier is highlighted', () => {
    const highlighted = TIERS.filter((t) => t.highlighted);
    expect(highlighted).toHaveLength(1);
    expect(highlighted[0].id).toBe('professional');
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
    const starter = TIERS.find((t) => t.id === 'starter')!;
    // In test env, NEXT_PUBLIC_STRIPE_PRICE_ID_PRO is not set
    expect(getTierPriceId(starter)).toBeNull();
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
