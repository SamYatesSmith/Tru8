'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton, useUser } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { CheckCircle, Home, Settings, User, CreditCard } from "lucide-react";
import { cn } from "@/lib/utils";

export function Navigation() {
  const pathname = usePathname();
  const { user, isSignedIn } = useUser();

  // Mock usage data - should come from API in production
  const mockUsage = {
    creditsRemaining: 47,
  };

  const navItems = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: Home,
    },
    {
      name: "New Check",
      href: "/checks/new",
      icon: CheckCircle,
    },
    {
      name: "Pricing",
      href: "/pricing",
      icon: CreditCard,
    },
    {
      name: "Account",
      href: "/account",
      icon: User,
    },
    {
      name: "Settings",
      href: "/settings",
      icon: Settings,
    },
  ];

  return (
    <>
      {/* Skip Link - PHASE 03: Accessibility */}
      <a
        href="#main-content"
        className="skip-link"
        aria-label="Skip to main content"
      >
        Skip to main content
      </a>

      {/* Two-Pill Navbar System */}
      <nav className="navbar-pill-system" role="navigation" aria-label="Main navigation">
        {/* Primary Pill - Always Visible */}
        <div className="navbar-primary-pill">
          <Link
            href="/"
            className="navbar-pill-brand navbar-brand-link"
            aria-label="Tru8 home"
          >
            <div className="navbar-pill-logo" aria-hidden="true">
              <span>T8</span>
            </div>
            <span>Tru8</span>
          </Link>
        </div>

        {/* Secondary Pill - Hover Reveal with Navigation */}
        {isSignedIn && (
          <div className="navbar-secondary-pill" role="region" aria-label="Application navigation">
            <ul role="list" className="navbar-secondary-nav">
              {navItems.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href);
                const Icon = item.icon;

                return (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={cn("navbar-secondary-item", isActive && "active")}
                      aria-current={isActive ? 'page' : undefined}
                      aria-label={`${item.name}${isActive ? ' (current page)' : ''}`}
                    >
                      <Icon size={16} aria-hidden="true" />
                      <span>{item.name}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </nav>

      {/* User Section - Top Right */}
      <div className="fixed top-4 right-4 z-50">
        <div className="flex items-center space-x-3" role="region" aria-label="User account">
          {isSignedIn ? (
            <>
              {/* Credits Display */}
              <div
                className="hidden sm:flex items-center space-x-2 text-sm bg-white px-3 py-2 rounded-full border shadow-sm"
                role="status"
                aria-label={`${mockUsage.creditsRemaining} credits remaining`}
              >
                <span className="text-gray-600" aria-hidden="true">Credits:</span>
                <span className="font-medium text-gray-900">{mockUsage.creditsRemaining}</span>
              </div>

              {/* User Button */}
              <UserButton
                appearance={{
                  elements: {
                    avatarBox: "h-8 w-8",
                  }
                }}
                afterSignOutUrl="/"
                // Clerk already handles accessibility for the UserButton
              />
            </>
          ) : (
            <div className="flex items-center space-x-2" role="group" aria-label="Account options">
              <Button variant="outline" asChild>
                <Link href="/sign-in" aria-label="Sign in to your account">
                  Sign In
                </Link>
              </Button>
              <Button className="btn-primary" asChild>
                <Link href="/sign-up" aria-label="Create new account">
                  Get Started
                </Link>
              </Button>
            </div>
          )}
        </div>
      </div>

    </>
  );
}