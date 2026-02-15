import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
}

export function LoadingSpinner({ message = 'Loading...' }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className="text-accent animate-spin mb-4" size={48} />
      <p className="text-zinc-400 text-lg">{message}</p>
    </div>
  );
}
