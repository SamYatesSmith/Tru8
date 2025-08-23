export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || "v1";

export const COLORS = {
  darkIndigo: "#2C2C54",
  deepPurpleGrey: "#474787",
  coolGrey: "#AAABB8", 
  lightGrey: "#ECECEC",
  supported: "#1E6F3D",
  contradicted: "#B3261E",
  uncertain: "#A15C00",
} as const;

export const VERDICT_LABELS = {
  supported: "Supported",
  contradicted: "Contradicted", 
  uncertain: "Uncertain",
} as const;

export const VERDICT_ICONS = {
  supported: "✓",
  contradicted: "!",
  uncertain: "?",
} as const;