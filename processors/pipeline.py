import os
import re
import textwrap
import ast
from pathlib import Path

from processors.frame_parser import parse_frames
from processors.code_snippet import extract_snippet, find_file_in_codebase
from processors.compressor import shorten_trace
from processors.canonicalizer import canonicalize_exception

from llm.openai_client import LLMClient
from jira.jira_client import JiraClient
from storage.ticket_store import TicketStore
from storage.vector_store import cosine_sim, vec_to_b64, b64_to_vec
from config.settings import SIMILARITY_THRESHOLD, CODEBASE_DIRS


MAX_TRACE_LINES = 60
MAX_LIB_SNIPPET_CHARS = 1000
MAX_TOTAL_PROMPT_CHARS = 4000


class ErrorPipeline:
    def __init__(self):
        self.llm = LLMClient()
        self.jira = JiraClient()
        self.db = TicketStore()

    # ----------------------------------------------------------------------
    # Extract only the function that contains a given line number
    # ----------------------------------------------------------------------
    def extract_full_function(self, path, line_no):
        """
        Extract ONLY the function where the error occurred.
        """
        if not os.path.exists(path):
            alt = find_file_in_codebase(os.path.basename(path))
            if alt:
                path = alt
            else:
                print(f"⚠️ Could not locate file for {path}")
                return None

        try:
            with open(path, "r", encoding="utf8") as f:
                lines = f.readlines()

            # Find the function definition above the error line
            start_idx = None
            idx = max(0, line_no - 1)
            for i in range(idx, -1, -1):
                if re.match(r"^\s*def\s+\w+\s*\(.*\)\s*:", lines[i]):
                    start_idx = i
                    break

            if start_idx is None:
                return None

            # Capture until the next def/class
            func_lines = []
            for j in range(start_idx, len(lines)):
                if j > start_idx and re.match(r"^(def|class)\s+\w+", lines[j].strip()):
                    break
                func_lines.append(lines[j])

            return "".join(func_lines)

        except Exception as e:
            print(f"⚠️ Failed to extract full function from {path}: {e}")
            return None

    # ----------------------------------------------------------------------
    # MAIN PIPELINE
    # ----------------------------------------------------------------------
    def process_exception(self, trace):
        # Canonicalize and embed for duplicate detection
        clean = canonicalize_exception(trace)
        embedding = self.llm.embed(clean)

        # ----------------------------- DUPLICATE CHECK -----------------------------
        best_match, best_score = None, 0.0
        for ticket_id, summary, b64vec in self.db.fetch_all_embeddings():
            stored_vec = b64_to_vec(b64vec)
            sim = cosine_sim(embedding, stored_vec)
            if sim > best_score:
                best_score, best_match = sim, ticket_id

        if best_score >= SIMILARITY_THRESHOLD:
            cur = self.db.conn.cursor()
            cur.execute("SELECT jira_key FROM tickets WHERE id = ?", (best_match,))
            row = cur.fetchone()
            jira_key = row[0] if row else None

            self.db.add_occurrence(best_match, trace)
            if jira_key:
                self.jira.add_comment(jira_key, "Error occurred again (auto-detected).")
            return {
                "duplicate": True,
                "ticket_id": best_match,
                "jira_key": jira_key,
                "similarity": best_score,
            }

        # ----------------------------- NEW ERROR → PREPARE LLM -----------------------------
        frames = parse_frames(trace)
        snippets = []

        if frames:
            project_frames = []
            lib_frames = []

            # Split project vs library frames
            for fr in frames:
                normalized = fr["path"].replace("\\", "/").lower()
                if any(base.lower().replace("\\", "/") in normalized for base in CODEBASE_DIRS):
                    project_frames.append(fr)
                else:
                    lib_frames.append(fr)

            # ----------------------------------------------
            # NEW LOGIC: extract ONLY the functions mentioned
            # ----------------------------------------------
            for fr in project_frames:
                func_code = self.extract_full_function(fr["path"], fr["line"])
                if func_code:
                    snippets.append({
                        "path": fr["path"],
                        "line": fr["line"],
                        "snippet": func_code
                    })
                else:
                    small_snip = extract_snippet(fr["path"], fr["line"])
                    if small_snip:
                        snippets.append({
                            "path": fr["path"],
                            "line": fr["line"],
                            "snippet": small_snip
                        })

            # Add 1–2 library context snippets
            for fr in lib_frames[:2]:
                lib_snip = extract_snippet(fr["path"], fr["line"])
                if lib_snip:
                    snippets.append({
                        "path": fr["path"],
                        "line": fr["line"],
                        "snippet": lib_snip[:MAX_LIB_SNIPPET_CHARS]
                    })

        # ----------------------------- Logging for debugging -----------------------------
        print("\n📄 Frames selected for LLM context:")
        for s in snippets:
            print(f" - {s['path']}:{s['line']} ({len(s['snippet'])} chars)")

        # ----------------------------- Shorten long stack traces -----------------------------
        trace_lines = trace.splitlines()
        if len(trace_lines) > MAX_TRACE_LINES:
            trace = "\n".join(trace_lines[:30] + ["... (trace shortened) ..."] + trace_lines[-20:])

        # ----------------------------- Smart prompt trimming -----------------------------
        total_chars = len(trace) + sum(len(s["snippet"]) for s in snippets)

        if total_chars > MAX_TOTAL_PROMPT_CHARS:
            print(f"⚠️ Prompt too long ({total_chars} chars), trimming.")
            # Trim non-critical snippets first
            if len(snippets) > 1:
                for s in snippets[1:]:
                    s["snippet"] = s["snippet"][:400]

            total_chars = len(trace) + sum(len(s["snippet"]) for s in snippets)
            if total_chars > MAX_TOTAL_PROMPT_CHARS:
                trace = trace[:int(MAX_TOTAL_PROMPT_CHARS * 0.4)]

        # ----------------------------- Show LLM payload -----------------------------
        print("\n===================== SENT TO LLM =====================")
        print(f"STACK TRACE ({len(trace)} chars):\n{trace}")
        for s in snippets:
            print(f"\nCODE SNIPPET from {s['path']}:{s.get('line')} ({len(s['snippet'])} chars):")
            print(textwrap.shorten(s["snippet"], width=800, placeholder="...[cut]..."))
        print("=======================================================\n")

        # ----------------------------- LLM Analysis -----------------------------
        analysis = self.llm.analyze(trace, snippets)

        summary = analysis["summary"]
        description = analysis["cause"]

        # Priority mapping
        raw_priority = analysis["priority"].lower()
        if "crit" in raw_priority or "p1" in raw_priority or "high" in raw_priority:
            priority = "High"
        elif "p2" in raw_priority or "med" in raw_priority:
            priority = "Medium"
        else:
            priority = "Low"

        suggestions = analysis.get("suggestions", [])

        # Create Jira ticket
        jira_key = self.jira.create_ticket(summary, description, priority, suggestions)

        # Store ticket + embedding
        ticket_id = self.db.add_new_ticket(
            jira_key=jira_key,
            summary=summary,
            embedding=vec_to_b64(embedding)
        )

        # Store occurrence + exception details
        self.db.add_occurrence(ticket_id, trace)
        self.db.add_exception_details(
            ticket_id,
            analysis,
            trace,
            clean,
            snippets[0]["snippet"] if snippets else ""
        )

        return {
            "duplicate": False,
            "analysis": analysis,
        }
