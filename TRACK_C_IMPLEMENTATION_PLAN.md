# Track C: Mobile App - Detailed Implementation Plan

## 📱 **Current Status Analysis**

### **Existing Implementation**
- ✅ Basic Expo setup with React Native 0.76.3
- ✅ NativeWind (Tailwind) configured
- ✅ Clerk authentication package installed
- ✅ React Query installed
- ✅ RevenueCat (react-native-purchases) installed
- ✅ Basic navigation structure (Expo Router)
- ✅ CreateCheckForm component (partial)
- ✅ Basic API client with multipart upload support

### **Critical Gaps Identified**
1. **Navigation**: No proper tab navigation or stack structure
2. **Auth Flow**: Sign-in screen exists but not integrated with navigation
3. **API Integration**: Endpoints don't match backend exactly (case conversion missing)
4. **Design System**: Not ported from web (missing CSS variables → React Native styles)
5. **Progress Monitoring**: No SSE/EventSource implementation
6. **Results Display**: No claim cards, verdict pills, or evidence components
7. **Push Notifications**: Package installed but not configured
8. **IAP**: RevenueCat installed but not integrated

---

## 🎯 **Week 1: Core Setup - PRIORITY TASKS**

### **1.1 Fix Navigation Structure**
```typescript
// app/(app)/_layout.tsx - Protected app routes
// app/(auth)/_layout.tsx - Auth routes
// app/(tabs)/_layout.tsx - Main tab navigation
```

**Required Files:**
- `app/_layout.tsx` - Root layout with Clerk provider
- `app/(app)/_layout.tsx` - Protected route wrapper
- `app/(tabs)/_layout.tsx` - Tab navigator
- `app/(tabs)/home.tsx` - Home/New Check
- `app/(tabs)/history.tsx` - Check history
- `app/(tabs)/account.tsx` - Account/settings

### **1.2 Port Design System**
Create `lib/design-system.ts`:
```typescript
export const Colors = {
  // From DESIGN_SYSTEM.md
  primary: '#1E40AF',
  verdictSupported: '#059669',
  verdictContradicted: '#DC2626',
  verdictUncertain: '#D97706',
  // ... complete color system
};

export const Spacing = {
  space1: 4,
  space2: 8,
  space3: 12,
  space4: 16,
  // ... 4pt grid system
};
```

### **1.3 Fix Clerk Integration**
```typescript
// app/_layout.tsx
import { ClerkProvider, useAuth } from '@clerk/clerk-expo';
import * as SecureStore from 'expo-secure-store';

const tokenCache = {
  async getToken(key: string) {
    return await SecureStore.getItemAsync(key);
  },
  async saveToken(key: string, value: string) {
    await SecureStore.setItemAsync(key, value);
  },
};
```

### **1.4 Update API Client**
Fix case conversion and match backend exactly:
```typescript
// lib/api.ts - Add case conversion
function convertKeysToCamelCase(obj: any): any { /* ... */ }
function convertKeysToSnakeCase(obj: any): any { /* ... */ }

// Match backend endpoints exactly
export async function createCheck(data: CreateCheckRequest, token: string) {
  // POST /api/v1/checks with proper snake_case conversion
}
```

---

## 🎯 **Week 2: Check Creation - COMPLETE FLOW**

### **2.1 Camera Integration**
```typescript
// components/CameraCapture.tsx
import * as ImagePicker from 'expo-image-picker';
import { Camera } from 'expo-camera';

// Handle permissions properly
// Implement camera UI with capture button
// Process and validate image before upload
```

### **2.2 Share Extension for URLs**
```typescript
// app.json configuration
{
  "expo": {
    "plugins": [
      "expo-sharing",
      ["expo-intent-launcher", {
        "intentFilters": [
          {
            "action": "SEND",
            "data": [{ "mimeType": "text/plain" }],
            "category": ["DEFAULT"]
          }
        ]
      }]
    ]
  }
}
```

