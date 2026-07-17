from pathlib import Path

from google import genai


def analyze_text(formatted_final_prompt, gemini_key, model_name, ai_txt_output_path):
    # initializing our gemini client
    gemini_client = genai.Client(api_key=gemini_key.strip())

    # here we determine, do we use user provided model or the set of free models
    # we have set of free models, so if the first one is unavailable, we still get some analysis of our transcript and not just the error
    model_waterfall = (
        [model_name]
        if model_name
        else [
            "gemini-3.5-flash",  # The primary fast model
            "gemini-3-flash-preview",  # The stable free-tier workhorse
            "gemini-3.1-flash-lite",  # The ultra-lightweight backup
        ]
    )

    final_ai_text = None
    last_error = None
    # storing names of the models which were tried to be used or a model which was used, to indicate them in the UI
    used_models = []

    for model_name in model_waterfall:
        try:
            # Attempt the generation with the current model in the loop
            used_models.append(model_name)
            ai_response = gemini_client.models.generate_content(
                model=model_name,
                contents=formatted_final_prompt,
            )
            final_ai_text = ai_response.text
            break  # if success, we break out of the fallback loop

        except Exception as e:
            error_msg = str(e).lower()
            last_error = str(e)

            # 2. Check if the error is a rate limit (429), quota, or server overload (503)
            # if it is, it means that model is just unavailable, so we can try the next one in the list,
            # if no, it is a critical error (like an invalid API key), so we crash immediately
            if (
                "429" in error_msg
                or "503" in error_msg
                or "quota" in error_msg
                or "overloaded" in error_msg
            ):
                continue
            else:
                raise RuntimeError(
                    f"Gemini API failed with a critical error: {last_error}"
                )

    # 3. If the loop finishes and we still don't have text, it means every model failed
    # if the user provided it's own model, we give a little bit different error text
    if model_name and final_ai_text is None:
        raise RuntimeError(f"Provided model failed. Error: {last_error}")
    elif final_ai_text is None:
        raise RuntimeError(
            f"All fallback models failed due to high demand or rate limits. Last error: {last_error}"
        )

    # storing the responce text to the file
    try:
        Path(ai_txt_output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(ai_txt_output_path, "w", encoding="utf-8") as out_file:
            out_file.write(final_ai_text)
    except Exception as e:
        raise IOError(f"Could not save the AI response to file: {str(e)}")

    return final_ai_text, used_models
