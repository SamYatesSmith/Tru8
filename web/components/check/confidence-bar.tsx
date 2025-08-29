"use client";

import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

interface ConfidenceBarProps {
  confidence: number; // 0-100
  verdict?: 'supported' | 'contradicted' | 'uncertain';
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  className?: string;
}

export function ConfidenceBar({ 
  confidence, 
  verdict,
  showLabel = true,
  size = 'md',
  animated = true,
  className 
}: ConfidenceBarProps) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    // Animate on mount
    if (animated) {
      const timer = setTimeout(() => {
        setWidth(confidence);
      }, 100);
      return () => clearTimeout(timer);
    } else {
      setWidth(confidence);
    }
  }, [confidence, animated]);

  const sizeClasses = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3"
  };

  const labelClasses = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base"
  };

  // Use verdict-specific gradient if provided, otherwise use primary gradient
  const getGradientClass = () => {
    if (!verdict) return "bg-gradient-to-r from-tru8-primary to-purple-600";
    
    switch (verdict) {
      case 'supported':
        return "bg-gradient-to-r from-green-500 to-emerald-600";
      case 'contradicted':
        return "bg-gradient-to-r from-red-500 to-red-600";
      case 'uncertain':
        return "bg-gradient-to-r from-amber-500 to-orange-600";
      default:
        return "bg-gradient-to-r from-tru8-primary to-purple-600";
    }
  };

  return (
    <div className={cn("space-y-1", className)}>
      <div 
        className={cn(
          "w-full bg-gray-200 rounded-full overflow-hidden",
          sizeClasses[size]
        )}
        role="progressbar"
        aria-valuenow={confidence}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Confidence: ${confidence}%`}
      >
        <div 
          className={cn(
            "h-full rounded-full transition-all duration-1000 ease-out",
            getGradientClass()
          )}
          style={{ width: `${width}%` }}
        />
      </div>
      
      {showLabel && (
        <div className={cn(
          "flex justify-between items-center text-gray-600",
          labelClasses[size]
        )}>
          <span className="font-medium">Confidence</span>
          <span className="font-semibold">{Math.round(confidence)}%</span>
        </div>
      )}
    </div>
  );
}