import { Upload } from 'lucide-react';

interface Props {
  onFileSelect: (file: File) => void;
}

export default function AudioUploader({ onFileSelect }: Props) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files[0]);
    }
  };

  return (
    <div className="input-section">
      <h3>Upload Audio</h3>
      <p>Select an existing .wav audio file</p>
      <input
        type="file"
        id="audio-upload"
        accept="audio/*"
        onChange={handleChange}
        style={{ display: 'none' }}
      />
      <label htmlFor="audio-upload" className="button" style={{ backgroundColor: '#4b5563', color: 'white' }}>
        <Upload size={20} />
        Browse Files
      </label>
    </div>
  );
}
