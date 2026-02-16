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

  if (!response.ok) {
    throw new Error("Failed to fetch response");
  }

  return response.json();
}
