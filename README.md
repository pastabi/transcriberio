# Meet the greatest FREE video analyzer ever created - Transcriberio

A simple browser-based local automation utility to extract audio from video clips, transcribe it with blazing speed using Groq's cloud-hosted Whisper-large-v3, wrap it smoothly inside structural templates and run the output throught Gemini AI to get some tolerable analysis.

## Features

- any length video support
  (I am sure 3-4 hours will be ok, maybe even much more, but I haven't tested; the daily limit for audio transcription is stated as 8 hours, but I haven't reached this limit; the 2 hour hourly limit is stated, but I exceeded this limit without consequences)
- URL support (not only local files, but link on any video, youtube etc. will do)
- several AI fallback options, so if the main model is unavailable, you still can get the AI output
  (max 20 video a day with gemini 3.5 flash model, 20 more with weaker 3.0 flash and 500 more with bare minimum model 3.1 flash light)
- on every run you get an .mp3 file of your audio, .txt of transcript and .md of AI output

## Prerequisites

### 1. Ensure your system has Python 3, FFmpeg and Git installed.

#### On Linux Mint/Ubuntu:

```bash
sudo apt update && sudo apt install python3 python3-venv ffmpeg git -y
```

#### On Windows

```PowerShell
winget install Python.Python.3
winget install Gyan.FFmpeg
winget install Git.Git
```

### 2. Get the Groq API key

1. register on groq.com
2. go to API Keys section at the top menu,
3. create API key

- note: store it somewhere immediately, as Groq will not let you copy it again once you close the window

### 3. Get the Gemini (Google AI Studio) API key

1. register a Google account (if not already)
2. go to Google AI Studio and click "Get API key" in the bottom left corner
3. create API key

- note: you may not store it, as you can always copy it from here (at Groq you can't)

## Installation

### Complete command line installation on Linux Mint/Ubuntu

Open your terminal in the folder where you want the project to live.

```bash
git clone https://github.com/pastabi/transcriberio.git
cd transcriberio
chmod +x run.sh
./run.sh
```

It will automatically launch the dashboard in your browser.
Add the keys you got from Groq and Gemini to the app and you are all set.

### Complete command line installation on Windows

Open PowerShell in the folder where you want the project to live.

```PowerShell
git clone https://github.com/pastabi/transcriberio.git
cd transcriberio
.\run.bat
```

It will automatically launch the dashboard in your browser.
Add the keys you got from Groq and Gemini to the app and you are all set.

## Plans

- [x] 1. Add longer videos support (over 1:40 hours)
- [x] 2. Add fallback models for AI analysis, so it works even if primary one is unavailable in the moment
- [x] 3. Add video support via link (video will be downloaded with yt-dlp)
- [ ] 4. Create sufficient documentation and instructions
- [ ] 5. Add option to choose the model for the users with a paid plan
