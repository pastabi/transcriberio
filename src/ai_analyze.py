from pathlib import Path

from google import genai


def analyze_text(formatted_final_prompt, gemini_key, ai_txt_output_path):
    try:
        gemini_client = genai.Client(api_key=gemini_key.strip())
        ai_response = gemini_client.models.generate_content(
            model="gemini-3.5-flash",
            contents=formatted_final_prompt,
        )
        final_ai_text = ai_response.text
    except Exception as e:
        raise RuntimeError(f"Gemini API failed to generate text: {str(e)}")

    try:
        Path(ai_txt_output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(ai_txt_output_path, "w", encoding="utf-8") as out_file:
            out_file.write(final_ai_text)
    except Exception as e:
        raise IOError(f"Could not save the AI response to file: {str(e)}")

    return final_ai_text
