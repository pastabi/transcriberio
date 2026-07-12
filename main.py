from datetime import datetime

from dotenv import load_dotenv

from src.ai_analyze import analyze_text
from src.fill_template import fill_template
from src.to_audio import FFmpegError, extract_audio
from src.transcribe import transcribe_audio
from src.ui import create_ui

load_dotenv()


def run_pipeline(
    video_path,
    template_file,
    system_prompt_fallback,
    language_choice,
    groq_key,
    gemini_key,
):
    if not groq_key.strip() or not gemini_key.strip():
        yield "❌ Error: Please enter both API Keys in the settings.", "", "", None
        return

    with open(".env", "w") as env_file:
        env_file.write(f"GROQ_API_KEY={groq_key.strip()}\n")
        env_file.write(f"GEMINI_API_KEY={gemini_key.strip()}\n")

    if not video_path:
        yield "❌ Error: Please upload a video file.", "", "", None
        return

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    mp3_output = f"results/audio_{now}.mp3"
    txt_output_path = f"results/transcription_result_{now}.txt"
    ai_txt_output_path = f"results/ai_final_result_{now}.txt"

    # --- STEP 1: Audio ---
    yield "⏳ Step 1/4: Extracting audio...", "", "", None
    try:
        extract_audio(video_path, mp3_output)
    except FFmpegError as e:
        yield f"❌ FFmpeg Error: {str(e)}", "", "", None
        return
    except Exception as e:
        yield f"❌ Unknown Error: {str(e)}", "", "", None
        return

    # --- STEP 2: Transcribe ---
    yield "⏳ Step 2/4: Transcribing...", "", "", None
    try:
        transcript = transcribe_audio(
            mp3_output, groq_key, txt_output_path, language_choice
        )
    except RuntimeError as e:
        yield f"❌ Groq Transcribing Error: {str(e)}", "", "", None
        return
    except IOError as e:
        yield f"❌ File Save Error: {str(e)}", "", "", None
        return
    except Exception as e:
        yield f"❌ Unknown Error: {str(e)}", "", "", None
        return

    # --- STEP 3: Template filling ---
    try:
        formatted_prompt = fill_template(
            transcript, template_file, system_prompt_fallback
        )
    except IOError as e:
        yield f"❌ File Read Error: {str(e)}", formatted_prompt, "", None
        return
    except Exception as e:
        yield f"❌ Unknown Error: {str(e)}", formatted_prompt, "", None
        return

    # --- STEP 4: AI analysis ---
    try:
        final_ai_text = analyze_text(formatted_prompt, gemini_key, ai_txt_output_path)
    except RuntimeError as e:
        yield f"❌ AI Error: {str(e)}", formatted_prompt, "", None
        return
    except IOError as e:
        yield f"❌ File Save Error: {str(e)}", formatted_prompt, "", None
        return
    except Exception as e:
        yield f"❌ Unknown Error: {str(e)}", formatted_prompt, "", None
        return

    # --- FINAL: Finish ---
    yield "✅ Complete!", formatted_prompt, final_ai_text, ai_txt_output_path


# Launch the app
if __name__ == "__main__":
    # Pass the run_pipeline function into our UI builder
    demo = create_ui(run_pipeline)
    demo.launch(inbrowser=True)