### **2.3 File Upload with Progress**
```typescript
// lib/upload.ts
export async function uploadFileWithProgress(
  file: File,
  onProgress: (progress: number) => void
) {
  // Use XMLHttpRequest for progress tracking
  // Handle multipart/form-data properly
  // Match backend's /api/v1/checks/upload endpoint
}
```

### **2.4 Progress Monitoring (SSE Alternative)**
Since React Native doesn't support EventSource natively:
```typescript
// hooks/use-check-progress.ts
import { useEffect, useState } from 'react';

export function useCheckProgress(checkId: string) {
  // Poll /api/v1/checks/{checkId} every 2 seconds
  // Or use WebSocket connection if backend supports it
  // Update progress state based on response
}
```

---

## 🎯 **Week 3: Results & History**

### **3.1 Port Result Components from Web**
**Required Components:**
- `components/check/ClaimCard.tsx` - Display individual claims
- `components/check/VerdictPill.tsx` - Verdict indicators
- `components/check/ConfidenceBar.tsx` - Confidence visualization
- `components/check/CitationChip.tsx` - Source citations
- `components/check/EvidenceDrawer.tsx` - Evidence details

### **3.2 Results Screen**
```typescript
// app/check/[id].tsx
import { useCheck } from '@/hooks/use-check';
import { ClaimCard } from '@/components/check/ClaimCard';

export default function CheckResultsScreen({ id }) {
  const { data: check, isLoading } = useCheck(id);
  
  // Display claims with verdicts
  // Show evidence for each claim
  // Handle loading and error states
}
```

### **3.3 History List**
```typescript
// app/(tabs)/history.tsx
import { useInfiniteQuery } from '@tanstack/react-query';
import { FlatList } from 'react-native';

export default function HistoryScreen() {
  const { data, fetchNextPage, hasNextPage } = useInfiniteQuery({
    queryKey: ['checks'],
    queryFn: ({ pageParam = 0 }) => getChecks(token, pageParam, 20),
    getNextPageParam: (lastPage, pages) => /* ... */
  });
  
  // Infinite scroll with FlatList
  // Show check summaries
  // Navigate to details on tap
}
```

### **3.4 Push Notifications**
```typescript
// services/notifications.ts
import * as Notifications from 'expo-notifications';

export async function registerForPushNotifications() {
  // Request permissions
  // Get Expo push token
  // Send to backend
}

// Handle check completion notifications
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});
```

### **3.5 Share Results**
```typescript
// components/ShareSheet.tsx
import * as Sharing from 'expo-sharing';

export async function shareCheckResults(check: Check) {
  // Generate shareable text/image
  // Use native share sheet
  // Track sharing analytics
}
```

---

## 🎯 **Week 4: IAP & Polish**

### **4.1 RevenueCat Integration**
```typescript
// services/purchases.ts
import Purchases from 'react-native-purchases';

export async function initializePurchases(userId: string) {
  await Purchases.configure({
    apiKey: process.env.EXPO_PUBLIC_REVENUECAT_KEY,
    appUserID: userId,
  });
}

export async function purchaseSubscription(productId: string) {
  const { customerInfo } = await Purchases.purchaseProduct(productId);
  // Sync with backend
  return customerInfo.entitlements.active;
}
```

### **4.2 Subscription UI**
```typescript
// app/(tabs)/account.tsx
import { useRevenueCat } from '@/hooks/use-revenuecat';

export default function AccountScreen() {
  const { offerings, currentPlan, purchase } = useRevenueCat();
  
  // Display current plan
  // Show upgrade options
  // Handle purchase flow
  // Display usage/credits
}
```

### **4.3 Settings Screen**
```typescript
// components/account/SettingsSection.tsx
- Notification preferences
- Privacy settings
- Cache management
- Sign out
```

### **4.4 Offline Handling**
```typescript
// hooks/use-offline.ts
import NetInfo from '@react-native-community/netinfo';

export function useOfflineSync() {
  // Queue actions when offline
  // Sync when connection restored
  // Show offline indicator
}
```

