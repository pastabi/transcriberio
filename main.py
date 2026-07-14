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
    use_template_cb,
    use_ai_cb,
):
    status_logs = ["Starting Pipeline..."]
    number_of_steps = 4 if use_ai_cb else 3

    def get_status():
        return "\n".join(status_logs)

    if not groq_key.strip() or not gemini_key.strip():
        yield "❌ Error: Please enter both API Keys in the settings.", "", "", None, None, None
        return

    with open(".env", "w") as env_file:
        env_file.write(f"GROQ_API_KEY={groq_key.strip()}\n")
        env_file.write(f"GEMINI_API_KEY={gemini_key.strip()}\n")

    if not video_path:
        yield "❌ Error: Please upload a video file.", "", "", None, None, None
        return

    start = datetime.now()
    timestamp = start.strftime("%Y%m%d_%H%M%S")
    mp3_output = f"results/{timestamp}_audio.mp3"
    txt_output_path = f"results/{timestamp}_transcription_result.txt"
    ai_txt_output_path = f"results/{timestamp}_ai_final_result.txt"

    # --- STEP 1: Audio ---
    audio_status_text = f"⏳ Step 1/{number_of_steps}: Extracting audio..."
    status_logs.append(audio_status_text)
    yield get_status(), "", "", None, None, None

    try:
        extract_audio(video_path, mp3_output)
    except FFmpegError as e:
        status_logs.append(f"❌ FFmpeg Error: {str(e)}")
        yield get_status(), "", "", None, None, None
        return
    except Exception as e:
        status_logs.append(f"❌ Unknown Error: {str(e)}")
        yield get_status(), "", "", None, None, None
        return

    elapsed = datetime.now() - start
    seconds_taken = round(elapsed.total_seconds(), 1)
    status_logs.append(f"✅ Done in {seconds_taken} seconds")
    yield get_status(), "", "", mp3_output, None, None

    # --- STEP 2: Transcribe ---
    transcription_status_text = f"⏳ Step 2/{number_of_steps}: Transcribing..."
    status_logs.append(transcription_status_text)
    yield get_status(), "", "", mp3_output, None, None
    start = datetime.now()

    try:
        transcript = transcribe_audio(
            mp3_output, groq_key, txt_output_path, language_choice
        )
    except RuntimeError as e:
        status_logs.append(f"❌ Groq Transcribing Error: {str(e)}")
        yield get_status(), "", "", mp3_output, None, None
        return
    except IOError as e:
        status_logs.append(f"❌ File Save Error: {str(e)}")
        yield get_status(), "", "", mp3_output, None, None
        return
    except Exception as e:
        status_logs.append(f"❌ Unknown Error: {str(e)}")
        yield get_status(), "", "", mp3_output, None, None
        return

    elapsed = datetime.now() - start
    seconds_taken = round(elapsed.total_seconds(), 1)
    status_logs.append(f"✅ Done in {seconds_taken} seconds")
    yield get_status(), "", "", mp3_output, txt_output_path, None

    # --- STEP 3: Template filling ---
    template_status_text = (
        f"⏳ Step 3/{number_of_steps}: Filling the template..."
        if use_template_cb
        else f"⏳ Step 3/{number_of_steps}: Outputting the transcription..."
    )
    status_logs.append(template_status_text)
    yield get_status(), "", "", mp3_output, txt_output_path, None
    start = datetime.now()

    try:
        filled_template = (
            fill_template(transcript, template_file, system_prompt_fallback)
            if use_template_cb
            else transcript
        )
    except IOError as e:
        status_logs.append(f"❌ File Read Error: {str(e)}")
        yield get_status(), filled_template, "", mp3_output, txt_output_path, None
        return
    except Exception as e:
        status_logs.append(f"❌ Unknown Error: {str(e)}")
        yield get_status(), filled_template, "", mp3_output, txt_output_path, None
        return

    elapsed = datetime.now() - start
    seconds_taken = round(elapsed.total_seconds(), 1)
    status_logs.append(f"✅ Done in {seconds_taken} seconds")
    yield get_status(), filled_template, "", mp3_output, txt_output_path, None

    # --- STEP 4: AI analysis ---
    if use_ai_cb:
        status_logs.append(f"⏳ Step 4/{number_of_steps}: Asking AI...")
        yield get_status(), filled_template, "", mp3_output, txt_output_path, None
        start = datetime.now()
        try:
            final_ai_text = analyze_text(
                filled_template, gemini_key, ai_txt_output_path
            )
        except RuntimeError as e:
            status_logs.append(f"❌ AI Error: {str(e.message)}")
            yield get_status(), filled_template, "", mp3_output, txt_output_path, None
            return
        except IOError as e:
            status_logs.append(f"❌ File Save Error: {str(e)}")
            yield get_status(), filled_template, "", mp3_output, txt_output_path, None
            return
        except Exception as e:
            status_logs.append(f"❌ Unknown Error: {str(e)}")
            yield get_status(), filled_template, "", mp3_output, txt_output_path, None
            return

        elapsed = datetime.now() - start
        seconds_taken = round(elapsed.total_seconds(), 1)
        status_logs.append(f"✅ Done in {seconds_taken} seconds")
        yield get_status(), filled_template, final_ai_text, mp3_output, txt_output_path, ai_txt_output_path
    else:
        final_ai_text = ""
        ai_txt_output_path = None

    # --- FINAL: Finish ---
    status_logs.append("🎉 Pipeline Completed!")
    yield get_status(), filled_template, final_ai_text, mp3_output, txt_output_path, ai_txt_output_path


# Launch the app
if __name__ == "__main__":
    # Pass the run_pipeline function into our UI builder
    demo = create_ui(run_pipeline)
    demo.launch(inbrowser=True)
