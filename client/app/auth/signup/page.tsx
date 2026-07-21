import AuthForm from "@/components/auth/AuthForm";

export default function SignUpPage() {
  return (
    <main className="flex min-h-[100dvh] w-full items-center justify-center p-0 md:p-8">
      <AuthForm mode="signup" />
    </main>
  );
}
