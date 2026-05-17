import axios from 'axios';

export interface EvaluationResult {
  text_similarity: number;
  pitch_similarity: number;
  rhythm_similarity: number;
  voice_similarity: number;
  overall_score: number;
  user_transcription: string;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? '' : 'http://localhost:5000'),
});

export const evaluateChant = async (audioBlobOrFile: Blob | File): Promise<EvaluationResult> => {
  const formData = new FormData();
  formData.append('audio', audioBlobOrFile, 'recording.wav');

  const response = await api.post<EvaluationResult>('/api/compare', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};
