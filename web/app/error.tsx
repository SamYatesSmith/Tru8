'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
        <p className="text-gray-600 mb-4 text-sm">
          An unexpected error occurred. Please try again.
        </p>
        <button
          onClick={reset}
          className="px-4 py-2 bg-black text-white text-sm rounded hover:bg-gray-800"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
