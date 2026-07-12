import os

import gradio as gr


def create_ui(pipeline_callback):
    with gr.Blocks(title="Transcriberio") as app:
        gr.Markdown("# AI Video Analyzer Pipeline")

        with gr.Row():
            with gr.Column():

                gr.Markdown("### 1. API Keys (Will auto-fill after first run)")
                groq_key_input = gr.Textbox(
                    label="Groq API Key (For Audio)",
                    type="password",
                    value=os.getenv("GROQ_API_KEY", ""),
                )
                gemini_key_input = gr.Textbox(
                    label="Gemini API Key (For Text Analysis)",
                    type="password",
                    value=os.getenv("GEMINI_API_KEY", ""),
                )

                gr.Markdown("---")

                gr.Markdown("### 2. Upload video")
                with gr.Row(equal_height=False):
                    video_input = gr.Video(
                        label="Choose Video File", scale=2, min_width=200
                    )
                    language_input = gr.Dropdown(
                        choices=[
                            "Auto-Detect",
                            "Ukrainian",
                            "English",
                            "Russian",
                            "Polish",
                        ],
                        value="Auto-Detect",
                        label="Force Transcription Language",
                        scale=1,
                        min_width=120,
                    )

                gr.Markdown("---")

                gr.Markdown("### 3. AI Instructions Template")
                template_file_input = gr.UploadButton(
                    label="Attach .txt template file",
                    file_types=[".txt"],
                    variant="secondary",
                )
                fallback_text_input = gr.Textbox(
                    label="Or write instructions directly here:",
                    value="You are a helpful assistant. Please summarize the following video transcript in 3 bullet points:\n\n(Take into account this is automatic transcript, so some inconsistencies or meaning loses may occur because of wrong words interpretations)\n${TRANSCRIPT}",
                    lines=6,
                )

                submit_btn = gr.Button("Run Full Pipeline", variant="primary")
                status_tracker = gr.Markdown("### Status: Idle")

            with gr.Column():
                gr.Markdown("### 4. Results")
                prompt_output = gr.Textbox(
                    label="Intermediate Step: The Prompt Sent to AI", lines=8
                )
                ai_output = gr.Textbox(label="Final Result: AI Response", lines=12)
                file_output = gr.File(label="Download AI Response (.txt)")

        submit_btn.click(
            fn=pipeline_callback,
            inputs=[
                video_input,
                template_file_input,
                fallback_text_input,
                language_input,
                groq_key_input,
                gemini_key_input,
            ],
            outputs=[status_tracker, prompt_output, ai_output, file_output],
        )

    return app
