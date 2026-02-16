import { useState } from "react";
import { View, Text, TextInput, Pressable, ScrollView } from "react-native";
import { sendChatQuery } from "../../src/api/chat";
import { ChatResponse } from "../../src/types/Chat";

export default function HomeScreen() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onAnalyze = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await sendChatQuery(query);
      setResponse(data);
    } catch (err) {
      setError("Failed to analyze query");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={{ padding: 16 }}>
      <Text style={{ fontSize: 22, fontWeight: "600", marginBottom: 12 }}>
        CyberSage
      </Text>

      <TextInput
        placeholder="Explain WannaCry attack"
        value={query}
        onChangeText={setQuery}
        style={{
          borderWidth: 1,
          borderRadius: 8,
          padding: 12,
          marginBottom: 12,
        }}
      />

      <Pressable
        onPress={onAnalyze}
        style={{
          backgroundColor: "#2563eb",
          padding: 12,
          borderRadius: 8,
          alignItems: "center",
        }}
      >
        <Text style={{ color: "white", fontWeight: "600" }}>
          {loading ? "Analyzing..." : "Analyze"}
        </Text>
      </Pressable>

      {error && (
        <Text style={{ color: "red", marginTop: 12 }}>{error}</Text>
      )}

      {response && (
        <View style={{ marginTop: 20 }}>
          <Text style={{ fontSize: 18, fontWeight: "700" }}>
            {response.attack_name}
          </Text>

          <Text style={{ marginTop: 8 }}>{response.summary}</Text>

          <Text style={{ marginTop: 12, fontWeight: "600" }}>
            Attack Vector
          </Text>
          <Text>{response.attack_vector}</Text>

          <Text style={{ marginTop: 12, fontWeight: "600" }}>Impact</Text>
          <Text>{response.impact}</Text>

          <Text style={{ marginTop: 12, fontWeight: "600" }}>
            Prevention
          </Text>
          {response.prevention.map((item, idx) => (
            <Text key={idx}>• {item}</Text>
          ))}

          <Text style={{ marginTop: 12 }}>
            Severity: {response.severity}
          </Text>
          <Text>Confidence: {response.confidence}</Text>
        </View>
      )}
    </ScrollView>
  );
}
