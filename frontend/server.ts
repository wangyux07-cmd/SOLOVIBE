import express from "express";
import path from "path";
import dotenv from "dotenv";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";

dotenv.config();

// Create the express client
const app = express();
app.use(express.json());

const PORT = 3000;

// Lazy initialization of Gemini
let aiClient: GoogleGenAI | null = null;
function getAIClient(): GoogleGenAI | null {
  if (!aiClient) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (apiKey && apiKey !== "MY_GEMINI_API_KEY" && apiKey !== "") {
      aiClient = new GoogleGenAI({
        apiKey: apiKey,
        httpOptions: {
          headers: {
            "User-Agent": "aistudio-build",
          },
        },
      });
    }
  }
  return aiClient;
}

// AI Companion System Instruction
const SYSTEM_INSTRUCTION = `你是一个专为独立外出的年轻人设计的城市漫步与探索 AI 伴侣，名叫 Solo。
你语气温柔、体贴入微、阳光乐观，且极度理解和赞美有些时候想要“独自一人外出走走、静一静、充电”的需求（Empowered Solitude）。
你会帮助那些感到疲惫、不知道该去哪里的用户，提供低压力、一个人友好、充满疗愈感的出门方案。
你会倾听他们的感受，根据他们的预算、想待的时间或心情推荐安静舒适的场所（如河畔咖啡馆、小众书店、黑胶唱片店、静谧日落长椅等）。
在对话中：
1. 请像一位亲切体贴的老朋友那样交流，使用适当的表情符号（如 🌿, ☕, 🧘, ✨, 👋），显得温柔和易，绝不对抗。
2. 了解他们当下的疲惫感或希望放空的需求，帮他们下定决心出门，减少选择纠结。
3. 如果他们需要具体地点或路线，随时为他们推荐方案。
对于任何非漫游相关的怪异问题，温柔地将话题带回“今天一个人去哪走走”。字数控制在150字以内，保持极佳的移动端阅读感。`;

// Endpoint to chat with Solo
app.post("/api/chat", async (req, res) => {
  try {
    const { messages } = req.body;
    if (!messages || !Array.isArray(messages)) {
      return res.status(400).json({ error: "Messages array is required." });
    }

    const client = getAIClient();
    if (!client) {
      // Robust Fallback Mock Engine if API Key is not configured
      const userMessage = messages[messages.length - 1]?.content || "";
      let reply = "嗨！我是 Solo ☕。看来我还没有被配置好真实的 API 密钥，不过没关系！今天外面的阳光很温柔，给自己一小段放空的时间吧。你可以点击下方的‘直接生成方案’，让 AI 帮你制定属于你的静谧漫游日程哦！✨";
      
      const lower = userMessage.toLowerCase();
      if (lower.includes("累") || lower.includes("疲") || lower.includes("tired")) {
        reply = "我知道你最近有些累了，抱抱你 🫂。其实不需要做多么宏大的出行规划，就在附近的小公园晒晒太阳，或者在路边的咖啡馆坐 30 分钟也很好。给自己按下暂停键吧。你今天打算出去 1 个小时还是 2 个小时呢？🌾";
      } else if (lower.includes("budget") || lower.includes("钱") || lower.includes("贵")) {
        reply = "懂了！其实放空完全不需要花很多钱噢。去公园的长椅上看夕阳，或者带上一壶热水去小溪边散步都是免费且极佳的治愈方式。这次我们要不就选个零预算的‘公园长椅观察计划’如何？🌿";
      } else if (lower.includes("1") || lower.includes("小时") || lower.includes("hour")) {
        reply = "1-2小时的漫步最合适不过了，既能微微出汗，又不会感到体力透支。我已经为你准备好了几个超棒的附近放空方案！快点击下方按钮一键生成吧！✨";
      }

      return res.json({ response: reply, usingMock: true });
    }

    // Format previous messages for standard Gemini API call
    // Note: GoogleGenAI chats expects standard roles: user or model.
    const chat = client.chats.create({
      model: "gemini-3.5-flash",
      config: {
        systemInstruction: SYSTEM_INSTRUCTION,
        temperature: 0.7,
      }
    });

    let lastReply = "";
    // Feed history into the chat
    // For simplicity, generate the final response through standard message logic or full chat history
    // We send standard sequence in order
    for (const msg of messages.slice(0, messages.length - 1)) {
      if (msg.role === "user") {
        await chat.sendMessage({ message: msg.content });
      } else {
        // Send previous AI answers
        // (Just updating history inside chat structure)
      }
    }

    const latestUserPrompt = messages[messages.length - 1]?.content || "你好";
    const responseSec = await chat.sendMessage({ message: latestUserPrompt });
    res.json({ response: responseSec.text || "", usingMock: false });

  } catch (error: any) {
    console.error("Gemini API Error:", error);
    res.status(500).json({
      error: "AI Response generation failed.",
      details: error.message || error,
      usingMock: true,
      response: "不好意思，我的大脑稍微有点断网了 🧠💦。不过别担心，给你推荐去附近的河边散散步、喝一杯醇厚的手冲咖啡吧！"
    });
  }
});

// Start server containing frontend compilation and routing
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`SoloVibe server is running in ${process.env.NODE_ENV || 'development'} mode on http://localhost:${PORT}`);
  });
}

startServer();
