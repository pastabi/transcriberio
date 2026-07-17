import threading
from datetime import datetime

from dotenv import load_dotenv

from src.ai_analyze import analyze_text
from src.fill_template import fill_template
from src.to_audio import FFmpegError, extract_audio
from src.transcribe import transcribe_audio
from src.ui import create_ui
from src.utils.utils import append_timestamp, cleanup_temp_dirs, seconds_passed

load_dotenv()

temp_dirs = []


pipeline_active = threading.Event()


def run_pipeline(
    video_path,
    video_url,
    template_file,
    system_prompt_fallback,
    language_choice,
    groq_key,
    gemini_key,
    model_name,
    use_template_cb,
    use_ai_cb,
):
    def get_status():
        return "\n".join(status_logs)

    status_logs = [append_timestamp("Starting Pipeline...")]

    number_of_steps = 4 if use_ai_cb else 3

    if not groq_key.strip():
        yield "⚠️ Error: Please enter Groq API Key.", "", "", None, None, None
        return
    elif use_ai_cb and not gemini_key.strip():
        yield "⚠️ Error: Please enter Gemini API Key to use AI analysis.", "", "", None, None, None
        return

    with open(".env", "w") as env_file:
        env_file.write(f"GROQ_API_KEY={groq_key.strip()}\n")
        env_file.write(f"GEMINI_API_KEY={gemini_key.strip()}\n")
        env_file.write(f"GEMINI_MODEL={model_name.strip()}\n")

    if not video_path and not video_url:
        yield "⚠️ Error: Please upload a video file or insert video url.", "", "", None, None, None
        return

    start = datetime.now()
    timestamp = start.strftime("%Y%m%d_%H%M%S")
    mp3_output = f"results/{timestamp}_audio.mp3"
    txt_output_path = f"results/{timestamp}_transcription_result.txt"
    ai_txt_output_path = f"results/{timestamp}_ai_final_result.md"

    # --- STEP 1: Audio ---
    audio_status_text = append_timestamp(
        f"⏳ Step 1/{number_of_steps}: Extracting audio..."
        if video_path
        else f"⏳ Step 1/{number_of_steps}: Downloading audio from provided URL..."
    )
    status_logs.append(audio_status_text)
    yield get_status(), "", "", None, None, None

    try:
        pipeline_active.set()
        audio_chanks, temp_audio_chanks_dir = extract_audio(
            video_path, video_url, mp3_output
        )
        temp_dirs.append(temp_audio_chanks_dir)
        pipeline_active.clear()
    except FFmpegError as e:
        pipeline_active.clear()
        status_logs.append(append_timestamp(f"⚠️ FFmpeg Error: {str(e)}"))
        yield get_status(), "", "", None, None, None
        return
    except Exception as e:
        pipeline_active.clear()
        status_logs.append(append_timestamp(f"⚠️ Unknown Error: {str(e)}"))
        yield get_status(), "", "", None, None, None
        return

    # calculating how many seconds the step taken and outputting the result
    seconds_taken = seconds_passed(start)
    status_logs.append(append_timestamp(f"✅ Done in {seconds_taken} seconds"))
    yield get_status(), "", "", mp3_output, None, None

    # --- STEP 2: Transcribe ---
    transcription_status_text = append_timestamp(
        f"⏳ Step 2/{number_of_steps}: Transcribing..."
    )
    status_logs.append(transcription_status_text)
    yield get_status(), "", "", mp3_output, None, None
    start = datetime.now()

    try:
        pipeline_active.set()
        transcript = transcribe_audio(
            audio_chanks, groq_key, txt_output_path, language_choice
        )
        pipeline_active.clear()
    except RuntimeError as e:
        pipeline_active.clear()
        status_logs.append(append_timestamp(f"⚠️ Groq Transcribing Error: {str(e)}"))
        yield get_status(), "", "", mp3_output, None, None
        return
    except IOError as e:
        pipeline_active.clear()
        status_logs.append(append_timestamp(f"⚠️ File Save Error: {str(e)}"))
        yield get_status(), "", "", mp3_output, None, None
        return
    except Exception as e:
        pipeline_active.clear()
        status_logs.append(append_timestamp(f"⚠️ Unknown Error: {str(e)}"))
        yield get_status(), "", "", mp3_output, None, None
        return
    finally:
        # when we got the transcript we don't need chanks anymore
        cleanup_temp_dirs(temp_dirs)

    seconds_taken = seconds_passed(start)
    status_logs.append(append_timestamp(f"✅ Done in {seconds_taken} seconds"))
    yield get_status(), "", "", mp3_output, txt_output_path, None

    # --- STEP 3: Template filling ---
    template_status_text = append_timestamp(
        f"⏳ Step 3/{number_of_steps}: Filling the template..."
        if use_template_cb
        else f"⏳ Step 3/{number_of_steps}: Outputting the transcription..."
    )
    status_logs.append(template_status_text)
    yield get_status(), "", "", mp3_output, txt_output_path, None
    start = datetime.now()

    try:
        pipeline_active.set()
        filled_template = (
            fill_template(transcript, template_file, system_prompt_fallback)
            if use_template_cb
            else transcript
        )
        pipeline_active.clear()
    except IOError as e:
        pipeline_active.clear()
        status_logs.append(append_timestamp(f"⚠️ File Read Error: {str(e)}"))
        yield get_status(), filled_template, "", mp3_output, txt_output_path, None
        return
    except Exception as e:
        pipeline_active.clear()
        status_logs.append(append_timestamp(f"⚠️ Unknown Error: {str(e)}"))
        yield get_status(), filled_template, "", mp3_output, txt_output_path, None
        return

    seconds_taken = seconds_passed(start)
    status_logs.append(append_timestamp(f"✅ Done in {seconds_taken} seconds"))
    yield get_status(), filled_template, "", mp3_output, txt_output_path, None

    # --- STEP 4: AI analysis ---
    if use_ai_cb:
        status_logs.append(
            append_timestamp(f"⏳ Step 4/{number_of_steps}: Asking AI...")
        )
        yield get_status(), filled_template, "", mp3_output, txt_output_path, None
        start = datetime.now()
        try:
            pipeline_active.set()
            final_ai_text, models_used = analyze_text(
                filled_template, gemini_key, model_name, ai_txt_output_path
            )
            pipeline_active.clear()
        except RuntimeError as e:
            pipeline_active.clear()
            status_logs.append(append_timestamp(f"⚠️ AI Error: {str(e)}"))
            yield get_status(), filled_template, "", mp3_output, txt_output_path, None
            return
        except IOError as e:
            pipeline_active.clear()
            status_logs.append(append_timestamp(f"⚠️ File Save Error: {str(e)}"))
            yield get_status(), filled_template, "", mp3_output, txt_output_path, None
            return
        except Exception as e:
            pipeline_active.clear()
            status_logs.append(append_timestamp(f"⚠️ Unknown Error: {str(e)}"))
            yield get_status(), filled_template, "", mp3_output, txt_output_path, None
            return

        seconds_taken = seconds_passed(start)

        if len(models_used) == 2:
            status_logs.append(
                append_timestamp(
                    f"ℹ️ Model {models_used[0]} was unavailable, used {models_used[1]} instead"
                )
            )
        elif len(models_used) == 3:
            status_logs.append(
                append_timestamp(
                    f"ℹ️ Models {models_used[0]}, {models_used[1]} were unavailable, used {models_used[2]} instead"
                )
            )
        else:
            status_logs.append(append_timestamp(f"ℹ️ Model {models_used[0]} was used"))

        status_logs.append(append_timestamp(f"✅ Done in {seconds_taken} seconds"))
        yield get_status(), filled_template, final_ai_text, mp3_output, txt_output_path, ai_txt_output_path
    else:
        final_ai_text = ""
        ai_txt_output_path = None

    # --- FINAL: Finish ---
    status_logs.append(append_timestamp("🎉 Pipeline Completed!"))
    yield get_status(), filled_template, final_ai_text, mp3_output, txt_output_path, ai_txt_output_path


# Launch the app
if __name__ == "__main__":
    # Pass the run_pipeline function into our UI builder
    demo = create_ui(run_pipeline, temp_dirs, pipeline_active)
    demo.launch(inbrowser=True)
