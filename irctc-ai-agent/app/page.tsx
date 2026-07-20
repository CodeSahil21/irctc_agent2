import { ChatWindow } from "@/components/chat/ChatWindow";

export default function HomePage() {
  return (
    <main className="flex min-h-[100dvh] w-full items-center justify-center p-0 md:p-6">
      <ChatWindow />
    </main>
  );
}
