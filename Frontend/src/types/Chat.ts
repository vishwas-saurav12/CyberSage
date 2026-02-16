export interface ChatResponse {
  attack_name: string;
  summary: string;
  attack_vector: string;
  impact: string;
  prevention: string[];
  severity: string;
  confidence: number;
}
