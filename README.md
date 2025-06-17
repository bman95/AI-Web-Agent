# AI-Web-Agent

This project creates a chatbot-style interface that controls a Playwright browser using the [MCP (Model Context Protocol)](https://github.com/microsoft/playwright-mcp) server. It allows for automated web interactions like navigation, form-filling, clicking, and scraping using natural language commands.

## 🔧 Features

- Interactive chatbot loop with real-time streaming responses.
- Executes web automation tasks using Playwright via MCP.
- Short-term memory of last N turns for contextual understanding.
- Displays invoked tool calls for debugging and transparency.
- Written in Python, supports asynchronous execution.

## 🧠 Technologies Used

- Python 3.12+
- [Playwright MCP](https://www.npmjs.com/package/@playwright/mcp)
- OpenAI GPT-4.1
- `colorama` for colored CLI output
- Async/Await + streaming support for responsive CLI

## 🚀 Getting Started

### 1. Install Requirements

Make sure you have `npx` and Python 3.12+ installed.

Install Python dependencies:

```bash
pip install -r requirements.txt
````

### 1. Run the Chat Interface

```bash
python web_agent.py
```

Optional: specify memory size (number of user+assistant turns to remember):

```bash
python web_agent.py --mem 10
```

### 2. Using the Agent

Once running, you'll see a chatbot prompt. You can type commands like:

```
Go to LinkedIn and search for "Data Scientist at Google"
Click the first result
Take a screenshot of the page
```

### 3. Exiting the Agent

To stop the agent, type:

```
exit
```

## 📁 Project Structure

```
.
├── web_agent.py         # Main CLI entrypoint
├── instructions.md      # Behavior instructions for the Agent
├── requirements.txt     # Python dependencies
└── README.md            # You're here!
```

## 📌 Notes

* The agent assumes it is running in a browser where you are already logged into relevant sites.
* This is ideal for automating tasks across authenticated pages like LinkedIn, Gmail, etc.
* Responses are streamed in real-time and actions are transparent via CLI logs.

## 🧪 Example Commands

```text
Search for "Machine Learning jobs" on LinkedIn.
Apply filter "Remote".
Click on the third result and extract the job description.
```

## 🛠️ Troubleshooting

If you see an error like `npx is not installed`, make sure Node.js and `npx` are properly set up:

```bash
npm install -g npx
```

---

Happy automating! 🤖
