# Start here: set up Techno-Heresy on your computer

You do not need to know how to code. Plan on installing two things, then downloading three sets of game data. Nothing in this package downloads or shares the game data for you.

## 1. Download the project from GitHub

On the project's GitHub page, choose **Code → Download ZIP**. Extract the downloaded file with your computer's **Extract All** or **Uncompress** option. Put the extracted project folder somewhere easy to find, such as Documents, and leave its files together. You can open every `.md` guide in a text editor or in Codex.

## 2. Install Python

Get the current stable Python 3 installer from [python.org/downloads](https://www.python.org/downloads/). Follow the installer for your computer. On Windows, if it offers **Add Python to PATH**, select it. Close and reopen your terminal after installation.

To check it worked, open **PowerShell** from the Windows Start menu, **Terminal** from macOS Spotlight, or your Linux Terminal app, and enter:

```text
python --version
```

If Windows says `python` is unknown, try `py --version`. If macOS/Linux says it is unknown, try `python3 --version`. You need Python 3.10 or newer. If none of those works, return to the Python installer before continuing.

## 3. Get an AI assistant that can use your local folder

**Easiest verified route: Codex in the ChatGPT desktop app.** Create a [ChatGPT account](https://chatgpt.com/) if you do not have one. Then follow the [official ChatGPT desktop quickstart](https://learn.chatgpt.com/docs/quickstart): download the app for your operating system, sign in, choose **Codex**, and open the extracted project folder as a local project. You do not need an OpenAI API key for this guide.

If you use another AI assistant, it needs permission to read the extracted folder and run Python commands on your computer. A chat window that only accepts pasted text cannot install or run the local search tool. You can still ask it to explain these steps, but use a local-capable assistant for the setup and skills.

## 4. Download the rules and points yourself

Follow [DATA_SETUP.md](DATA_SETUP.md). It links to:

1. Official Core Rules and Universal Rules Updates PDFs.
2. BSData's community catalogue JSON files.
3. BSData's community Munitorum YAML files, with the official Munitorum for comparison.

The guide shows exactly which `data/` folders to put them in. Create folders that are missing. Keep the downloaded files on your computer.

## 5. Ask the assistant to finish setup

With the extracted project folder open in Codex or another local-capable assistant, copy and send this message:

> Read `SETUP_WITH_AI.md` in this project and complete its local setup checklist. I have placed my own rules PDFs, BSData catalogue JSON, and Munitorum YAML in `data/`. Install the Python dependency, process the PDFs locally, build and test the search index, then confirm the two skills are discoverable. Do not download or upload game data.

The assistant should run the setup check and report any missing file with its destination. If your assistant cannot access local files or run commands, use the manual commands in [DATA_SETUP.md](DATA_SETUP.md).

## 6. Ask your first question

After setup succeeds, try:

> Use the warhammer-40k-rules skill: what are the points for Necron Warriors in my installed data? Show the source and its date.

Or:

> Use the warhammer-40k-army-list skill to build a 1,000 point Necrons army from my installed data. State anything you could not verify.

The skills use the files you installed. To update later, replace those files with newer copies and ask the assistant to run the setup check again.
