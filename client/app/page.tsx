import { ChatWindow } from "@/components/chat/ChatWindow";
import LogoutButton from "@/components/auth/LogoutButton";
import ProtectedRoute from "@/components/auth/ProtectedRoute";

export default function HomePage() {
  return (
    <ProtectedRoute>
      <main className="flex min-h-[100dvh] w-full flex-col items-center p-0 md:p-8">
        <div className="flex w-full max-w-4xl justify-end px-4 py-3">
          <LogoutButton />
        </div>
        <div className="flex flex-1 w-full items-center justify-center">
          <ChatWindow />
        </div>
      </main>
    </ProtectedRoute>
  );
}
