import { EvaluationResult } from '../services/api';

interface Props {
  results: EvaluationResult;
}

export default function ScoreDisplay({ results }: Props) {
  return (
    <div className="score-display">
      <h2>Analysis Results</h2>
      
      <div className="score-grid">
        <div className="score-box" style={{ background: 'linear-gradient(135deg, #10b981, #3b82f6)', color: 'white' }}>
          <h3>Overall Score</h3>
          <p className="score-val">{results.overall_score}%</p>
        </div>
        <div className="score-box">
          <h3>Pronunciation</h3>
          <p className="score-val">{results.text_similarity}%</p>
        </div>
        <div className="score-box">
          <h3>Pitch (Vedic Accent)</h3>
          <p className="score-val">{results.pitch_similarity}%</p>
        </div>
        <div className="score-box">
          <h3>Rhythm (Tempo)</h3>
          <p className="score-val">{results.rhythm_similarity}%</p>
        </div>
        <div className="score-box">
          <h3>Voice (Timbre)</h3>
          <p className="score-val">{results.voice_similarity}%</p>
        </div>
      </div>

      <div className="transcription">
        <strong>What we heard:</strong>
        <p>"{results.user_transcription}"</p>
      </div>
    </div>
  );
}
