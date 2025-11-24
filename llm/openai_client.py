import json
import re
import tiktoken
from openai import OpenAI
from config.settings import OPENAI_API_KEY, MODEL_NAME, EMBEDDING_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

JSON_BLOCK = re.compile(r"\{(?:[^{}]|{[^{}]*})*\}", re.DOTALL)

ENCODER = tiktoken.encoding_for_model(MODEL_NAME)

MAX_TOKENS_PER_CHUNK = 1000

from typing import List
from pydantic import BaseModel


class ExceptionAnalysis(BaseModel):
    cause: str
    summary: str
    priority: str
    suggestions: List[str]
    documentation_link: List[str]
    exception_class: str


def count_tokens(text: str) -> int:
    try:
        return len(ENCODER.encode(text))
    except Exception:
        return len(text.split())


class LLMClient:

    def embed(self, text):
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def _extract_json(self, text: str):
        """
        Extract JSON robustly, even if OpenAI returns extra text.
        """
        # direct parse first
        try:
            return json.loads(text)
        except:
            pass

        m = JSON_BLOCK.search(text)
        if not m:
            return None

        try:
            return json.loads(m.group(0))
        except:
            return None

    def _build_system_prompt(self):
        return """
You are an AI debugging assistant. You will receive:
1. A Python stack trace
2. One or more code snippets

Your task: analyze the error and return STRICT JSON with:

{
  "cause": "...",
  "summary": "...",
  "priority": "High | Medium | Low",
  "suggestions": ["...", "..."],
  "documentation_link": ["url1", "url2"],
}

Give only 2 suggestions maximum.

RETURN VALID JSON ONLY.
"""

    def _clean(self, text):
        return "\n".join(
            line.rstrip()
            for line in text.split("\n")
            if line.strip()
        )

    def _chunk_text(self, text, max_tokens=MAX_TOKENS_PER_CHUNK):
        text = self._clean(text)
        lines = text.split("\n")
        chunks = []
        current = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            tentative = (current + "\n" + line) if current else line

            if count_tokens(tentative) > max_tokens:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = tentative

        if current:
            chunks.append(current)

        return chunks

    def _chunk_snippets(self, snippets, max_tokens=MAX_TOKENS_PER_CHUNK):
        """
        Chunk code snippets based on token count.
        Returns list of snippet lists.
        """
        if not snippets:
            return []
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for snippet in snippets:
            snippet_text = self._clean(snippet["snippet"])
            snippet_tokens = count_tokens(snippet_text)
            
            # If single snippet exceeds max, still add it (don't lose data)
            if snippet_tokens > max_tokens:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_tokens = 0
                chunks.append([snippet])
            # If adding to current chunk exceeds max, start new chunk
            elif current_tokens + snippet_tokens > max_tokens:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = [snippet]
                current_tokens = snippet_tokens
            # Add to current chunk
            else:
                current_chunk.append(snippet)
                current_tokens += snippet_tokens
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def _analyze_chunk(self, trace_chunk, snippet_chunk, is_refinement=False):
        """
        Analyze a single chunk of trace + snippets.
        
        Args:
            trace_chunk: Stack trace text
            snippet_chunk: List of code snippet dicts
            is_refinement: If True, use refinement prompt
        """
        trace_chunk = self._clean(trace_chunk)

        if is_refinement:
            prompt = f"Additional trace context:\n\n{trace_chunk}\n\n"
            if snippet_chunk:
                prompt += "Additional code snippets:\n"
                for s in snippet_chunk:
                    cleaned = self._clean(s["snippet"])
                    prompt += f"\n--- {s['path']}:{s['line']} ---\n{cleaned}\n"
        else:
            prompt = f"STACK TRACE:\n{trace_chunk}\n\nCODE SNIPPETS:\n"
            for s in snippet_chunk:
                cleaned = self._clean(s["snippet"])
                prompt += f"\n--- {s['path']}:{s['line']} ---\n{cleaned}\n"

        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        return self._extract_json(resp.choices[0].message.content.strip())

    def analyze(self, trace, snippets):
        """
        Analyze exception by chunking trace and snippets into manageable pieces.
        
        Strategy:
        1. Send first chunk of trace with first chunk of snippets
        2. Send remaining snippet chunks (to get all context analyzed)
        3. Send remaining trace chunks (for refinement)
        """
        
        trace_chunks = self._chunk_text(trace)
        snippet_chunks = self._chunk_snippets(snippets)
        
        print(f"📦 Trace chunks: {len(trace_chunks)}, Snippet chunks: {len(snippet_chunks)}")
        
        # PRIMARY ANALYSIS: First trace chunk with first snippet chunk
        primary = None
        if trace_chunks:
            first_snippets = snippet_chunks[0] if snippet_chunks else []
            primary = self._analyze_chunk(trace_chunks[0], first_snippets, is_refinement=False)
        
        if not primary:
            primary = {
                "cause": "LLM returned invalid JSON",
                "summary": "Invalid output",
                "priority": "Medium",
                "suggestions": ["Retry with fewer chunks"],
                "documentation_link": [],
                "exception_class": "PythonError",
            }
        
        print(f"✅ Primary analysis complete")
        
        # REFINEMENT PHASE 1: Process remaining snippet chunks
        for i, snippet_chunk in enumerate(snippet_chunks[1:], start=1):
            print(f"🔄 Processing snippet chunk {i+1}/{len(snippet_chunks)}...")
            
            refinement = self._analyze_chunk(
                trace_chunks[0],
                snippet_chunk,
                is_refinement=True
            )
            
            if refinement and refinement.get("suggestions"):
                for sug in refinement["suggestions"]:
                    if sug not in primary["suggestions"]:
                        primary["suggestions"].append(sug)
        
        # REFINEMENT PHASE 2: Process remaining trace chunks
        for i, trace_chunk in enumerate(trace_chunks[1:], start=1):
            print(f"🔄 Processing trace chunk {i+1}/{len(trace_chunks)}...")
            
            # Send with empty snippets since we already processed all snippet chunks
            refinement = self._analyze_chunk(
                trace_chunk,
                [],
                is_refinement=True
            )
            
            if refinement and refinement.get("suggestions"):
                for sug in refinement["suggestions"]:
                    if sug not in primary["suggestions"]:
                        primary["suggestions"].append(sug)
        
        print(f"✅ All chunks processed")
        return primary
