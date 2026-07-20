import os
import time

import gradio as gr

from src.utils.utils import append_timestamp, cleanup_temp_dirs

CSS = """
/* ---------- */
/* class to dim the unchecked steps */
.dimmed {
    opacity: 0.3 !important;
    pointer-events: none !important;
    user-select: none !important;
    transition: opacity 0.3s ease;
}
/* ---------- */

/* ---------- */
/* Making the final files placehorders (before the files are there) small */
.short_file {
    max-height: 60px !important;
}

.short_file .large, 
.short_file .empty, 
.short_file [aria-label="Empty value"] {
    max-height: 60px !important;
    height: 60px !important;
}
.short_file .icon {
    display: none;
}
/* ---------- */

/* ---------- */
/* making the checkboxes just inline checkboxes, without texts, backgrounds, stretching etc */
.minimal-cb {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    
    min-width: 16px !important; 
    width: 16px !important;
    
    flex: 0 0 16px !important; 
    padding: 0 !important;
    margin-top: 2px !important;
}

.minimal-cb label {
    padding: 0 !important;
}
/* ---------- */

/* ---------- */
/* fixing the bug with inputs flickering with controls when dimmed/undimmed */
.anti-blick {
    overflow: hidden !important;
}
/* ---------- */

/* ---------- */
/* making the controls color correspond to the theme*/
body.dark, .dark {
    color-scheme: dark !important;
}
/* ---------- */
"""

# 1. Programmatically inject the CSS into the document head
# 2. Start the heartbeat polling for the background server
# (The browser will ping the server every 5 seconds, but browsers throttle background tabs, so this might drop to 1 ping/minute if the user switches tabs. We account for this in the main.py logic, allowing 120 seconds buffer time)
# We use standard string formatting (%s) because f-strings will crash when they see CSS curly brackets
custom_js = """
function() {
    var css = `%s`;
    var style = document.createElement('style');
    style.appendChild(document.createTextNode(css));
    document.head.appendChild(style);

    setInterval(function() {
        fetch('/heartbeat').catch(() => {});
    }, 5000);
}
""" % CSS.replace("`", "\\`")  # This escapes any possibe stray backticks in my CSS


