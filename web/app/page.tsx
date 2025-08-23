import { CreateCheckForm } from "@/components/check/create-check-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Tru8</h1>
          <p className="text-xl text-muted-foreground mb-2">
            Instant fact-checking with dated evidence
          </p>
          <p className="text-muted-foreground">
            Get explainable verdicts on claims from articles, images, videos, and text
          </p>
        </div>

        <SignedOut>
          {/* Not signed in - show sign in prompt */}
          <div className="max-w-md mx-auto">
            <Card>
              <CardHeader>
                <CardTitle className="text-center">Get Started</CardTitle>
              </CardHeader>
              <CardContent className="text-center space-y-4">
                <p className="text-muted-foreground">
                  Sign in to start fact-checking content with Tru8
                </p>
                <SignInButton mode="modal">
                  <Button className="w-full" size="lg">
                    Sign In to Continue
                  </Button>
                </SignInButton>
              </CardContent>
            </Card>
          </div>
        </SignedOut>

        <SignedIn>
          {/* Signed in - show check form */}
          <div className="max-w-2xl mx-auto">
            <Card>
              <CardHeader>
                <CardTitle>Create New Fact-Check</CardTitle>
              </CardHeader>
              <CardContent>
                <CreateCheckForm 
                  onSuccess={(checkId) => {
                    // Redirect to check details or stay on page
                    window.location.href = `/check/${checkId}`;
                  }}
                />
              </CardContent>
            </Card>
          </div>
        </SignedIn>
      </div>
    </div>
  );
}