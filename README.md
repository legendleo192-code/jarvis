# JARVIS AI Assistant

An advanced terminal-based JARVIS that uses OpenRouter models as its AI brain and can follow natural-language commands in Hinglish, Hindi, or English.

## Features

- OpenRouter chat brain with any supported model.
- Interactive and one-shot command modes.
- Tool loop for real work: shell commands, file reading/writing, directory listing, time lookup, and persistent memory.
- Safety gate before shell/file-write actions, with optional auto-approve mode for trusted environments.
- Persistent memory stored locally so JARVIS can remember preferences and project facts.
- No third-party Python dependencies; works with Python 3.10+.

## Setup

```bash
export OPENROUTER_API_KEY="your_openrouter_key"
python -m jarvis_ai --model openrouter/auto
```

Optional environment variables:

```bash
export OPENROUTER_MODEL="openrouter/auto"
export JARVIS_AUTO_APPROVE="0"          # set 1 to skip approvals
export JARVIS_WORKSPACE="$PWD"          # commands are limited to this directory by default
export JARVIS_MEMORY_FILE="$HOME/.jarvis/memory.json"
```

## Usage

Interactive mode:

```bash
python -m jarvis_ai
```

One-shot mode:

```bash
python -m jarvis_ai --once "mere project ka structure check karo aur batao kya hai"
```

Trusted automation mode:

```bash
python -m jarvis_ai --auto-approve --once "README me setup instructions improve karo"
```

## Safety notes

By default JARVIS asks before running shell commands or writing files. Keep that enabled when using powerful models on your main machine. Auto-approve is useful inside a disposable VM or a controlled project folder.

## Development

Run tests:

```bash
python -m unittest discover -s tests
```
