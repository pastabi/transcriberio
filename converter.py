import os
import subprocess
import gradio as gr
from groq import Groq

def process_pipeline(video_path, template_file, system_prompt_fallback, language_choice, user_api_key):
    # 1. Validate API Key input first
    if not user_api_key.strip():
        yield "❌ Error: Please enter a valid Groq API Key in the settings box.", "", None
        return
        
    if not video_path:
        yield "❌ Error: Please upload a video file.", "", None
        return

    mp3_output = "temp_audio.mp3"
    txt_output_path = "final_prompt.txt"
    
    # --- STEP 1: Local FFmpeg Conversion ---
    yield "⏳ Step 1/4: Extracting compressed audio locally...", "", None
    try:
        if os.path.exists(mp3_output):
            os.remove(mp3_output)
        command = f"ffmpeg -i '{video_path}' -vn -acodec libmp3lame -ac 1 -ar 16000 -b:a 32k '{mp3_output}' -y"
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        yield f"❌ FFmpeg Error: {str(e)}", "", None
        return
    
    # --- STEP 2: Initialize Groq Dynamically with User's Key ---
    yield "⏳ Step 2/4: Audio extracted! Transcribing via Groq Cloud API...", "", None
    try:
        # We initialize the client inside the function using the key provided by the UI textbox
        client = Groq(api_key=user_api_key.strip())
        
        lang_map = {"Ukrainian": "uk", "English": "en", "Russian": "ru", "Polish": "pl"}
        api_options = {"model": "whisper-large-v3", "response_format": "json", "file": None}
        if language_choice != "Auto-Detect":
            api_options["language"] = lang_map[language_choice]

        with open(mp3_output, "rb") as audio_file:
            api_options["file"] = audio_file
            response = client.audio.transcriptions.create(**api_options)
        transcript = response.text
    except Exception as e:
        yield f"❌ Groq API Error: {str(e)}", "", None
        return
    finally:
        if os.path.exists(mp3_output):
            os.remove(mp3_output)
            
    # --- STEP 3: Handle Template Processing ---
    yield "⏳ Step 3/4: Processing your template and placeholders...", "", None
    template_content = ""
    if template_file is not None:
        try:
            with open(template_file.name, "r", encoding="utf-8") as f:
                template_content = f.read()
        except Exception as e:
            yield f"❌ Error reading template file: {str(e)}", "", None
            return
    else:
        template_content = system_prompt_fallback

    placeholder = "${TRANSCRIPT}"
    if placeholder in template_content:
        formatted_final_prompt = template_content.replace(placeholder, transcript.strip())
    else:
        formatted_final_prompt = f"{template_content.strip()}\n\n{transcript.strip()}"
        
    # --- STEP 4: Generate Downloadable File ---
    yield "⏳ Step 4/4: Writing final prompt to a text file...", "", None
    try:
        with open(txt_output_path, "w", encoding="utf-8") as out_file:
            out_file.write(formatted_final_prompt)
    except Exception as e:
        yield f"❌ Error creating download file: {str(e)}", "", None
        return

    yield "✅ Complete! Your prompt is ready below.", formatted_final_prompt, txt_output_path

# --- UI Layout ---
with gr.Blocks(title="Cloud Prompt Packager") as demo:
    gr.Markdown("# 🎬 Video to LLM Prompt Packager")
    
    with gr.Row():
        with gr.Column():
            # --- NEW UI ELEMENT: API Key Input Box ---
            api_key_input = gr.Textbox(
                label="🔑 Enter Groq API Key", 
                placeholder="gsk_...", 
                type="password"
            )
            video_input = gr.Video(label="1. Upload Video File (.mp4)")
            language_input = gr.Dropdown(
                choices=["Auto-Detect", "Ukrainian", "English", "Russian", "Polish"],
                value="Auto-Detect",
                label="2. Force Transcription Language"
            )
            
            gr.Markdown("### 3. Choose Template Option (File takes priority)")
            template_file_input = gr.File(label="Upload a .txt template file", file_types=[".txt"])
            fallback_text_input = gr.Textbox(
                label="Or write fallback instructions directly here:",
                value="Summarize the following text:\n\n${TRANSCRIPT}",
                lines=4
            )
            
            submit_btn = gr.Button("Execute Pipeline", variant="primary")
            status_tracker = gr.Markdown("### Status: Idle")
            
        with gr.Column():
            text_output = gr.Textbox(label="Preview Output Prompt", lines=14)
            file_output = gr.File(label="Download as Text File (.txt)")
            
    submit_btn.click(
        fn=process_pipeline,
        # Pass the new api_key_input component here
        inputs=[video_input, template_file_input, fallback_text_input, language_input, api_key_input],
        outputs=[status_tracker, text_output, file_output]
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
