import { API_BASE_URL } from "../config/api";
import { ChatResponse } from "../types/Chat";

export async function sendChatQuery(query: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });

  const data = await response.json();

  if (!response.ok) {
    // Backend structured error
    if (data?.detail?.message) {
      throw new Error(data.detail.message);
    }

    // Fallback
    throw new Error("Server error occurred");
  }

  return data;
}