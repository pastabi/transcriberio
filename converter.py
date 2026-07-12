import os
import subprocess
import gradio as gr
from groq import Groq
from google import genai
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path


# 1. On startup, try to load any saved keys from a local .env file
load_dotenv()

def process_pipeline(video_path, template_file, system_prompt_fallback, language_choice, groq_key, gemini_key):
    # 2. Validate API Keys
    if not groq_key.strip() or not gemini_key.strip():
        yield "❌ Error: Please enter both API Keys in the settings.", "", "", None
        return
        
    # 3. AUTO-SAVE FEATURE: Save the provided keys locally so you don't have to type them again
    with open(".env", "w") as env_file:
        env_file.write(f"GROQ_API_KEY={groq_key.strip()}\n")
        env_file.write(f"GEMINI_API_KEY={gemini_key.strip()}\n")
        
    if not video_path:
        yield "❌ Error: Please upload a video file.", "", "", None
        return

    mp3_output = "temp_audio.mp3"
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_output_path = f"results/ai_final_result_{now}.txt"
    
    # --- STEP 1: Local FFmpeg Conversion ---
    yield "⏳ Step 1/5: Extracting compressed audio locally...", "", "", None
    try:
        if os.path.exists(mp3_output):
            os.remove(mp3_output)
        command = f"ffmpeg -i '{video_path}' -vn -acodec libmp3lame -ac 1 -ar 16000 -b:a 32k '{mp3_output}' -y"
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        yield f"❌ FFmpeg Error: {str(e)}", "", "", None
        return
    
    # --- STEP 2: Groq Transcription ---
    yield "⏳ Step 2/5: Transcribing via Groq Whisper...", "", "", None
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
        yield f"❌ Groq API Error: {str(e)}", "", "", None
        return
    finally:
        if os.path.exists(mp3_output):
            os.remove(mp3_output)
            
    # --- STEP 3: Handle Template Processing ---
    yield "⏳ Step 3/5: Injecting transcript into template...", "", "", None
    template_content = ""
    if template_file is not None:
        try:
            with open(template_file.name, "r", encoding="utf-8") as f:
                template_content = f.read()
        except Exception as e:
            yield f"❌ Error reading template: {str(e)}", "", "", None
            return
    else:
        template_content = system_prompt_fallback

    placeholder = "${TRANSCRIPT}"
    if placeholder in template_content:
        formatted_final_prompt = template_content.replace(placeholder, transcript.strip())
    else:
        formatted_final_prompt = f"{template_content.strip()}\n\n{transcript.strip()}"
        
    # --- STEP 4: Send to Gemini AI ---
    yield "⏳ Step 4/5: Analyzing text with Gemini 3.5 Flash...", formatted_final_prompt, "", None
    try:
        gemini_client = genai.Client(api_key=gemini_key.strip())
        
        # FIXED: Using the correct, active gemini-3.5-flash model
        ai_response = gemini_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=formatted_final_prompt,
        )
        final_ai_text = ai_response.text
    except Exception as e:
        yield f"❌ Gemini API Error: {str(e)}", formatted_final_prompt, "", None
        return

    # --- STEP 5: Generate Downloadable File ---
    yield "⏳ Step 5/5: Saving final AI output...", formatted_final_prompt, final_ai_text, None
    try:
        Path(txt_output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(txt_output_path, "w", encoding="utf-8") as out_file:
            out_file.write(final_ai_text)
    except Exception as e:
        yield f"❌ Error saving file: {str(e)}", formatted_final_prompt, final_ai_text, None
        return

    yield "✅ Complete! The AI has processed your video.", formatted_final_prompt, final_ai_text, txt_output_path


# --- UI Layout ---
with gr.Blocks(title="Transcriberio") as app:
    gr.Markdown("# 🤖 Full AI Video Analyzer Pipeline")
    
    with gr.Row():
        with gr.Column():

            gr.Markdown("### 1. API Keys (Will auto-fill after first run)")
            # PRE-FILL FEATURE: Automatically pull the keys from the environment variables if they exist
            groq_key_input = gr.Textbox(
                label="Groq API Key (For Audio)", 
                type="password",
                value=os.getenv("GROQ_API_KEY", "")
            )
            gemini_key_input = gr.Textbox(
                label="Gemini API Key (For Text Analysis)", 
                type="password",
                value=os.getenv("GEMINI_API_KEY", "")
            )
            
            gr.Markdown("---")

            gr.Markdown("### 2. Upload video")
            with gr.Row(equal_height=False):
                video_input = gr.Video(
                    label="Choose Video File", 
                    scale=2, 
                    min_width=200
                )
                language_input = gr.Dropdown(
                    choices=["Auto-Detect", "Ukrainian", "English", "Russian", "Polish"],
                    value="Auto-Detect",
                    label="Force Transcription Language",
                    scale=1,
                    min_width=120
                )
                    
            gr.Markdown("---")

            gr.Markdown("### 3. AI Instructions Template")
            template_file_input = gr.UploadButton(
                label="Attach .txt template file", 
                file_types=[".txt"],
                variant="secondary"
            )
            fallback_text_input = gr.Textbox(
                label="Or write instructions directly here:",
                value="You are a helpful assistant. Please summarize the following video transcript in 3 bullet points:\n\n(Take into account this is automatic transcript, so some inconsistencies or meaning loses may occur because of wrong words interpretations)\n${TRANSCRIPT}",
                lines=6
            )
            
            submit_btn = gr.Button("Run Full Pipeline", variant="primary")
            status_tracker = gr.Markdown("### Status: Idle")
            
        with gr.Column():
            gr.Markdown("### 4. Results")
            prompt_output = gr.Textbox(label="Intermediate Step: The Prompt Sent to AI", lines=8)
            ai_output = gr.Textbox(label="Final Result: AI Response", lines=12)
            file_output = gr.File(label="Download AI Response (.txt)")
            
    submit_btn.click(
        fn=process_pipeline,
        inputs=[video_input, template_file_input, fallback_text_input, language_input, groq_key_input, gemini_key_input],
        outputs=[status_tracker, prompt_output, ai_output, file_output]
    )

if __name__ == "__main__":
    app.launch(inbrowser=True)
