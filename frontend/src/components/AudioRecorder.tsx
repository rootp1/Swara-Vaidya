import { useState, useRef } from 'react';
import { Mic, Square, CheckCircle } from 'lucide-react';

interface Props {
  onRecordingComplete: (blob: Blob) => void;
}

export default function AudioRecorder({ onRecordingComplete }: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const [hasRecorded, setHasRecorded] = useState(false);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setHasRecorded(true);
        onRecordingComplete(blob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setHasRecorded(false);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Could not access microphone.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
    }
  };

  return (
    <div className="input-section">
      <h3>Record Audio</h3>
      <p>Use your microphone to chant</p>
      
      {!isRecording ? (
        <button 
          className={`recording-btn ${hasRecorded ? 'recorded' : 'idle'}`}
          onClick={startRecording}
        >
          {hasRecorded ? <CheckCircle size={20}/> : <Mic size={20}/>}
          {hasRecorded ? 'Record Again' : 'Start Recording'}
        </button>
      ) : (
        <button className="recording-btn recording" onClick={stopRecording}>
          <Square size={20} />
          Stop Recording
        </button>
      )}
    </div>
  );
}
