import { createServer } from "http";
import { Server } from "socket.io";
import { nanoid } from "nanoid";

const httpServer = createServer();
const io = new Server(httpServer, { cors: { origin: "*" } });

function detectPnr(content: string) {
  return content.match(/\b\d{10}\b/)?.[0] ?? null;
}

async function generateReply(content: string) {
  const lower = content.toLowerCase();
  const pnr = detectPnr(content);

  if (pnr) {
    return {
      text: `Here's the latest status for PNR ${pnr}:`,
      attachment: { type: "pnr_status" as const, pnr, status: "Confirmed · B4, 22", chart: "Prepared" },
    };
  }

  // Widget: date picker
  if (/date|when|journey|travel|tomorrow|day/.test(lower)) {
    return {
      text: "Which date would you like to travel?",
      attachment: {
        type: "widget" as const,
        widget: { type: "date_picker" as const, label: "Journey Date" },
      },
    };
  }

  // Widget: station picker
  if (/from|source|origin|departure station/.test(lower)) {
    return {
      text: "Please select your departure station:",
      attachment: {
        type: "widget" as const,
        widget: { type: "station_picker" as const, label: "From Station", field: "from" as const },
      },
    };
  }

  if (/to |destination|arrival station/.test(lower)) {
    return {
      text: "Please select your destination station:",
      attachment: {
        type: "widget" as const,
        widget: { type: "station_picker" as const, label: "To Station", field: "to" as const },
      },
    };
  }

  // Widget: class selector
  if (/class|berth|seat type|ac|sleeper/.test(lower)) {
    return {
      text: "Which travel class do you prefer?",
      attachment: {
        type: "widget" as const,
        widget: {
          type: "class_selector" as const,
          label: "Travel Class",
          options: ["1A", "2A", "3A", "SL", "CC", "EC"],
        },
      },
    };
  }

  // Widget: passenger count
  if (/passenger|how many|people|person|traveller/.test(lower)) {
    return {
      text: "How many passengers will be travelling?",
      attachment: {
        type: "widget" as const,
        widget: { type: "passenger_count" as const, label: "Passengers", min: 1, max: 6 },
      },
    };
  }

  // Widget: quick reply
  if (/help|what can|options|menu/.test(lower)) {
    return {
      text: "What would you like to do?",
      attachment: {
        type: "widget" as const,
        widget: {
          type: "quick_reply" as const,
          label: "Choose an option",
          options: [
            "Check PNR status",
            "Search trains between stations",
            "Check seat availability",
            "Book a ticket",
            "Cancel a ticket",
          ],
        },
      },
    };
  }

  // Train list
  if (/train|search|route/.test(lower)) {
    return {
      text: "Here are a few options that match your route:",
      attachment: {
        type: "train_list" as const,
        trains: [
          { number: "12951", name: "Mumbai Rajdhani", from: "NDLS", to: "BCT", departure: "16:25", arrival: "08:15", duration: "15h 50m", classes: ["1A", "2A", "3A"] },
          { number: "12009", name: "Shatabdi Express", from: "NDLS", to: "ADI", departure: "06:10", arrival: "13:35", duration: "7h 25m", classes: ["CC", "EC"] },
        ],
      },
    };
  }

  return {
    text: "I can help with PNR status, train searches, seat availability, and bookings. Type 'help' to see all options.",
    attachment: { type: "none" as const },
  };
}

io.on("connection", (socket) => {
  socket.on("query:send", async ({ id, content }) => {
    socket.emit("query:ack", { id });
    socket.emit("agent:typing", { isTyping: true });

    const { text, attachment } = await generateReply(content);
    const replyId = nanoid();

    const words = text.split(" ");
    for (const word of words) {
      socket.emit("message:chunk", { id: replyId, delta: word + " " });
      await new Promise((r) => setTimeout(r, 35));
    }

    socket.emit("message:complete", {
      message: { id: replyId, role: "agent", status: "sent", createdAt: Date.now(), content: text, attachment },
    });
    socket.emit("agent:typing", { isTyping: false });
  });
});

const PORT = Number(process.env.SOCKET_PORT ?? 4000);
httpServer.listen(PORT, () => console.log(`Socket server on :${PORT}`));
