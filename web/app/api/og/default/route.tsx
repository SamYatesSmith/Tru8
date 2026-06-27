import { ImageResponse } from '@vercel/og';

export const runtime = 'edge';

export async function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: '#ffffff',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        {/* Orange accent line */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 6,
            backgroundColor: '#f27907',
          }}
        />

        {/* Wordmark */}
        <div
          style={{
            fontSize: 96,
            fontWeight: 700,
            color: '#18181b',
            letterSpacing: '-0.02em',
          }}
        >
          Tru8
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 32,
            color: '#71717a',
            marginTop: 16,
            letterSpacing: '0.05em',
          }}
        >
          Evidence research infrastructure.
        </div>

        {/* Bottom accent line */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: 6,
            backgroundColor: '#f27907',
          }}
        />
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
