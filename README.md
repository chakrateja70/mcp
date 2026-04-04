# MCP (Model Context Protocol) - Basic Example

This repository contains a **basic MCP implementation** with:

- An **MCP Server** (`server.py`) that exposes two tools:
  - `login_tool` → calls a local `/login` API
  - `query_tool` → calls a local `/query` API
- An **MCP Client** (`client.py`) that connects to the server over **stdio** and uses **Google Gemini** to decide when to call MCP tools.

---

## What is this project doing?

### Server (`server.py`)
The MCP server:
- Starts an MCP server named **"newrag"**
- Exposes two MCP tools:
  1. **login_tool(name, age)**
     - Sends `{ "name": ..., "age": ... }` to `http://localhost:8000/login`
  2. **query_tool(query)**
     - Sends `{ "query": ... }` to `http://localhost:8000/query`

The server also logs output to:
- Terminal (stderr)
- A file named `rag_server.log`

### Client (`client.py`)
The MCP client:
- Connects to the server script you provide (Python or Node)
- Reads your questions from the terminal
- Uses **Gemini** to decide if a tool should be used
- Calls the MCP tool and prints the tool result

It also supports a simple “missing parameters” flow:
- If Gemini decides a tool is needed but required inputs are missing,
  the client asks you to enter the missing values.

---

## Requirements

- Python **3.11+**
- A `.env` file with your Gemini key:

```env
GOOGLE_API_KEY=your_api_key_here
```

---

## Install

### Option 1: using `requirements.txt`
```bash
pip install -r requirements.txt
```

### Option 2: using `pyproject.toml`
If you are using `uv`:
```bash
uv sync
```

---

## Run the MCP server

In one terminal, run:

```bash
python server.py
```

> Note: This server expects your backend APIs to be running locally:
- `http://localhost:8000/login`
- `http://localhost:8000/query`

---

## Run the MCP client

In another terminal, run:

```bash
python client.py server.py
```

Then type queries like:

- `login`
- `sign in`
- `I want to login to Lomaa`
- `Tell me about Lomaa IT Solutions`
- `What is Lomaa?`

Type `quit` to exit.

---

## Project Files

- `server.py` → MCP server with `login_tool` and `query_tool`
- `client.py` → MCP client that uses Gemini + calls MCP tools
- `requirements.txt` → minimal dependencies
- `pyproject.toml` → project definition / dependencies

---

## Notes / Tips

- Make sure your local API server (port 8000) is running, otherwise the tools will fail.
- If `GOOGLE_API_KEY` is missing, the client will stop with an error.
