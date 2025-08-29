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
    <nav className="border-b border-gray-200 bg-white">
      <div className="container">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <div 
              className="flex h-8 w-8 items-center justify-center rounded-lg"
              style={{ background: 'var(--gradient-primary)' }}
            >
              <span className="text-sm font-bold text-white">T8</span>
            </div>
            <span className="text-xl font-bold text-gray-900">Tru8</span>
          </Link>

          {/* Navigation Items - Only show if signed in */}
          {isSignedIn && (
            <div className="hidden md:flex items-center space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href || pathname.startsWith(item.href);
                
                return (
                  <Link key={item.name} href={item.href}>
                    <Button
                      variant="ghost"
                      className={cn(
                        "flex items-center space-x-2 px-3 py-2",
                        isActive && "bg-gray-100 font-medium"
                      )}
                      style={isActive ? { color: 'var(--tru8-primary)' } : undefined}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{item.name}</span>
                    </Button>
                  </Link>
                );
              })}
            </div>
          )}

          {/* User Section */}
          <div className="flex items-center space-x-4">
            {isSignedIn ? (
              <div className="flex items-center space-x-3">
                {/* Credits Display */}
                <div className="hidden sm:flex items-center space-x-2 text-sm">
                  <span className="text-gray-600">Credits:</span>
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
                />
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Button variant="outline" asChild>
                  <Link href="/sign-in">Sign In</Link>
                </Button>
                <Button className="btn-primary" asChild>
                  <Link href="/sign-up">Get Started</Link>
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Navigation */}
        {isSignedIn && (
          <div className="md:hidden border-t border-gray-200 px-4 py-2">
            <div className="flex items-center justify-around">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href || pathname.startsWith(item.href);
                
                return (
                  <Link key={item.name} href={item.href}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className={cn(
                        "flex flex-col items-center space-y-1 px-2 py-2",
                        isActive && "font-medium"
                      )}
                      style={isActive ? { color: 'var(--tru8-primary)' } : undefined}
                    >
                      <Icon className="h-4 w-4" />
                      <span className="text-xs">{item.name}</span>
                    </Button>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}