import { redirect } from 'next/navigation';

interface ClaimDetailRedirectProps {
  params: { id: string; position: string };
  searchParams?: { view?: string };
}

/**
 * Redirect stub — preserves old /claim/[position] deep links.
 * Redirects to the unified check page with ?claim=N query param.
 */
export default function ClaimDetailRedirect({ params, searchParams }: ClaimDetailRedirectProps) {
  const view = searchParams?.view ? `&view=${searchParams.view}` : '';
  redirect(`/dashboard/check/${params.id}?claim=${params.position}${view}`);
}
