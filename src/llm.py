import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-haiku-5-5"
client = anthropic.Anthropic()


def ask_llm(system, user, max_tokens=1024):
    """Send one prompt to the LLM. This is the only place that talks to Claude."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # The reply is a list of blocks; keep only the visible text (skip any reasoning blocks)
    text = "".join(block.text for block in response.content if block.type == "text")
    return {
        "text": text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }