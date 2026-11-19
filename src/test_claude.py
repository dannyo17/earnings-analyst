from dotenv import load_dotenv
import anthropic

load_dotenv()  # loads ANTHROPIC_API_KEY from the .env file into the environment

client = anthropic.Anthropic()  # picks up the key from the environment automatically

response = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=100,
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
)

print(response.content[0].text)