# ScreenSage

A local AI desktop assistant. Speak your problem, it screenshots your screen, and returns step-by-step guidance in a floating overlay — works for any app, any task.

![Python](https://img.shields.io/badge/python-3.10+-blue) ![PyQt6](https://img.shields.io/badge/UI-PyQt6-green) ![Gemini](https://img.shields.io/badge/LLM-Gemini%202.0%20Flash-orange)

---

## What it does

1. A floating pill bar sits at the bottom of your screen at all times
2. Click **▶ Start**, speak your problem, click **■ Stop**
3. ScreenSage screenshots your screen and sends it + your voice to Gemini
4. If it's not confident, it searches the web (Serper API) to verify steps
5. A result overlay appears with numbered, step-by-step guidance
6. Sessions are saved — resume any past conversation on next launch

**Works for anything on screen:** UI fixes, coding questions, app how-tos, terminal commands, design prompts, and more.

---

## Setup

```bash
git clone https://github.com/hatimanees/screensage
cd screensage

# Windows
./setup.bat
./run.bat

# Mac / Linux
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

On first launch, missing API keys are prompted in the terminal and saved to `.env` automatically.

---

## API Keys

| Key | Required | Where to get |
|-----|----------|-------------|
| `DEEPGRAM_API_KEY` | Yes | [console.deepgram.com](https://console.deepgram.com) |
| `GEMINI_API_KEY` | Yes | [aistudio.google.com](https://aistudio.google.com) |
| `SERPER_API_KEY` | Optional | [serper.dev](https://serper.dev) — 2,500 free searches/month |

`SERPER_API_KEY` is optional. Without it, ScreenSage answers from Gemini's own knowledge only.

---

## Features

- **Always-on floating bar** — stays visible across all apps, never steals focus
- **Collapse / expand** — shrinks to a mini pill when not in use
- **Agentic loop** — Gemini decides when to search the web; no hardcoded rules
- **Session history** — every conversation saved to `sessions/`; resume on next launch
- **Resizable overlay** — drag any edge or corner to resize; drag header to move
- **Copy output** — one-click copy of the full response
- **Text selection** — select any part of the response to copy manually
- **Delete recording** — press Delete mid-recording to cancel without any API calls

---

## Architecture

```
main.py  ←  CLI entry, config loader, session picker
└── QApplication
      ├── RecordingBar      ←  persistent floating pill (PyQt6)
      └── Agent (QObject)
            ├── AudioRecorder   ←  sounddevice
            ├── SessionWriter   ←  saves turns to sessions/*.json
            └── _Worker (QThread)
                  ├── DeepgramSTT    ←  transcribes WAV
                  └── GeminiLLM      ←  agentic loop with tool use
                        ├── web_search   (Serper API)
                        └── fetch_url    (stdlib urllib)
```

### Agentic loop

```
Gemini sees: system prompt + session history + transcript + live screenshot

while iterations < 6:
    if no tool calls → return answer
    execute web_search / fetch_url → append result
→ force final answer if max iterations hit
```

---

## Stack

| Component | Choice |
|-----------|--------|
| UI | PyQt6 — frameless, always-on-top, translucent |
| STT | Deepgram SDK v6 — nova-2 model |
| LLM | Gemini 2.5 Flash via `google-genai` — configurable in `assistant/config.yaml` |
| Web search | Serper API (optional) |
| Session storage | Local JSON files in `sessions/` |

---

## Project structure

```
screensage/
├── .env.example
├── setup.bat / setup.sh
├── run.bat / run.sh
└── assistant/
    ├── main.py
    ├── config.yaml
    ├── requirements.txt
    ├── core/
    │   ├── agent.py          ←  orchestrates STT + LLM + UI
    │   ├── session.py        ←  session persistence
    │   └── tool_executor.py  ←  routes LLM tool calls
    ├── providers/
    │   ├── stt/deepgram.py
    │   ├── llm/gemini.py     ←  agentic loop
    │   └── search/serper.py
    ├── capture/
    │   ├── screen.py         ←  mss screenshot
    │   └── audio.py          ←  sounddevice recorder
    └── ui/
        ├── recording_bar.py  ←  floating pill
        └── overlay.py        ←  result card
```

---

## Configuration

Edit `assistant/config.yaml` to change providers or models:

```yaml
llm: gemini

gemini:
  api_key: ${GEMINI_API_KEY}
  model: gemini-2.5-flash   # swap to gemini-2.0-flash, gemini-1.5-pro, etc.
```

Any Gemini model supported by the `google-genai` SDK works here.

---

## License

MIT
