def fill_template(transcript, template_file, system_prompt_fallback):
    template_content = ""
    # reading the template file, if such is provided
    if template_file is not None:
        try:
            with open(template_file.name, "r", encoding="utf-8") as f:
                template_content = f.read()
        except Exception as e:
            raise IOError(f"Could not load template text from file: {str(e)}")
    else:
        template_content = system_prompt_fallback

    placeholder = "${TRANSCRIPT}"
    # just replacing the placeholder with the transcript, or adding the transcript at the end, that's it
    if placeholder in template_content:
        formatted_final_prompt = template_content.replace(
            placeholder, transcript.strip()
        )
    else:
        formatted_final_prompt = f"{template_content.strip()}\n\n{transcript.strip()}"

    return formatted_final_prompt
