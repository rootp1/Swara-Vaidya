import librosa
import numpy as np
import json
import re
from sklearn.preprocessing import StandardScaler
from librosa.sequence import dtw
from difflib import SequenceMatcher
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks, resample
import warnings

warnings.filterwarnings('ignore')

import os

def evaluate_chant(user_audio_path, whisper_model, reference_features_path=None, ref_audio_path=None):
    if reference_features_path is None:
        reference_features_path = os.path.join(os.path.dirname(__file__), "reference_features.json")
    if ref_audio_path is None:
        ref_audio_path = os.path.join(os.path.dirname(__file__), "chant1.wav")
    with open(reference_features_path, "r") as f:
        reference = json.load(f)

    ref_pitch = np.array(reference["pitch_contour"])
    ref_tempo = reference["tempo"]
    ref_mfcc = np.array(reference["mfcc"])
    ref_mantra = reference["mantra_text"]

    ref_audio, ref_sr = librosa.load(ref_audio_path)
    ref_audio, _ = librosa.effects.trim(ref_audio)

    audio, sr = librosa.load(user_audio_path)
    audio, _ = librosa.effects.trim(audio)

    pitch, _, _ = librosa.pyin(
        audio,
        fmin=librosa.note_to_hz('C2'),
        fmax=librosa.note_to_hz('C7')
    )
    pitch = np.nan_to_num(pitch)

    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    tempo = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)

    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)

    # 1. Pitch similarity
    pitch_voiced     = pitch[pitch > 0]
    ref_pitch_voiced = ref_pitch[ref_pitch > 0]
     
    if len(pitch_voiced) == 0 or len(ref_pitch_voiced) == 0:
        pitch_similarity = 0.0
    else:
        pitch_log     = np.log2(pitch_voiced)
        ref_pitch_log = np.log2(ref_pitch_voiced)
        pitch_norm     = (pitch_log - np.mean(pitch_log))         / (np.std(pitch_log)         + 1e-9)
        ref_pitch_norm = (ref_pitch_log - np.mean(ref_pitch_log)) / (np.std(ref_pitch_log)     + 1e-9)
        pitch_resampled     = resample(pitch_norm,     100)
        ref_pitch_resampled = resample(ref_pitch_norm, 100)
        D, wp = dtw(pitch_resampled.reshape(1, -1), ref_pitch_resampled.reshape(1, -1), metric='euclidean')
        dtw_distance     = D[-1, -1] / len(wp)
        pitch_similarity = 100 * np.exp(-dtw_distance / 5)

    def extract_pitch_zones(pitch_contour):
        voiced = [(i, p) for i, p in enumerate(pitch_contour) if p > 0]
        if len(voiced) < 6:
            return [], np.array([])
        pitches = np.array([v[1] for v in voiced])
        smoothed = uniform_filter1d(pitches, size=5)
        norm = (smoothed - np.mean(smoothed)) / (np.std(smoothed) + 1e-9)
        slope = np.gradient(norm)
        peaks, _ = find_peaks(norm)
        if len(peaks) == 0:
            peak_idx = int(np.argmax(norm))
        else:
            center   = len(norm) // 2
            peak_idx = peaks[int(np.argmin(np.abs(peaks - center)))]
        zones        = []
        current_zone = None
        start        = 0
        threshold    = 0.05
        for i in range(len(norm)):
            if slope[i] > threshold:
                zone = "udatta"
            elif slope[i] < -threshold:
                zone = "svarita"
            else:
                zone = "anudatta"
            if current_zone is None:
                current_zone = zone
                start        = i
            elif zone != current_zone:
                zones.append({"zone": current_zone, "avg_pitch": float(np.mean(norm[start:i])), "length": i - start})
                current_zone = zone
                start        = i
        zones.append({"zone": current_zone, "avg_pitch": float(np.mean(norm[start:])), "length": len(norm) - start})
        return zones, norm

    def compare_pitch_zones(ref_zones, user_zones):
        if not ref_zones or not user_zones:
            return 0.0, ["Could not detect pitch zones — recording may be too quiet"]
        feedback = []
        scores   = []
        ref_dict  = {z["zone"]: z for z in ref_zones}
        user_dict = {z["zone"]: z for z in user_zones}
        for zone in ["anudatta", "udatta", "svarita"]:
            if zone not in ref_dict: continue
            if zone not in user_dict:
                feedback.append(f"Missing {zone} section in your chant")
                scores.append(0.0)
                continue
            ref_z  = ref_dict[zone]
            user_z = user_dict[zone]
            pitch_diff = abs(ref_z["avg_pitch"] - user_z["avg_pitch"])
            zone_score = max(0.0, 1.0 - pitch_diff)
            scores.append(zone_score)
        ref_total  = sum(z["length"] for z in ref_zones)
        user_total = sum(z["length"] for z in user_zones)
        if ref_total > 0 and user_total > 0:
            ref_peak_ratio  = ref_dict.get("udatta",  {}).get("length", 0) / ref_total
            user_peak_ratio = user_dict.get("udatta", {}).get("length", 0) / user_total
            timing_diff     = abs(ref_peak_ratio - user_peak_ratio)
        zone_similarity = float(np.mean(scores)) * 100 if scores else 0.0
        return zone_similarity, feedback

    ref_zones,  ref_norm  = extract_pitch_zones(ref_pitch)
    user_zones, user_norm = extract_pitch_zones(pitch)
    zone_sim, zone_feedback = compare_pitch_zones(ref_zones, user_zones)

    def classify_accent_levels(pitch_contour):
        voiced = pitch_contour[pitch_contour > 0]
        if len(voiced) == 0: return np.array([])
        low_thresh  = np.percentile(voiced, 33)
        high_thresh = np.percentile(voiced, 66)
        levels = []
        for p in pitch_contour:
            if p == 0: levels.append(0)
            elif p < low_thresh: levels.append(1)
            elif p < high_thresh: levels.append(2)
            else: levels.append(3)
        return np.array(levels)

    ref_accent_levels  = classify_accent_levels(ref_pitch)
    user_accent_levels = classify_accent_levels(pitch)
    if len(ref_accent_levels) > 0 and len(user_accent_levels) > 0:
        accent_sim = SequenceMatcher(None, ref_accent_levels.tolist(), user_accent_levels.tolist()).ratio() * 100
    else:
        accent_sim = 0.0

    def detect_pitch_shape(pitch_segment):
        if len(pitch_segment) < 3: return 'flat'
        mid   = len(pitch_segment) // 2
        first = np.mean(pitch_segment[:mid])
        last  = np.mean(pitch_segment[mid:])
        peak  = np.max(pitch_segment)
        rising          = last  > first * 1.05
        falling         = first > last  * 1.05
        has_peak_middle = (peak > first * 1.05) and (peak > last * 1.05)
        if has_peak_middle: return 'rising_falling'
        elif rising: return 'rising'
        elif falling: return 'falling'
        else: return 'flat'

    def analyze_syllable_shapes(pitch_contour, n_segments=8):
        voiced = pitch_contour[pitch_contour > 0]
        if len(voiced) < n_segments: return []
        segments = np.array_split(voiced, n_segments)
        return [detect_pitch_shape(seg) for seg in segments]

    def shape_sequence_similarity(ref_shapes, user_shapes):
        if not ref_shapes or not user_shapes: return 0.0, []
        score = SequenceMatcher(None, ref_shapes, user_shapes).ratio() * 100
        return score, []

    ref_shapes  = analyze_syllable_shapes(ref_pitch)
    user_shapes = analyze_syllable_shapes(pitch)
    shape_sim, shape_feedback = shape_sequence_similarity(ref_shapes, user_shapes)

    def pitch_slope_similarity(ref_p, user_p):
        def get_slopes(p):
            voiced = p[p > 0]
            if len(voiced) < 2: return np.array([0.0])
            return np.diff(np.log2(voiced))
        ref_slopes  = get_slopes(ref_p)
        user_slopes = get_slopes(user_p)
        if len(ref_slopes) == 0 or len(user_slopes) == 0: return 0.0
        D, wp = dtw(ref_slopes.reshape(1, -1), user_slopes.reshape(1, -1), metric='euclidean')
        slope_dist = D[-1, -1] / len(wp)
        return 100 * np.exp(-slope_dist / 0.5)

    slope_sim = pitch_slope_similarity(ref_pitch, pitch)

    pitch_combined = (
        0.35 * pitch_similarity +
        0.25 * zone_sim         +
        0.15 * slope_sim        +
        0.15 * accent_sim       +
        0.10 * shape_sim
    )

    def get_onset_envelope(y, sr):
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        if onset_env.max() > 0:
            onset_env = onset_env / onset_env.max()
        return onset_env

    user_onset = get_onset_envelope(audio, sr)
    ref_onset  = get_onset_envelope(ref_audio, ref_sr)
    D, wp = dtw(user_onset.reshape(1, -1), ref_onset.reshape(1, -1), metric='euclidean')
    onset_dist       = D[-1, -1] / len(wp)
    tempo_similarity = 100 * np.exp(-onset_dist / 0.3)

    mfcc_scaled = StandardScaler().fit_transform(mfcc.T).T
    ref_mfcc_scaled = StandardScaler().fit_transform(ref_mfcc.T).T
    delta = librosa.feature.delta(mfcc_scaled)
    ref_delta = librosa.feature.delta(ref_mfcc_scaled)
    mfcc_combined = np.vstack([mfcc_scaled, delta])
    ref_mfcc_combined = np.vstack([ref_mfcc_scaled, ref_delta])
    D, wp = dtw(mfcc_combined, ref_mfcc_combined, metric='euclidean')
    mfcc_distance = D[-1, -1] / len(wp)
    mfcc_similarity = 100 * np.exp(-mfcc_distance / 50)

    user_result = whisper_model.transcribe(
        user_audio_path,
        language="en",
        initial_prompt=f"This is a Sanskrit mantra chant: {ref_mantra}"
    )
    user_text = user_result["text"].lower().strip()
    ref_text = ref_mantra.lower().strip()

    def clean_text(text):
        text = text.lower()
        text = re.sub(r'[^a-z\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    ref_clean = clean_text(ref_text)
    user_clean = clean_text(user_text)

    def split_syllables(text):
        return re.findall(r'[bcdfghjklmnpqrstvwxyz]*[aeiou]+[bcdfghjklmnpqrstvwxyz]*', text)

    ref_syllables  = split_syllables(ref_clean)
    user_syllables = split_syllables(user_clean)

    char_sim = SequenceMatcher(None, ref_clean, user_clean).ratio()
    word_sim = SequenceMatcher(None, ref_clean.split(), user_clean.split()).ratio()
    syl_sim = SequenceMatcher(None, ref_syllables, user_syllables).ratio()

    text_similarity = (0.20 * char_sim + 0.30 * word_sim + 0.50 * syl_sim) * 100
    overall = (0.40 * text_similarity + 0.25 * mfcc_similarity + 0.20 * pitch_combined + 0.15 * tempo_similarity)

    return {
        "text_similarity": round(text_similarity, 2),
        "pitch_similarity": round(pitch_combined, 2),
        "rhythm_similarity": round(tempo_similarity, 2),
        "voice_similarity": round(mfcc_similarity, 2),
        "overall_score": round(overall, 2),
        "user_transcription": user_text
    }
