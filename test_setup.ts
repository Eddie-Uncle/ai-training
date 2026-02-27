import { GoogleGenerativeAI } from "@google/generative-ai";
import { config } from "dotenv";

async function testSetup() {
  console.log("🔍 Testing setup...");
  
  // Load environment variables from .env file
  config();

  const apiKey = process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;
  if (!apiKey) {
    console.log("⚠️  GOOGLE_API_KEY or GEMINI_API_KEY not found in environment");
    return false;
  }

  try {
    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });
    const result = await model.generateContent("Hi");
    const response = await result.response;
    console.log("✅ Setup successful! API is working.");
    console.log("📝 Response:", response.text().substring(0, 50) + "...");
    return true;
  } catch (error) {
    console.log("❌ Error:", error);
    return false;
  }
}

testSetup();