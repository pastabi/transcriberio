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

# here we store directories of temp files we would need to clean after some processes are done
temp_dirs = []

# creating a indicator, if our pipline not running or not,
# we need it to track this state in UI and be able to fire cleanup function
pipeline_active = threading.Event()


# main pipeline execution function that will run all steps one by one
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
    # prepares array of status logs before feeding it to UI
    def get_status():
        return "\n".join(status_logs)

    # array of status logs
    status_logs = [append_timestamp("Starting Pipeline...")]

    # if user don't use AI analysis number of overal steps is lower
    number_of_steps = 4 if use_ai_cb else 3

    # checking the key presence just in case (we also don't allow to start the pipeline without them)
    if not groq_key.strip():
        yield "⚠️ Error: Please enter Groq API Key.", "", "", None, None, None
        return
    elif use_ai_cb and not gemini_key.strip():
        yield "⚠️ Error: Please enter Gemini API Key to use AI analysis.", "", "", None, None, None
        return

    # storing in .env file our keys and model name
    with open(".env", "w") as env_file:
        env_file.write(f"GROQ_API_KEY={groq_key.strip()}\n")
        env_file.write(f"GEMINI_API_KEY={gemini_key.strip()}\n")
        env_file.write(f"GEMINI_MODEL={model_name.strip()}\n")

    # checking for video input just in case (again, can't start pipeline without it)
    if not video_path and not video_url:
        yield "⚠️ Error: Please upload a video file or insert a video url.", "", "", None, None, None
        return

    # creating the filepathes for our future files output (audio, transcript text, ai analysis markdown)
    start = datetime.now()
    timestamp = start.strftime("%Y%m%d_%H%M%S")
    mp3_output = f"results/{timestamp}_audio.mp3"
    txt_output_path = f"results/{timestamp}_transcription_result.txt"
    ai_txt_output_path = f"results/{timestamp}_ai_final_result.md"

    # --- PIPELINE START ---

    # --- STEP 1: Audio ---
    # conditional status, depending of what source of video was used
    # append_timestamp adds the time at the front of the message
    audio_status_text = append_timestamp(
        f"⏳ Step 1/{number_of_steps}: Extracting audio..."
        if video_path
        else f"⏳ Step 1/{number_of_steps}: Downloading audio from provided URL..."
    )
    status_logs.append(audio_status_text)
    # this send updates to UI (the ui function listens for updates on these variables mapped to specific ui elements)
    # 1 - status field, 2 - template with transcript/transcript, 3 - AI text output, 4 - audio file, 5 - transcription text file, 6 - AI output markdown file
    yield get_status(), "", "", None, None, None

    try:
        # updating our indicator that some lasting process is starting to happen
        pipeline_active.set()
        # receiveing chanks of audio with the temp directory they stored in
        # the mp3_output path we feeds into function gets an audio tied to it inside the function, so we don't need to return it
        audio_chanks, temp_audio_chanks_dir = extract_audio(
            video_path, video_url, mp3_output
        )
        # updating our array of folders for deletion
        temp_dirs.append(temp_audio_chanks_dir)
        # now, as the action finished, we need to indicate that it's finished
        # we do this before the any yield and we can't do it in "finally", because if the pipeline got cancelled, yield won't have any listeners, so the function will just drop without reaching the indicator of "finally" block, so we won't receive any signal at UI and won't be able to update ui and run a cleanup at the very end
        # so, we need to do this for the every lasting process - indicate that it started, before it starts, and before any yield indicate that it finished (successfully or not)
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
    # updating UI about the next step start
    transcription_status_text = append_timestamp(
        f"⏳ Step 2/{number_of_steps}: Transcribing..."
    )
    status_logs.append(transcription_status_text)
    yield get_status(), "", "", mp3_output, None, None
    start = datetime.now()

    try:
        pipeline_active.set()
        # feeding audio chunks and waiting for the transcript
        # the same with txt_output_path as with audio, the file got written and bound to this path, we don't need to return it
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
    # updating UI that the next step is starting
    # conditional status, depending either user chose the template checkbox or not
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
        # if user chose to use template, we fill this template,
        # otherways we just return the transcript from the previous step
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
    # run this step only if selected in UI
    if use_ai_cb:
        # updating UI that the next step is starting
        status_logs.append(
            append_timestamp(f"⏳ Step 4/{number_of_steps}: Asking AI...")
        )
        yield get_status(), filled_template, "", mp3_output, txt_output_path, None
        start = datetime.now()
        try:
            pipeline_active.set()
            # we want to get the array of models which were tried to be used, to indicate it in UI later
            # the same with ai_txt_output_path as with audio, the file got written and bound to this path, we don't need to return anything
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

        # conditional status of which models were used depending on how many fallback models were tried
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
    # if the step is not selected in UI, just fill the empty value for UI
    else:
        final_ai_text = ""
        ai_txt_output_path = None

    # --- FINAL: Finish ---
    # just the final UI indication of pipeline finish
    status_logs.append(append_timestamp("🎉 Pipeline Completed!"))
    yield get_status(), filled_template, final_ai_text, mp3_output, txt_output_path, ai_txt_output_path


# Launch the app
# ensures web server starts only when this file is run directly
if __name__ == "__main__":
    # creating out ui, passing the pipeline function to it and starting the app in browser
    demo = create_ui(run_pipeline, temp_dirs, pipeline_active)
    demo.launch(inbrowser=True)
