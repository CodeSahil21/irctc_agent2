import { ChatWindow } from "@/components/chat/ChatWindow";
import LogoutButton from "@/components/auth/LogoutButton";
import ProtectedRoute from "@/components/auth/ProtectedRoute";

export default function HomePage() {
  return (
    <ProtectedRoute>
      <main className="flex h-full w-full flex-col items-center overflow-hidden box-border p-3 md:p-6">
        <div className="flex w-full max-w-7xl shrink-0 justify-end px-2 py-2">
          <LogoutButton />
        </div>
        <div className="flex min-h-0 flex-1 w-full max-w-7xl items-stretch">
          <ChatWindow />
        </div>
      </main>
    </ProtectedRoute>
  );
}
