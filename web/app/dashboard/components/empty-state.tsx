interface EmptyStateProps {
  icon: React.ReactNode;
  message: string;
  submessage?: string;
}

export function EmptyState({ icon, message, submessage }: EmptyStateProps) {
  return (
    <div className="bg-white border border-zinc-200 p-12 text-center">
      <div className="flex justify-center mb-4">
        {icon}
      </div>
      <p className="text-xl font-semibold text-zinc-900 mb-2">{message}</p>
      {submessage && (
        <p className="text-zinc-500">{submessage}</p>
      )}
    </div>
  );
}
