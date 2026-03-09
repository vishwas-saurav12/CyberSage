import { useState } from "react";
import { View, Text, TextInput, Pressable, ScrollView } from "react-native";
import { sendChatQuery } from "../../src/api/chat";
import { ChatResponse } from "../../src/types/Chat";

/* Severity color mapping */
const severityColor: Record<string, string> = {
  Critical: "#ef4444",
  High: "#f97316",
  Medium: "#eab308",
  Low: "#22c55e",
};

/* Severity Badge Component */
const SeverityBadge = ({ severity }: { severity: string }) => {
  return (
    <View
      style={{
        backgroundColor: severityColor[severity] || "#6b7280",
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 6,
        alignSelf: "flex-start",
        marginTop: 6,
      }}
    >
      <Text style={{ color: "white", fontWeight: "600", fontSize: 12 }}>
        {severity.toUpperCase()}
      </Text>
    </View>
  );
};

export default function HomeScreen() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    try {
      setLoading(true);
      setError("");

      const result = await sendChatQuery(query);
      setResponse(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={{ padding: 20 }}>

      {/* Query Input */}
      <TextInput
        placeholder="Ask about a cyber attack..."
        value={query}
        onChangeText={setQuery}
        style={{
          borderWidth: 1,
          borderRadius: 8,
          padding: 12,
          marginBottom: 12
        }}
      />

      {/* Analyze Button */}
      <Pressable
        onPress={handleAnalyze}
        style={{
          backgroundColor: "#2563eb",
          padding: 12,
          borderRadius: 8,
          alignItems: "center"
        }}
      >
        <Text style={{ color: "white", fontWeight: "600" }}>
          {loading ? "Analyzing..." : "Analyze"}
        </Text>
      </Pressable>

      {/* Error Message */}
      {error ? (
        <Text style={{ color: "red", marginTop: 10 }}>{error}</Text>
      ) : null}

      {/* Result Display */}
      {response && (
        <View style={{ marginTop: 25 }}>

          {/* Attack Title */}
          <Text style={{ fontSize: 22, fontWeight: "bold" }}>
            {response.attack_name}
          </Text>

          {/* Severity Badge */}
          <SeverityBadge severity={response.severity} />

          {/* Summary */}
          <Text style={{ marginTop: 14, fontWeight: "600", fontSize: 16 }}>
            Summary
          </Text>
          <Text>{response.summary}</Text>

          {/* Attack Vector */}
          <Text style={{ marginTop: 14, fontWeight: "600", fontSize: 16 }}>
            Attack Vector
          </Text>
          <Text>{response.attack_vector}</Text>

          {/* Impact */}
          <Text style={{ marginTop: 14, fontWeight: "600", fontSize: 16 }}>
            Impact
          </Text>
          <Text>{response.impact}</Text>

          {/* Prevention */}
          <Text style={{ marginTop: 14, fontWeight: "600", fontSize: 16 }}>
            Prevention
          </Text>

          {response.prevention.map((step, index) => (
            <Text key={index}>• {step}</Text>
          ))}

          {/* Confidence */}
          <Text style={{ marginTop: 16, fontWeight: "600" }}>
            Confidence Score: {response.confidence}
          </Text>

        </View>
      )}

    </ScrollView>
  );
}