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

/* 聊天接口 - 包含严苛的数据清洗
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

    // 获取最新消息
    const latestMessage = cleanMessages[cleanMessages.length - 1];
    if (!latestMessage) {
      return res.status(400).json({ error: "No message content found." });
    }

    // ✅ 转发给 FastAPI 后端
    try {
      const backendRes = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messages: cleanMessages,
          thread_id: req.body?.thread_id || Date.now().toString()
        })
      });

      if (!backendRes.ok) {
        const errorText = await backendRes.text();
        console.error(`Backend returned error ${backendRes.status}:`, errorText);
        throw new Error(`Backend error: ${backendRes.status} ${errorText}`);
      }

      const backendData = await backendRes.json();
      res.json({ response: backendData.response, usingMock: false });
    } catch (error: any) {
      console.error("Backend fetch error:", error);
      res.status(500).json({
        error: "Backend request failed.",
        details: error.message,
        usingMock: true,
        response: "后端连接失败，不过别担心，出去走走吧！"
      });
    }

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
*/

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