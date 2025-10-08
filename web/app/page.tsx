import { AnimatedBackground } from '@/components/marketing/animated-background'

export default function Home() {
  return (
    <>
      {/* Animated Background */}
      <AnimatedBackground />

      {/* Main Content */}
      <main className="relative min-h-screen">
        <div className="container mx-auto px-4 py-20">
          <h1 className="text-5xl font-bold text-white mb-4">Tru8</h1>
          <p className="text-xl text-slate-300 mb-8">
            Phase 1 Complete: Foundation & Authentication
          </p>
          <div className="space-y-2 text-slate-400">
            <p>✅ Next.js 14 with TypeScript and Tailwind CSS</p>
            <p>✅ Clerk authentication configured</p>
            <p>✅ Backend API client with JWT token injection</p>
            <p>✅ 3-layer animated pixel grid background</p>
            <p>✅ Reduced motion accessibility support</p>
          </div>
        </div>
      </main>
    </>
  )
}
