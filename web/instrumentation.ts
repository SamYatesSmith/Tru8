export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const Sentry = await import("@sentry/nextjs");

    Sentry.init({
      dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
      enabled: process.env.NODE_ENV === "production",
      tracesSampleRate: 0.1,
      debug: false,
    });
  }
}
