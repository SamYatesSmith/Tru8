import Purchases, { PurchasesOffering, PurchasesPackage, CustomerInfo } from 'react-native-purchases';

// Product configuration matching backend pricing
export const MOBILE_PRODUCTS = {
  free: {
    identifier: 'free_plan',
    name: 'Free',
    price: '£0',
    credits: 3,
    description: '3 free fact-checks',
    features: [
      '3 fact-checks',
      'Real-time verification',
      'Source citations',
      'Standard support'
    ]
  },
  professional: {
    identifier: 'professional_plan',
    name: 'Professional',
    price: '£7',
    credits: 40,
    description: '40 checks per month',
    features: [
      '40 fact-checks per month',
      'URL verification',
      'Export to PDF/JSON/CSV',
      'Comprehensive sources (10+ citations)',
      'Priority support'
    ]
  }
} as const;

export type MobilePlan = keyof typeof MOBILE_PRODUCTS;

export class RevenueCatService {
  private static instance: RevenueCatService;
  private isInitialized = false;

  public static getInstance(): RevenueCatService {
    if (!RevenueCatService.instance) {
      RevenueCatService.instance = new RevenueCatService();
    }
    return RevenueCatService.instance;
  }

  public async initialize(userId?: string): Promise<void> {
    if (this.isInitialized) return;

    try {
      const apiKey = process.env.EXPO_PUBLIC_REVENUECAT_API_KEY;
      if (!apiKey) {
        console.warn('RevenueCat API key not configured');
        return;
      }

      // Initialize RevenueCat
      await Purchases.configure({ apiKey });
      
      // Set user ID if provided (from Clerk auth)
      if (userId) {
        await Purchases.logIn(userId);
      }

      this.isInitialized = true;
      console.log('RevenueCat initialized successfully');
    } catch (error) {
      console.error('Failed to initialize RevenueCat:', error);
      throw error;
    }
  }

  public async getOfferings(): Promise<PurchasesOffering | null> {
    try {
      if (!this.isInitialized) {
        await this.initialize();
      }

      const offerings = await Purchases.getOfferings();
      return offerings.current;
    } catch (error) {
      console.error('Failed to get offerings:', error);
      return null;
    }
  }

  public async purchasePackage(pkg: PurchasesPackage): Promise<CustomerInfo> {
    try {
      if (!this.isInitialized) {
        throw new Error('RevenueCat not initialized');
      }

      const { customerInfo } = await Purchases.purchasePackage(pkg);
      return customerInfo;
    } catch (error) {
      console.error('Purchase failed:', error);
      throw error;
    }
  }

  public async getCustomerInfo(): Promise<CustomerInfo> {
    try {
      if (!this.isInitialized) {
        await this.initialize();
      }

      return await Purchases.getCustomerInfo();
    } catch (error) {
      console.error('Failed to get customer info:', error);
      throw error;
    }
  }

  public async restorePurchases(): Promise<CustomerInfo> {
    try {
      if (!this.isInitialized) {
        throw new Error('RevenueCat not initialized');
      }

      return await Purchases.restorePurchases();
    } catch (error) {
      console.error('Failed to restore purchases:', error);
      throw error;
    }
  }

  public async logOut(): Promise<CustomerInfo> {
    try {
      if (!this.isInitialized) {
        throw new Error('RevenueCat not initialized');
      }

      return await Purchases.logOut();
    } catch (error) {
      console.error('Failed to log out:', error);
      throw error;
    }
  }

  // Helper methods
  public getActiveSubscription(customerInfo: CustomerInfo): string | null {
    const activeSubscriptions = Object.keys(customerInfo.entitlements.active);
    return activeSubscriptions.length > 0 ? activeSubscriptions[0] : null;
  }

  public isSubscriptionActive(customerInfo: CustomerInfo, entitlementId: string): boolean {
    return customerInfo.entitlements.active[entitlementId]?.isActive ?? false;
  }

  public getSubscriptionExpirationDate(customerInfo: CustomerInfo, entitlementId: string): Date | null {
    const entitlement = customerInfo.entitlements.active[entitlementId];
    return entitlement?.expirationDate ? new Date(entitlement.expirationDate) : null;
  }
}

export default RevenueCatService.getInstance();