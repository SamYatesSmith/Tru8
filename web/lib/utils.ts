import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(date))
}

export function formatRelativeTime(date: string | Date) {
  const now = new Date()
  const target = new Date(date)
  const diffInMs = now.getTime() - target.getTime()
  const diffInMinutes = Math.floor(diffInMs / (1000 * 60))
  const diffInHours = Math.floor(diffInMinutes / 60)
  const diffInDays = Math.floor(diffInHours / 24)

  if (diffInMinutes < 1) return "Just now"
  if (diffInMinutes < 60) return `${diffInMinutes}m ago`
  if (diffInHours < 24) return `${diffInHours}h ago`
  if (diffInDays < 7) return `${diffInDays}d ago`
  
  return formatDate(date)
}

export function getVerdictColor(verdict: string) {
  switch (verdict) {
    case "supported":
      return "text-supported"
    case "contradicted":
      return "text-contradicted"
    case "uncertain":
      return "text-uncertain"
    default:
      return "text-muted-foreground"
  }
}

export function getVerdictBadgeClass(verdict: string) {
  switch (verdict) {
    case "supported":
      return "verdict-pill-supported"
    case "contradicted":
      return "verdict-pill-contradicted"
    case "uncertain":
      return "verdict-pill-uncertain"
    default:
      return "bg-muted text-muted-foreground"
  }
}