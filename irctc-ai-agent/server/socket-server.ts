/**
 * Minimal Socket.IO server that mocks an IRCTC AI agent backend.
 * Run with: npm run server
 *
 * Replace `generateReply` with a call to your real LLM / agent backend.
 * The event contract (types/socket.ts) is the only thing the frontend
 * depends on, so you can swap this file out entirely.
 */
import { createServer } from "http";
import { Server } from "socket.io";
import { nanoid } from "nanoid";

const httpServer = createServer();
const io = new Server(httpServer, {
  cors: { origin: "*" },
});

function detectPnr(content: string) {
  const match = content.match(/\b\d{10}\b/);
  return match?.[0] ?? null;
}

function isTrainSearch(content: string) {
  return /train|from|to|station/i.test(content);
}

async function generateReply(content: string) {
  const pnr = detectPnr(content);

  if (pnr) {
    return {
      text: `Here's the latest status for PNR ${pnr}:`,
      attachment: {
        type: "pnr_status" as const,
        pnr,
        status: "Confirmed · B4, 22",
        chart: "Prepared",
      },
    };
  }

  if (isTrainSearch(content)) {
    return {
      text: "Here are a few options that match your route:",
      attachment: {
        type: "train_list" as const,
        trains: [
          {
            number: "12951",
            name: "Mumbai Rajdhani",
            from: "NDLS",
            to: "BCT",
            departure: "16:25",
            arrival: "08:15",
            duration: "15h 50m",
            classes: ["1A", "2A", "3A"],
          },
          {
            number: "12009",
            name: "Shatabdi Express",
            from: "NDLS",
            to: "ADI",
            departure: "06:10",
            arrival: "13:35",
            duration: "7h 25m",
            classes: ["CC", "EC"],
          },
        ],
      },
    };
  }

  return {
    text: "I can help with PNR status (share a 10-digit PNR), train searches between stations, or seat availability. What would you like to check?",
    attachment: { type: "none" as const },
  };
}

io.on("connection", (socket) => {
  socket.on("query:send", async ({ id, content }) => {
    socket.emit("query:ack", { id });
    socket.emit("agent:typing", { isTyping: true });

    const { text, attachment } = await generateReply(content);
    const replyId = nanoid();

    // simulate token-by-token streaming
    const words = text.split(" ");
    for (const word of words) {
      socket.emit("message:chunk", { id: replyId, delta: word + " " });
      await new Promise((r) => setTimeout(r, 35));
    }

    socket.emit("message:complete", {
      message: {
        id: replyId,
        role: "agent",
        status: "sent",
        createdAt: Date.now(),
        content: text,
        attachment,
      },
    });
    socket.emit("agent:typing", { isTyping: false });
  });
});

const PORT = Number(process.env.SOCKET_PORT ?? 4000);
httpServer.listen(PORT, () => {
  console.log(`IRCTC mock agent socket server listening on :${PORT}`);
});
