import { useState } from 'react';
import AudioUploader from './components/AudioUploader';
import AudioRecorder from './components/AudioRecorder';
import ScoreDisplay from './components/ScoreDisplay';
import { evaluateChant, EvaluationResult } from './services/api';
import './styles/App.css';

function App() {
  const [audioSource, setAudioSource] = useState<File | Blob | null>(null);
  const [sourceName, setSourceName] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState<string>('');

  const handleFileSelect = (file: File) => {
    setAudioSource(file);
    setSourceName(`File: ${file.name}`);
    setResults(null);
    setError('');
  };

  const handleRecordingComplete = (blob: Blob) => {
    setAudioSource(blob);
    setSourceName('Microphone Recording');
    setResults(null);
    setError('');
  };

  const handleSubmit = async () => {
    if (!audioSource) return;
    
    setLoading(true);
    setError('');
    
    try {
      const data = await evaluateChant(audioSource);
      setResults(data);
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'An error occurred during evaluation.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card app-container">
      <h1>Swara-Vaidya</h1>
      <p>Ensure to speak clearly to match the reference chant patterns.</p>

      <div className="inputs-container">
        <AudioUploader onFileSelect={handleFileSelect} />
        <AudioRecorder onRecordingComplete={handleRecordingComplete} />
      </div>

      {audioSource && (
        <div style={{ marginTop: '2rem' }}>
          <p>Selected Data: <strong>{sourceName}</strong></p>
          <button 
            className="submit-btn button" 
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? 'Evaluating Model...' : 'Analyze Chant'}
          </button>
        </div>
      )}

      {error && <p style={{ color: '#ef4444', marginTop: '1rem' }}>{error}</p>}

      {results && !loading && (
        <ScoreDisplay results={results} />
      )}
    </div>
  );
}

export default App;
