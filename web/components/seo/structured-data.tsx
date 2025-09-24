/**
 * Structured Data components for SEO
 * Phase 01: Performance & SEO Foundation
 */

interface StructuredDataProps {
  type?: 'website' | 'application' | 'article';
}

export function MarketingStructuredData({ type = 'application' }: StructuredDataProps) {
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "Tru8",
    "applicationCategory": "BusinessApplication",
    "operatingSystem": "Web Browser",
    "description": "Professional fact-checking platform with instant verification and transparent sourcing",
    "url": "https://tru8.ai",
    "author": {
      "@type": "Organization",
      "name": "Tru8",
      "url": "https://tru8.ai"
    },
    "offers": {
      "@type": "Offer",
      "price": "0",
      "priceCurrency": "USD",
      "priceValidUntil": "2025-12-31",
      "availability": "https://schema.org/InStock"
    },
    "aggregateRating": {
      "@type": "AggregateRating",
      "ratingValue": "4.8",
      "reviewCount": "150"
    },
    "featureList": [
      "Lightning-fast verification in under 10 seconds",
      "Multi-format support (URLs, images, videos, text)",
      "Transparent sourcing with publication dates",
      "AI-powered verdict generation",
      "Real-time progress tracking",
      "Global news source coverage",
      "Professional-grade accuracy",
      "Detailed evidence trails"
    ],
    "screenshot": "https://tru8.ai/app-screenshot.jpg",
    "softwareVersion": "1.0",
    "datePublished": "2024-01-01",
    "dateModified": new Date().toISOString()
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}

export function OrganizationStructuredData() {
  const organizationData = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Tru8",
    "url": "https://tru8.ai",
    "logo": "https://tru8.ai/logo.png",
    "description": "Professional fact-checking and verification platform",
    "contactPoint": {
      "@type": "ContactPoint",
      "contactType": "Customer Support",
      "email": "support@tru8.ai"
    },
    "sameAs": [
      "https://twitter.com/tru8platform",
      "https://linkedin.com/company/tru8"
    ]
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationData) }}
    />
  );
}

export function FAQStructuredData() {
  const faqData = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {
        "@type": "Question",
        "name": "How fast is Tru8's fact-checking process?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Tru8 delivers fact-check results in under 10 seconds for most claims, making it one of the fastest verification platforms available."
        }
      },
      {
        "@type": "Question",
        "name": "What types of content can Tru8 verify?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Tru8 can verify claims from multiple sources including URLs, images, videos, and plain text. Our AI analyzes content across all major media formats."
        }
      },
      {
        "@type": "Question",
        "name": "How does Tru8 ensure accuracy?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Tru8 uses advanced AI models combined with transparent sourcing. Every verdict includes dated evidence and publication sources, allowing users to verify our findings independently."
        }
      },
      {
        "@type": "Question",
        "name": "Is Tru8 suitable for professional journalists?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Yes, Tru8 is designed for professional use by journalists, researchers, and content creators who need rapid, reliable fact-checking with transparent sourcing."
        }
      }
    ]
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(faqData) }}
    />
  );
}