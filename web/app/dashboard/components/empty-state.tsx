interface EmptyStateProps {
  icon: React.ReactNode;
  message: string;
  submessage?: string;
}

export function EmptyState({ icon, message, submessage }: EmptyStateProps) {
  return (
    <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-12 text-center">
      <div className="flex justify-center mb-4">
        {icon}
      </div>
      <p className="text-xl font-semibold text-white mb-2">{message}</p>
      {submessage && (
        <p className="text-slate-400">{submessage}</p>
      )}
    </div>
  );
}
