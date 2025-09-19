import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div 
      style={{ 
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #F9FAFB 0%, #E5E7EB 100%)'
      }}
    >
      <SignUp 
        appearance={{
          elements: {
            formButtonPrimary: "font-semibold",
            card: "shadow-xl border border-gray-200",
            headerTitle: "font-bold text-gray-900",
            headerSubtitle: "text-gray-600",
            socialButtonsBlockButton: "border border-gray-300 font-medium",
            formFieldInput: "border-gray-300",
            footerActionLink: "font-semibold",
            rootBox: "mx-auto",
            cardBox: "mx-auto"
          },
          variables: {
            colorPrimary: "#1E40AF",
            colorText: "#1F2937",
            colorTextSecondary: "#4B5563",
            colorBackground: "#FFFFFF",
            colorInputBackground: "#FFFFFF",
            colorInputText: "#1F2937",
            borderRadius: "0.5rem",
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
          }
        }}
        afterSignUpUrl="/dashboard"
      />
    </div>
  );
}