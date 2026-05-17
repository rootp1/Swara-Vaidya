from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
import os
import tempfile
import traceback

# Import our refactored engine
from api_engine import evaluate_chant

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
CORS(app)

print("Loading Whisper model (this may take a bit)...")
# Load the model only once upon startup mapping to memory!
model = whisper.load_model("tiny")
print("Whisper model loaded successfully!")

@app.route('/api/compare', methods=['POST'])
def compare_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided. Please send a file in the 'audio' field."}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        audio_file.save(temp_path)

        # Run the chanting evaluation
        results = evaluate_chant(
            user_audio_path=temp_path,
            whisper_model=model
        )

        return jsonify(results), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return app.send_static_file(path)
    else:
        return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=False)
