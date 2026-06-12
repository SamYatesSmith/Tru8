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
            fontSize: 56,
            fontWeight: 700,
            color: '#18181b',
            letterSpacing: '-0.02em',
          }}
        >
          Tru8
        </div>

        {/* Title */}
        <div
          style={{
            fontSize: 52,
            fontWeight: 600,
            color: '#18181b',
            marginTop: 32,
            letterSpacing: '-0.01em',
            textAlign: 'center',
            maxWidth: 1000,
          }}
        >
          Tru8 vs four grounding APIs
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 30,
            color: '#71717a',
            marginTop: 20,
            letterSpacing: '0.02em',
          }}
        >
          Same claim. Verbatim responses.
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
