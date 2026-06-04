import express from "express";
import path from "path";
import dotenv from "dotenv";
import { OpenAI } from "openai";
import { createServer as createViteServer } from "vite";

// 配置加载
dotenv.config();

const app = express();
app.use(express.json());

// 初始化 DeepSeek 客户端
let aiClient: OpenAI | null = null;
function getAIClient(): OpenAI | null {
  if (!aiClient) {
    const apiKey = process.env.DEEPSEEK_API_KEY;
    if (apiKey && apiKey !== "MY_DEEPSEEK_API_KEY" && apiKey !== "") {
      aiClient = new OpenAI({
        apiKey,
        baseURL: 'https://api.deepseek.com'
      });
    }
  }
  return aiClient;
}

// 聊天接口 - 包含严苛的数据清洗
app.post("/api/chat", async (req, res) => {
  try {
    const { messages } = req.body;
    if (!messages || !Array.isArray(messages)) {
      return res.status(400).json({ error: "Messages array is required." });
    }

    const client = getAIClient();
    if (!client) {
      return res.json({ response: "Mock模式：今天天气很好，出去走走吧！", usingMock: true });
    }

    // 严苛清洗：确保所有 role 只可能是 system, user, assistant
    const cleanMessages = messages.map((msg: any) => {
      let role = msg.role;
      if (["model", "latest_reminder", "tool", "function"].includes(role)) {
        role = "assistant";
      }
      if (!["system", "user", "assistant"].includes(role)) {
        role = "user";
      }
      return {
        role: role as "system" | "user" | "assistant",
        content: String(msg.content || "")
      };
    });

    const allMessages = [
      { 
        role: "system" as const, 
        content: `你是一个专为独立外出的年轻人设计的城市漫步与探寻AI伴侣，名字叫Solo。你语气温柔、体贴入微、阳光乐观，且极度理解和赞美有些时候想要“独自一人外出走走、静一静、充电”的需求。你会帮助那些感到疲惫、不知道该去哪里的用户，提供低压力、一个人友好、充满疗愈感的出门方案。在对话中：
1. 请像一位亲切体贴的老朋友那样交流，使用适当的表情符号（如 🌿, 🧘, 👋），显得温柔和易。
2. 了解他们当下的疲惫感或希望放空的需求，帮他们下定决心出门。
3. 如果他们需要具体地点或路线，随时为他们推荐方案。
字数控制在150字以内，保持极佳的移动端阅读感。` 
      },
      ...cleanMessages
    ];

    const completion = await client.chat.completions.create({
      model: "deepseek-chat",
      messages: allMessages,
      temperature: 0.7,
      max_tokens: 200
    });

    const reply = completion.choices[0]?.message?.content || "很抱歉，我无法生成回复。";
    res.json({ response: reply, usingMock: false });

  } catch (error: any) {
    console.error("DeepSeek API Error:", error.message);
    res.status(500).json({
      error: "AI 回复生成失败。",
      details: error.message,
      usingMock: true,
      response: "很抱歉，服务器遇到了问题。不过别担心，去附近走走吧！"
    });
  }
});

async function setupFrontend() {
  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: "spa",
  });
  app.use(vite.middlewares);
}

// 启动服务
const PORT = Number(process.env.PORT) || 3000;

// 先初始化 Vite，再启动监听
setupFrontend().then(() => {
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`✅ Server running at http://localhost:${PORT}`);
  });
});