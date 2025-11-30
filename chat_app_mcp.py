"""
Chat Application with MCP Tools

This application combines:
- Gradio for the chat UI
- LangChain agents for AI capabilities
- MCP server for tools via the Model Context Protocol (HTTP/SSE)

Run the MCP server first: python mcp_server.py
Then run this app: python chat_app_mcp.py
"""

import os
import asyncio
import threading
import gradio as gr
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import SecretStr, Field, create_model
from dotenv import load_dotenv

from mcp import ClientSession
from mcp.client.sse import sse_client

load_dotenv()

# MCP Server URL - change this if running on a different host/port
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")

# Set up environment variables
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    raise ValueError("OPENROUTER_API_KEY environment variable not set")

openrouter_base_url = os.getenv("OPENROUTER_BASE_URL")
if not openrouter_base_url:
    raise ValueError("OPENROUTER_BASE_URL environment variable not set")

# Initialize the LLM
llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0.7,
    api_key=SecretStr(openrouter_api_key),
    base_url=openrouter_base_url,
)

# Global MCP session (managed by background thread)
_mcp_session: ClientSession | None = None
_mcp_loop: asyncio.AbstractEventLoop | None = None
_dynamic_tools: list[StructuredTool] = []
_agent = None


def _run_in_mcp_loop(coro):
    """Run a coroutine in the MCP event loop."""
    if _mcp_loop is None:
        raise RuntimeError("MCP loop not initialized")
    future = asyncio.run_coroutine_threadsafe(coro, _mcp_loop)
    return future.result(timeout=30)


def create_dynamic_tool(tool_name: str, tool_description: str, input_schema: dict) -> StructuredTool:
    """
    Dynamically create a LangChain StructuredTool from MCP tool definition.
    """
    # Build Pydantic model from JSON schema
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    fields = {}
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "string")
        prop_desc = prop_info.get("description", "")
        default = ... if prop_name in required else None

        # Map JSON schema types to Python types
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
        }
        python_type = type_map.get(prop_type, str)
        fields[prop_name] = (python_type, Field(default=default, description=prop_desc))

    # Create dynamic Pydantic model for args
    ArgsModel = create_model(f"{tool_name}Args", **fields) if fields else None

    # Create the function that calls the MCP tool
    def call_mcp_tool(**kwargs) -> str:
        if _mcp_session is None:
            return "Error: MCP session not initialized"

        async def _call():
            result = await _mcp_session.call_tool(tool_name, arguments=kwargs)
            if result.content:
                # Extract text from content
                texts = []
                for c in result.content:
                    if hasattr(c, "text"):
                        texts.append(c.text)
                return "\n".join(texts) if texts else "No text result"
            return "No result returned"

        return _run_in_mcp_loop(_call())

    return StructuredTool(
        name=tool_name,
        description=tool_description,
        func=call_mcp_tool,
        args_schema=ArgsModel,
    )


async def load_tools_from_mcp(session: ClientSession) -> list[StructuredTool]:
    """Load all tools from the MCP server and convert to LangChain tools."""
    tools_response = await session.list_tools()
    tools = []

    for mcp_tool in tools_response.tools:
        lc_tool = create_dynamic_tool(
            tool_name=mcp_tool.name,
            tool_description=mcp_tool.description or f"Tool: {mcp_tool.name}",
            input_schema=mcp_tool.inputSchema if hasattr(mcp_tool, "inputSchema") else {},
        )
        tools.append(lc_tool)
        print(f"  - Loaded tool: {mcp_tool.name}")

    return tools

# System prompt template - will be populated with dynamic tools
SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant with access to tools via MCP (Model Context Protocol).

Available tools:
{tool_list}

When users ask questions that require these capabilities, use the appropriate tool.
After receiving a tool response, provide a helpful answer using that information.
Be friendly and conversational."""


def create_agent_with_tools(tools: list[StructuredTool]):
    """Create a LangChain agent with the given tools."""
    # Build tool list for system prompt
    tool_descriptions = []
    for i, tool in enumerate(tools, 1):
        tool_descriptions.append(f"{i}. **{tool.name}** - {tool.description.split(chr(10))[0]}")
    
    tool_list = "\n".join(tool_descriptions)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tool_list=tool_list)
    
    return create_agent(llm, tools, system_prompt=system_prompt)


def convert_history_to_messages(history: list) -> list:
    """Convert Gradio chat history to LangChain messages."""
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


def chat(message: str, history: list) -> str:
    """Process a chat message and return the agent's response."""
    if _agent is None:
        return "Error: Agent not initialized. Please wait for MCP connection."
    
    # Convert history to LangChain messages
    langchain_messages = convert_history_to_messages(history)

    # Add the current user message
    langchain_messages.append(HumanMessage(content=message))

    try:
        # Invoke the agent
        result = _agent.invoke({"messages": langchain_messages})  # type: ignore[arg-type]

        # Get the last AI message content
        response = result["messages"][-1].content
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"


