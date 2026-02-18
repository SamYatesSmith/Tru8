import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { ClaimDetailClient } from './claim-detail-client';

interface ClaimDetailPageProps {
  params: { id: string; position: string };
}

export default async function ClaimDetailPage({ params }: ClaimDetailPageProps) {
  const { getToken } = auth();
  const token = await getToken();

  let checkData: any;
  try {
    checkData = await apiClient.getCheckById(params.id, token);
  } catch (error: any) {
    if (error.message?.includes('404') || error.message?.includes('not found')) {
      redirect('/dashboard/history');
    }
    throw error;
  }

  const position = parseInt(params.position, 10);
  const claims = checkData.claims || [];

  if (isNaN(position) || position < 0 || position >= claims.length) {
    redirect(`/dashboard/check/${params.id}`);
  }

  return (
    <ClaimDetailClient
      checkId={params.id}
      claim={claims[position]}
      position={position}
    />
  );
}
