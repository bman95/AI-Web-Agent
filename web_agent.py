import argparse
import asyncio
import shutil
from collections import deque
from typing import Deque, Dict, Any, List

from colorama import Fore, Style, init as colorama_init
from openai.types.responses import ResponseTextDeltaEvent

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerStdio

# ────────────────────────────── Inicialización ────────────────────────────── #
colorama_init(autoreset=True)

with open("instructions.md", "r", encoding="utf-8") as f:
    instructions = f.read()

# ──────────────────────────────── Colores CLI ─────────────────────────────── │
USER_PROMPT_COLOR = Fore.GREEN + Style.BRIGHT
ASSISTANT_PREFIX_COLOR = Fore.BLUE + Style.BRIGHT
SYSTEM_MSG_COLOR = Fore.YELLOW + Style.BRIGHT
TOOL_COLOR = Fore.MAGENTA + Style.BRIGHT
RESET = Style.RESET_ALL


# ─────────────────────────── Utilidades de Depuración ─────────────────────── #
async def display_tool_calls(result: Any) -> None:
    """Muestra en pantalla cada llamada a herramienta capturada en el resultado (al final)."""
    calls: List[Any] = []

    # LangChain-style
    if hasattr(result, "tool_calls") and result.tool_calls:
        calls = result.tool_calls
    # Otros frameworks (por ejemplo, lista de pares action/observation)
    elif hasattr(result, "intermediate_steps") and result.intermediate_steps:
        calls = [
            step[0] if isinstance(step, (list, tuple)) and step else step
            for step in result.intermediate_steps
        ]

    if not calls:
        return

    print(
        f"{TOOL_COLOR}\n🔧 ─── Herramientas invocadas ───────────────────────────{RESET}"
    )
    for call in calls:
        try:
            name = getattr(call, "tool", getattr(call, "name", str(call)))
            args = getattr(call, "tool_input", getattr(call, "args", {}))
        except Exception:
            name, args = str(call), {}
        print(f"{TOOL_COLOR}🛠️ [TOOL]{RESET} {name} → {args}")
    print(
        f"{TOOL_COLOR}──────────────────────────────────────────────────────{RESET}\n"
    )


# ────────────────────────────────── Chat loop ───────────────────────────────── #
async def chat_loop(mcp_server: MCPServerStdio, mem_size: int = 5) -> None:
    """
    Bucle interactivo estilo chatbot con memoria de corto plazo.

    El agente controla un navegador Playwright a través del MCP server.
    Las respuestas del asistente se emiten token-a-token en tiempo real.
    Muestra el nombre (y argumentos) de cada herramienta invocada, pero no su salida.
    """
    agent = Agent(
        name="Web Agent",
        instructions=instructions,
        model="gpt-4.1",
        mcp_servers=[mcp_server],
    )

    # Dos mensajes por turno (user + assistant)
    history: Deque[Dict[str, str]] = deque(maxlen=mem_size * 2)

    loop = asyncio.get_running_loop()
    print(f"{SYSTEM_MSG_COLOR}🚀 Chatbot iniciado. Memoria: {mem_size} turnos.{RESET}")
    print(
        f"{SYSTEM_MSG_COLOR}✏️ Escribe tu consulta (salir/exit/quit para terminar){RESET}\n"
    )

    while True:
        user_input: str = await loop.run_in_executor(
            None, input, f"{USER_PROMPT_COLOR}👤 Tú:{RESET} "
        )

        if user_input.strip().lower() in {"salir", "exit", "quit"}:
            print(f"\n{ASSISTANT_PREFIX_COLOR}🤖 Agent:{RESET} 👋 ¡Hasta luego!")
            break
        if not user_input.strip():
            continue

        context = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in history
        )
        full_prompt = f"{context}\nUser: {user_input}" if context else user_input

        trace_id = gen_trace_id()
        with trace(workflow_name="MCP Playwright Chat (streamed)", trace_id=trace_id):
            run_streaming = Runner.run_streamed(agent, input=full_prompt, max_turns=20)

            print(f"\n{ASSISTANT_PREFIX_COLOR}🤖 Agent:{RESET} ", end="", flush=True)

            assistant_tokens: List[str] = []

            async for event in run_streaming.stream_events():
                # Tokens del LLM
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    token = event.data.delta
                    print(token, end="", flush=True)
                    assistant_tokens.append(token)
                    continue

                # Eventos de llamada de herramienta
                if (
                    event.type == "run_item_stream_event"
                    and event.item.type == "tool_call_item"
                ):
                    try:
                        name = getattr(
                            event.item.raw_item,
                            "tool",
                            getattr(event.item.raw_item, "name", ""),
                        )
                        args = getattr(
                            event.item.raw_item,
                            "tool_input",
                            getattr(event.item.raw_item, "arguments", {}),
                        )
                    except Exception:
                        name, args = "", {}

                    print(f"{TOOL_COLOR}🔧 Herramienta llamada: {name} → {args}{RESET}")
                    # IMPORTANTE: ignoramos tool_call_output_item para no mostrar la salida

            # Fin de streaming
            print("\n", flush=True)

            # Resultado final para historial
            try:
                final_result = await run_streaming.wait_until_done()
                assistant_reply = final_result.final_output
            except AttributeError:
                assistant_reply = "".join(assistant_tokens)
                final_result = run_streaming  # type: ignore

        # Mostrar listado al final (sin salida)
        await display_tool_calls(final_result)

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": assistant_reply})


# ──────────────────────────────────── Main ─────────────────────────────────── #
async def main(mem_size: int) -> None:
    async with MCPServerStdio(
        name="Playwright Server (MCP)",
        params={"command": "npx", "args": ["@playwright/mcp@latest"]},
    ) as server:
        await chat_loop(server, mem_size=mem_size)


# ────────────────────────────────── Entrypoint ─────────────────────────────── #
if __name__ == "__main__":
    if not shutil.which("npx"):
        raise RuntimeError(
            "npx no está instalado. Instálalo con `npm install -g npx`. "
        )

    parser = argparse.ArgumentParser(
        description="Chatbot que controla Playwright vía MCP con memoria de corto plazo y streaming de respuestas."
    )
    parser.add_argument(
        "-m",
        "--mem",
        type=int,
        default=5,
        help="Número de turnos (usuario+asistente) que se mantienen en memoria (por defecto 5).",
    )
    args = parser.parse_args()

    asyncio.run(main(mem_size=max(1, args.mem)))