# Create Gradio interface
def create_ui():
    # Build dynamic tool list (simpler format, no table)
    tool_list_items = []
    for tool in _dynamic_tools:
        # Get first line of description, clean up any problematic characters
        desc = tool.description.split("\n")[0] if tool.description else "No description"
        # Remove any pipe characters that could break markdown
        desc = desc.replace("|", "-").strip()
        tool_list_items.append(f"- **{tool.name}**: {desc}")
    
    tool_list_md = "\n".join(tool_list_items) if tool_list_items else "- No tools available"
    
    with gr.Blocks(title="AI Chat with MCP Tools") as demo:
        gr.Markdown(
            f"""
# Assistente de Biblioteca com MCP

Este assistente te ajuda a escolher sua próxima leitura. Você pode pedir sugestões de livros, autores ou navegar por gêneros.

Conectado: `{MCP_SERVER_URL}`

### Ferramentas Disponíveis ({len(_dynamic_tools)}):
{tool_list_md}
"""
        )

        chatbot = gr.Chatbot(
            height=450,
            show_label=False,
        )

        with gr.Row():
            msg = gr.Textbox(
                placeholder="Digite sua mensagem aqui... Tente: 'Me indique um bom livro sobre arquitetura de software para iniciantes.'",
                show_label=False,
                scale=9,
                container=False,
            )
            submit_btn = gr.Button("Send", scale=1, variant="primary")

        with gr.Row():
            clear_btn = gr.Button("🗑️ Clear Chat")

        # Handle message submission
        def respond(message: str, chat_history: list):
            if not message.strip():
                return "", chat_history

            bot_response = chat(message, chat_history)
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": bot_response})
            return "", chat_history

        # Connect events
        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        submit_btn.click(respond, [msg, chatbot], [msg, chatbot])
        clear_btn.click(lambda: [], outputs=[chatbot])

        gr.Markdown(
            """
        ---
        *Construído com LangChain, Gradio, e MCP (Model Context Protocol)*
        """
        )

    return demo


async def run_mcp_session():
    """Connect to the MCP server via SSE and keep the session alive."""
    global _mcp_session, _dynamic_tools, _agent

    print(f"Connecting to MCP server at {MCP_SERVER_URL}...")
    
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _mcp_session = session
            print("MCP session initialized!")

            # Dynamically load tools from the server
            print("Loading tools from MCP server...")
            _dynamic_tools = await load_tools_from_mcp(session)
            print(f"Loaded {len(_dynamic_tools)} tools from MCP server")

            # Create the agent with dynamic tools
            _agent = create_agent_with_tools(_dynamic_tools)
            print("Agent created with dynamic tools!")

            # Keep the session alive
            while True:
                await asyncio.sleep(1)


def start_mcp_thread():
    """Start the MCP client connection in a background thread."""
    global _mcp_loop

    def run_loop():
        global _mcp_loop
        _mcp_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_mcp_loop)
        try:
            _mcp_loop.run_until_complete(run_mcp_session())
        except Exception as e:
            print(f"MCP connection error: {e}")
            print(f"Make sure the MCP server is running at {MCP_SERVER_URL}")

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    # Wait for MCP session and agent to initialize
    import time
    for _ in range(60):  # Wait up to 30 seconds
        if _agent is not None:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError(
            f"Failed to connect to MCP server at {MCP_SERVER_URL}. "
            "Make sure the server is running with: python mcp_server.py"
        )


def main():
    """Main entry point."""
    print("=" * 50)
    print("AI Chat with MCP Tools")
    print("=" * 50)
    print(f"Connecting to MCP server at {MCP_SERVER_URL}...")
    start_mcp_thread()
    print("MCP session ready!")
    print("=" * 50)

    # Create and launch UI
    demo = create_ui()
    demo.launch()


if __name__ == "__main__":
    main()
