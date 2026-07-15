from pathlib import Path

from groq import Groq


def transcribe_audio(mp3_chunks, groq_key, txt_output_path, language_choice):
    groq_client = Groq(api_key=groq_key.strip())
    lang_map = {"Ukrainian": "uk", "Russian": "ru", "English": "en", "Polish": "pl"}

    full_transcript = ""
    previous_context = ""

    for i, chunk_path in enumerate(mp3_chunks):
        try:
            api_options = {"model": "whisper-large-v3", "response_format": "json"}
            if language_choice != "Auto-Detect":
                api_options["language"] = lang_map[language_choice]

            if previous_context:
                api_options["prompt"] = previous_context

            with open(chunk_path, "rb") as audio_file:
                api_options["file"] = audio_file
                response = groq_client.audio.transcriptions.create(**api_options)

            chunk_text = response.text.strip()

            if full_transcript:
                full_transcript += f"\n[transcription chunk split line]\n{chunk_text}"
            else:
                full_transcript = chunk_text

            words = chunk_text.split()
            previous_context = " ".join(words[-50:]) if len(words) > 50 else chunk_text

        except Exception as e:
            raise RuntimeError(f"Groq API failed on chunk {i+1}: {str(e)}")

    try:
        Path(txt_output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(txt_output_path, "w", encoding="utf-8") as out_file:
            out_file.write(full_transcript)
    except Exception as e:
        raise IOError(f"Could not save transcription to file: {str(e)}")

    return full_transcript
