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
You are a Python debugging assistant. Given a stack trace and relevant code snippets, 
analyze the error and return a JSON object with the following fields:

- cause (string)
- summary (string, max 255 chars)
- priority (string: High, Medium, Low)
- suggestions (list of strings)
- documentation_link (list of 1-2 URLs)
- exception_class (string: one of ["PythonError", "MLError", "AIPipelineError", "DataError"])

Classification guidelines:
- PythonError -> built-in Python exceptions (TypeError, KeyError, FileNotFoundError, etc.)
- MLError -> errors from ML libraries (PyTorch, TensorFlow, Sklearn, ONNX, Transformers, CUDA, NCCL…)
- AIPipelineError -> errors inside custom application or pipeline logic
- DataError -> data format/schema/dtype/value issues, Pandas/Numpy loading problems


Choose priority using:
High   → crashes the program, breaks workflow, corrupts data  
Medium → feature breaks but program continues  
Low    → minor issues, noisy logs, recoverable  

Your output must be valid JSON only.
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
