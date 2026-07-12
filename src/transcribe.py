from pathlib import Path

from groq import Groq


def transcribe_audio(mp3_output, groq_key, txt_output_path, language_choice):
    try:
        groq_client = Groq(api_key=groq_key.strip())
        lang_map = {"Ukrainian": "uk", "English": "en", "Russian": "ru", "Polish": "pl"}
        api_options = {"model": "whisper-large-v3", "response_format": "json"}
        if language_choice != "Auto-Detect":
            api_options["language"] = lang_map[language_choice]

        with open(mp3_output, "rb") as audio_file:
            api_options["file"] = audio_file
            response = groq_client.audio.transcriptions.create(**api_options)
        transcript = response.text
    except Exception as e:
        raise RuntimeError(f"Groq API failed to transcribe audio: {str(e)}")

    try:
        Path(txt_output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(txt_output_path, "w", encoding="utf-8") as out_file:
            out_file.write(transcript)
    except Exception as e:
        raise IOError(f"Could not save transcription to file: {str(e)}")

    return transcript
