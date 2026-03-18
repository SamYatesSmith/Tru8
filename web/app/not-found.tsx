import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold mb-2">Page not found</h2>
        <p className="text-gray-600 mb-4 text-sm">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          href="/"
          className="inline-block px-4 py-2 bg-black text-white text-sm rounded hover:bg-gray-800"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