---

## 🔌 **API Integration Checklist**

### **Endpoints to Implement**
- [x] `POST /api/v1/checks` - Create check (needs case conversion fix)
- [ ] `POST /api/v1/checks/upload` - Upload image
- [x] `GET /api/v1/checks` - List checks
- [x] `GET /api/v1/checks/{id}` - Get check details
- [ ] `GET /api/v1/checks/{id}/progress` - SSE alternative needed
- [ ] `GET /api/v1/users/profile` - User profile
- [ ] `GET /api/v1/users/usage` - Usage stats
- [ ] `POST /api/v1/payments/mobile-webhook` - RevenueCat webhook

### **Critical Integration Points**
1. **Case Conversion**: Backend uses snake_case, mobile uses camelCase
2. **File Upload**: Must use multipart/form-data with proper headers
3. **Authentication**: Clerk token in Authorization header
4. **Error Handling**: Transform backend errors to user-friendly messages
5. **Progress Updates**: Poll or WebSocket since no EventSource

---

## 🎨 **Component Reuse from Web**

### **Direct Ports (with React Native adjustments)**
- VerdictPill → View with Text instead of div/span
- ConfidenceBar → View with Animated.View
- CitationChip → TouchableOpacity for links
- ClaimCard → View with proper spacing

### **Native-Specific Components**
- CameraCapture (using expo-camera)
- ShareSheet (using expo-sharing)
- PushNotificationHandler (expo-notifications)
- IAPManager (react-native-purchases)

---

## 📋 **Implementation Priority Order**

### **Day 1-2: Foundation**
1. Fix navigation structure
2. Complete Clerk integration
3. Port design system
4. Fix API client case conversion

### **Day 3-4: Check Creation**
5. Camera integration
6. File upload with backend endpoint
7. Progress monitoring solution
8. Form validation and error handling

### **Day 5-6: Results**
9. Port result components
10. Implement results screen
11. Build history list with pagination
12. Add share functionality

### **Day 7-8: Monetization**
13. RevenueCat setup
14. Subscription UI
15. Usage tracking
16. Settings screen

### **Day 9-10: Polish**
17. Push notifications
18. Offline handling
19. Performance optimization
20. Testing and bug fixes

---

## ⚠️ **Risk Mitigations**

### **Technical Risks**
- **SSE not supported**: Use polling or WebSocket
- **Large file uploads**: Implement chunking if needed
- **Camera permissions**: Graceful degradation
- **IAP complexity**: Start with simple tier structure

### **Integration Risks**
- **API mismatches**: Validate all endpoints early
- **Auth sync**: Test Clerk across platforms
- **Payment sync**: RevenueCat → Backend webhook critical

---

## 🚀 **Success Criteria**

### **Week 1 Complete When:**
- [ ] User can sign in with Clerk
- [ ] Tab navigation works
- [ ] Design system matches web
- [ ] API calls succeed with auth

### **Week 2 Complete When:**
- [ ] Can capture/upload images
- [ ] URL sharing works
- [ ] Progress updates display
- [ ] Checks created successfully

### **Week 3 Complete When:**
- [ ] Results display with verdicts
- [ ] History list with pagination
- [ ] Push notifications work
- [ ] Can share results

### **Week 4 Complete When:**
- [ ] IAP subscriptions work
- [ ] Settings fully functional
- [ ] Offline handling smooth
- [ ] App store ready

---

## 📱 **Testing Strategy**

### **Device Testing**
- iOS: iPhone 12+ (iOS 15+)
- Android: Pixel 5+ (Android 12+)
- Tablets: iPad, Samsung Tab

### **Key Test Scenarios**
1. Complete check flow (create → progress → results)
2. Purchase subscription flow
3. Offline → online sync
4. Push notification delivery
5. Camera permissions handling
6. Large file upload (6MB limit)

---

*This plan provides the detailed implementation roadmap for Track C with all dependencies, integration points, and technical requirements clearly defined.*