# function that returns our ui (that we use to start browser in main.py)
def create_ui(pipeline_callback, temp_dirs, pipeline_active):
    # getting from .env our stored keys and model name from previous run (if present)
    initial_groq = os.getenv("GROQ_API_KEY", "")
    initial_gemini = os.getenv("GEMINI_API_KEY", "")
    initial_model = os.getenv("GEMINI_MODEL", "")

    # function to create the label for keys area based on field inputs
    def get_keys_label(groq, gemini, model_name):
        g_stat = "key present" if groq and groq.strip() else "no key"
        gem_stat = "key present" if gemini and gemini.strip() else "no key"
        model = f", model - {model_name}" if model_name else ""
        return f"(Groq - {g_stat}, Gemini - {gem_stat}{model})"

    # the function that uses gradio to create our ui
    with gr.Blocks(title="Transcriberio") as app:

        # triggers our css and js ping code attachment to the html after the block renders
        app.load(js=custom_js)

        gr.Markdown("# AI Video Analyzer Pipeline")

        with gr.Row():
            with gr.Column():

                # --- SECTIONS ---
                # --- 1. API KEYS ---
                # if we have groq key for audio transcription, we keep this section closed to not take space
                is_open_by_default = not bool(initial_groq)

                gr.Markdown("### 1. API Keys")
                # creating accordion, to save the space - if we have our keys, we don't need to look at them
                with gr.Accordion(
                    # dynamically creating label, based on the loaded info
                    label=get_keys_label(initial_groq, initial_gemini, initial_model),
                    open=is_open_by_default,
                ) as keys_accordion:
                    gr.Markdown("Keys will auto-fill after your first run.")
                    groq_key_input = gr.Textbox(
                        label="Groq API Key (For Audio)",
                        type="password",
                        value=initial_groq,
                    )
                    gemini_key_input = gr.Textbox(
                        label="Gemini API Key (For Text Analysis)",
                        type="password",
                        value=initial_gemini,
                    )
                    model_input = gr.Textbox(
                        label="Model name (only if you have the paid plan, and want to use some other model)",
                        placeholder="you would need to enter the exact model name, e.g. gemini-3.5-flash",
                        value=initial_model,
                    )

                gr.Markdown("---")

                # --- 2. VIDEO UPLOAD ---
                gr.Markdown("### 2. Upload video")

                video_url = gr.Textbox(
                    label="Use Video From URL (audio from this link will be downloaded after you start the pipeline)",
                    placeholder="If you attach video file below, URL here will be ignored",
                    max_lines=1,
                )

                # having the language chooser in the same line as the video, so the video element doesn't take as much space
                with gr.Row(equal_height=False):
                    video_input = gr.Video(
                        label="Choose Video File", scale=2, min_width=200
                    )
                    language_input = gr.Dropdown(
                        choices=[
                            "Auto-Detect",
                            "Ukrainian",
                            "Russian",
                            "English",
                            "Polish",
                        ],
                        value="Auto-Detect",
                        label="Force Transcription Language",
                        scale=1,
                        min_width=120,
                    )

                gr.Markdown("---")

                # --- 3. TEMPLATE TOGGLE & AUTO-FILL ---
                with gr.Row(equal_height=True):
                    use_template_cb = gr.Checkbox(
                        show_label=False,
                        value=True,
                        container=False,
                        elem_classes=["minimal-cb"],
                    )

                    template_title = gr.Markdown(
                        "### 3. AI Instructions Template", elem_classes=["anti-blick"]
                    )

                with gr.Column() as template_content:
                    template_file_input = gr.File(
                        label="Upload a .txt template file",
                        file_types=[".txt"],
                        height=150,
                    )
                    fallback_text_input = gr.Textbox(
                        label="Or write instructions directly here (auto-fills on file upload):",
                        value="You are a helpful assistant. Please summarize the following video transcript:\n\n(Take into account that this is an automatic transcription, so some inconsistencies or loss of meaning may occur due to incorrect word interpretations.)\n${TRANSCRIPT}",
                        lines=8,
                        max_lines=8,
                    )

                gr.Markdown("---")

                # --- 4. AI TOGGLE ---
                with gr.Row(equal_height=True):
                    use_ai_cb = gr.Checkbox(
                        show_label=False,
                        value=True,
                        container=False,
                        elem_classes=["minimal-cb"],
                    )
                    ai_title = gr.Markdown(
                        "### 4. Perform AI Analysis", elem_classes=["anti-blick"]
                    )

                # --- BUTTONS ---
                with gr.Row():
                    # disabled by default until a video is uploaded (and keys are present)
                    submit_btn = gr.Button(
                        "Run Full Pipeline", variant="primary", interactive=False
                    )
                    # will be swapped with Run when Run will be clicked, by default is not visible
                    cancel_btn = gr.Button(
                        "Stop / Cancel", variant="stop", visible=False
                    )

            with gr.Column():
                gr.Markdown("### Status")
                status_tracker = gr.TextArea(
                    show_label=False,
                    value="Idle",
                    lines=5,
                    max_lines=5,
                    container=False,
                    elem_id="status-log-area",
                )
                gr.Markdown("### 5. Results")
                gr.Markdown("##### 5.1 Text outputs")

                prompt_output = gr.Textbox(
                    label="The Prompt With Transcript", lines=8, max_lines=8
                )
                ai_output = gr.Textbox(
                    label="Final Result: AI Response", lines=10, max_lines=10
                )

                gr.Markdown("##### 5.2 File outputs")

                audio_file_output = gr.File(
                    label="📥 Download audio (.mp3)",
                    elem_classes=["short_file"],
                )
                transcription_file_output = gr.File(
                    label="📥 Download transcript (.txt)",
                    elem_classes=["short_file"],
                )
                ai_file_output = gr.File(
                    label="📥 Download AI Response (.md)",
                    elem_classes=["short_file"],
                )

        # ==========================================
        # EVENT LISTENERS & LOGIC
        # ==========================================

        # 1. Update Accordion Title dynamically as user types their keys
        # the function that makes some ui updates
        # the inputs are determined by the "inputs" argument of the listener
        def update_accordion_title(groq, gemini, model_name):
            # in which element exactly this specific UI update will happen the "outputs" argument of the listener determines
            return gr.update(label=get_keys_label(groq, gemini, model_name))

        # the event listener itself
        groq_key_input.change(
            update_accordion_title,
            inputs=[groq_key_input, gemini_key_input, model_input],
            outputs=keys_accordion,
        )
        gemini_key_input.change(
            update_accordion_title,
            inputs=[groq_key_input, gemini_key_input, model_input],
            outputs=keys_accordion,
        )
        model_input.change(
            update_accordion_title,
            inputs=[groq_key_input, gemini_key_input, model_input],
            outputs=keys_accordion,
        )

        # 2. Smart Disable/Enable for the Run Button
        # based on required states determines if Run button should be clickable
        def validate_inputs(video, url, groq, gemini, ai_enabled):
            # Check 1: Must have a video
            if not video and not url:
                return gr.update(interactive=False)
            # Check 2: Must have Groq key (always needed for audio)
            if not groq.strip():
                return gr.update(interactive=False)
            # Check 3: If AI is toggled ON, must have Gemini key
            if ai_enabled and not gemini.strip():
                return gr.update(interactive=False)

            # If we pass all checks, enable the button
            return gr.update(interactive=True)

        inputs_to_watch = [
            video_input,
            video_url,
            groq_key_input,
            gemini_key_input,
            use_ai_cb,
        ]

        # Attach the validation to anytime these inputs change
        for component in inputs_to_watch:
            component.change(
                validate_inputs, inputs=inputs_to_watch, outputs=submit_btn
            )
        # Videos also trigger .upload and .clear, so we bind those too
        video_input.upload(validate_inputs, inputs=inputs_to_watch, outputs=submit_btn)
        video_input.clear(validate_inputs, inputs=inputs_to_watch, outputs=submit_btn)

        # 3. Auto-fill Textbox from .txt file upload
        def read_file_content(file_obj):
            if file_obj is None:
                return gr.update()  # Do nothing if file is cleared
            try:
                with open(file_obj.name, "r", encoding="utf-8") as f:
                    # Rerender the textbox with the text from the file
                    return gr.update(value=f.read())
            except Exception as e:
                return gr.update(value=f"Error reading file: {str(e)}")

        template_file_input.upload(
            read_file_content, inputs=template_file_input, outputs=fallback_text_input
        )

        # 4. Dimmen and disable the turned off sections
        def handle_template_toggle(is_enabled):
            # Apply our CSS dimmen class if disabled, but don't forget about "anti-blick"
            classes = ["anti-blick"] if is_enabled else ["dimmed", "anti-blick"]

            # Switch the label string
            prompt_label = "The Prompt With Transcript" if is_enabled else "Transcript"

            # Cascade disable AI: If template turns off, force AI off. If template turns on, do nothing.
            cascade_ai = gr.update(value=False) if not is_enabled else gr.update()

            # number of outputs should be the same as number of elements in "outputs" argument of listener
            return (
                gr.update(elem_classes=classes),  # Dims the title markdown
                gr.update(elem_classes=classes),  # Dims the file/textbox content
                gr.update(label=prompt_label),  # Updates the output label
                cascade_ai,  # Triggers the AI checkbox
            )

        use_template_cb.change(
            handle_template_toggle,
            inputs=[use_template_cb],
            outputs=[template_title, template_content, prompt_output, use_ai_cb],
        )

        def handle_ai_toggle(is_enabled):
            classes = ["anti-blick"] if is_enabled else ["dimmed", "anti-blick"]

            return (
                gr.update(elem_classes=classes),  # Dims the AI title markdown
                gr.update(visible=is_enabled),  # Completely hides the AI Textbox
                gr.update(
                    visible=is_enabled
                ),  # Completely hides the AI file download area
            )

        use_ai_cb.change(
            handle_ai_toggle,
            inputs=[use_ai_cb],
            outputs=[ai_title, ai_output, ai_file_output],
        )

        # 5. Scroll status area when overflow
        # Create a raw JavaScript function as a string to insert it into the element to run in dom
        scroll_js = """
        function() {
            const textarea = document.querySelector('#status-log-area textarea');
            if (textarea) {
                textarea.scrollTop = textarea.scrollHeight;
            }
        }
        """
        # Fire this JS every time the text in status_tracker updates
        status_tracker.change(fn=None, inputs=None, outputs=None, js=scroll_js)

        # 6. Pipeline Execution & Cancellation Logic
        # Helper function to swap button visibility
        def swap_buttons(show_submit):
            return gr.update(visible=show_submit), gr.update(visible=not show_submit)

        # Step A: When clicked, instantly hide Submit and show Cancel
        start_run = submit_btn.click(
            fn=lambda: swap_buttons(show_submit=False), outputs=[submit_btn, cancel_btn]
        )

        # Step B: Trigger the actual pipeline
        # "outputs" will receive data from all these yields we had in our pipeline
        run_event = start_run.then(
            fn=pipeline_callback,
            inputs=[
                video_input,
                video_url,
                template_file_input,
                fallback_text_input,
                language_input,
                groq_key_input,
                gemini_key_input,
                model_input,
                use_template_cb,
                use_ai_cb,
            ],
            outputs=[
                status_tracker,
                prompt_output,
                ai_output,
                audio_file_output,
                transcription_file_output,
                ai_file_output,
            ],
        )

        # Step C: If the pipeline finishes naturally, swap the buttons back
        run_event.then(
            fn=lambda: swap_buttons(show_submit=True), outputs=[submit_btn, cancel_btn]
        )

        # Step D: If Cancel is clicked, swap buttons back AND initiate the pipeline stop (kill the run_event)
        start_cancel = cancel_btn.click(
            fn=lambda: swap_buttons(show_submit=True),
            outputs=[submit_btn, cancel_btn],
            cancels=[run_event],
        )

        # Step E: Wait untill all running processes end and run a cleanup function
        def cancel_cleanup(status_tracker):
            # Updataing the status to indicate that cancellation has started
            status_tracker += f"\n{append_timestamp("⛔ Pipeline cancel initiated...")}"
            yield gr.update(value=status_tracker), gr.update()

            # If the pipeline is still grinding through a blocking process, wait for it
            if pipeline_active.is_set():
                status_tracker += f"\n{append_timestamp("⏳ Waiting for background processes to halt...")}"

                yield gr.update(value=status_tracker), gr.update(interactive=False)

            # Block the cleanup until pipeline_active.clear() is called
            while pipeline_active.is_set():
                time.sleep(0.5)

            # Now that the background processes are completely dead, execute the wipe
            cleanup_temp_dirs(temp_dirs)
            status_tracker += f"\n{append_timestamp("ℹ️ Pipeline stopped successfully. Cleanup finished.")}"
            yield gr.update(value=status_tracker), gr.update(interactive=True)

        start_cancel.then(
            fn=cancel_cleanup,
            inputs=status_tracker,
            outputs=[status_tracker, submit_btn],
        )

    return app
