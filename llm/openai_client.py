import json
import re
from openai import OpenAI
from config.settings import OPENAI_API_KEY, MODEL_NAME, EMBEDDING_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

class LLMClient:

    def embed(self, text):
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def _extract_json(self, text):
        try:
            return json.loads(text)
        except:
            m = JSON_BLOCK.search(text)
            if m:
                try:
                    return json.loads(m.group(0))
                except:
                    return None
        return None

    def analyze(self, trace, snippets):
        prompt = f"""
You are a Python debugging assistant.
You must return ONLY JSON with keys:
- cause (string)
- summary (string), it shouldn't exceed 255 characters.
- priority (string: one of ["High", "Medium", "Low"])
- suggestions (list of strings)

Choose priority using:
High   → crashes the program, breaks workflow, or corrupts data  
Medium → error prevents a feature from working, but app continues  
Low    → minor issues, recoverable, noisy logs, not user-facing  


STACK TRACE:
{trace}

CODE SNIPPETS:
{snippets}
"""

        for s in snippets:
            prompt += f"\n--- {s['path']}:{s['line']} ---\n{s['snippet']}\n"

        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        content = resp.choices[0].message.content.strip()
        parsed = self._extract_json(content)

        if parsed:
            return parsed

        return {
            "cause": "Model returned invalid JSON",
            "summary": "LLM failed to produce valid JSON",
            "priority": "Medium",
            "suggestions": ["Review input format"]
        }
