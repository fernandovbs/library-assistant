# Library Assistant

A conversational AI assistant that helps users discover books using the Open Library API. Built with LangChain, Gradio, and the Model Context Protocol (MCP).

## Features

- **Book Search**: Search for books by title, author, or keywords
- **Author Search**: Find authors and explore their works
- **Subject Browsing**: Browse books by genre/subject (fantasy, romance, mystery, etc.)
- **Book Recommendations**: Get personalized book recommendations based on interests
- **Conversational Interface**: Natural language chat interface powered by GPT-4o-mini

## Technologies Used

| Technology | Purpose |
|------------|---------|
| **Python** | Programming language |
| **Gradio** | Chat UI framework |
| **LangChain** | AI agent framework |
| **MCP (Model Context Protocol)** | Tool communication protocol |
| **FastMCP** | MCP server implementation |
| **OpenRouter** | LLM API provider |
| **Open Library API** | Book data source |
| **httpx** | HTTP client for API requests |

## Prerequisites

- Python 3.10 or higher
- An [OpenRouter](https://openrouter.ai/) API key

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/fernandovbs/library-assistant.git
   cd library-assistant
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:

   Copy the example environment file and add your API key:

   ```bash
   cp example.env .env
   ```

   Edit `.env` and set your OpenRouter API key:

   ```
   OPENROUTER_API_KEY=your_api_key_here
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   ```

## Running the Application

The application consists of two components that need to be run in separate terminals:

### 1. Start the MCP Server

In the first terminal:

```bash
python mcp_server.py
```

The server will start at `http://localhost:8000` with the SSE endpoint at `http://localhost:8000/sse`.

### 2. Start the Chat Application

In a second terminal:

```bash
python chat_app_mcp.py
```

The Gradio interface will open in your browser (typically at `http://127.0.0.1:7860`).

## Usage

Once both servers are running, you can interact with the assistant through the chat interface. Try questions like:

- "Recommend me a good science fiction book"
- "Search for books by Isaac Asimov"
- "Show me popular mystery novels"
- "Find books about artificial intelligence"
- "What are the top fantasy books?"

## Available Tools

The MCP server exposes the following tools:

| Tool | Description |
|------|-------------|
| `search_books` | Search for books by title, author, or keywords |
| `search_authors` | Search for authors and see their works |
| `browse_subject` | Browse books by subject/genre |
| `get_author_works` | Get all works by a specific author using their Open Library ID |
| `recommend_books` | Get book recommendations based on interests |

## Project Structure

```
library-assistant/
├── chat_app_mcp.py    # Gradio chat application with LangChain agent
├── mcp_server.py      # MCP server with Open Library tools
├── requirements.txt   # Python dependencies
├── example.env        # Example environment variables
├── .env               # Your environment variables (not in git)
└── README.md          # This file
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | Required |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `MCP_SERVER_URL` | MCP server SSE endpoint | `http://localhost:8000/sse` |

## License

This project uses the [Open Library API](https://openlibrary.org/developers/api) for book data.

## Acknowledgments

- [Open Library](https://openlibrary.org/) for providing free book data
- [LangChain](https://langchain.com/) for the AI agent framework
- [Gradio](https://gradio.app/) for the chat interface
- [Model Context Protocol](https://modelcontextprotocol.io/) for tool communication
