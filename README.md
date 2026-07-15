# Meet the greatest FREE video analyzer ever created - Transcriberio

A simple browser-based local automation utility to extract audio from video clips, transcribe it with blazing speed using Groq's cloud-hosted Whisper-large-v3, wrap it smoothly inside structural templates and run the output throught Gemini AI to get some tolerable analysis.

## Prerequisites

1. Ensure your system has Python 3 and FFmpeg installed.

### On Linux Mint/Ubuntu:

```bash
sudo apt update && sudo apt install python3 python3-venv ffmpeg -y
```

### On Windows

```PowerShell
winget install Python.Python.3
winget install Gyan.FFmpeg
```

2. Get the Groq API key

- register on groq.com
- go to API Keys section at the top menu,
- create API key
- store it somewhere

3. Get the Gemini (Google AI Studio) API key

- register a Google account (if not already)
- go to "Get API key" in the bottom left corner
- create API key
- you may not store it, as you can always copy it from here (at Groq you can't)

## Installation

1. Go to the folder you want this tool to live in
2. Download files from Github

```bash
git clone https://github.com/pastabi/transcriberio.git
```

3. Run the starting script

```bash
cd transcriberio
./run.sh
```

4. Add the keys you got from Groq and Gemini to the app

5. You are all set

## Plans

- [x] 1. Add longer videos support (over 1:40 hours)
- [ ] 2. Add automatic Gemini model switch (to newer available versions or if some is unavailable right now)
- [ ] 3. Add video support via link (video will be downloaded with yt-dlp)
- [ ] 4. Create sufficient documentation and instructions
