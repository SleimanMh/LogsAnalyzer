import os
import re
import textwrap

from processors.frame_parser import parse_frames, resolve_frame_location
from processors.code_snippet import extract_snippet, find_file_in_codebase
from processors.canonicalizer import canonicalize_exception
from processors.ml_classifier_service import MLClassifierService

from llm.openai_client import LLMClient
from jira.jira_client import JiraClient
from storage.ticket_store import TicketStore
from storage.dataset_writer import DatasetWriter
from storage.vector_store import cosine_sim, vec_to_b64, b64_to_vec
from config.settings import SIMILARITY_THRESHOLD, CODEBASE_DIRS


class ErrorPipeline:

    def __init__(self):
        self.llm = LLMClient()
        self.jira = JiraClient()
        self.db = TicketStore()
        self.dataset = DatasetWriter()
        self.ml = MLClassifierService()

    def extract_full_function(self, path, line_no):
        """Return full function code where the given line belongs."""
        if not os.path.exists(path):
            alt = find_file_in_codebase(os.path.basename(path))
            if alt:
                path = alt
            else:
                print(f"⚠️ Could not locate file: {path}")
                return None

        try:
            with open(path, "r", encoding="utf8") as f:
                lines = f.readlines()

            start_idx = None
            idx = max(0, line_no - 1)
            FUNC_RE = re.compile(r"^\s*def\s+\w+\s*\(.*\):")

            for i in range(idx, -1, -1):
                if FUNC_RE.match(lines[i]):
                    start_idx = i
                    break

            if start_idx is None:
                return None

            func = []
            for j in range(start_idx, len(lines)):
                if j > start_idx and re.match(r"^\s*(def|class)\s+", lines[j]):
                    break
                func.append(lines[j])

            return "".join(func)

        except Exception as e:
            print(f"⚠️ Function extraction failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------
    def process_exception(self, trace):

        clean = canonicalize_exception(trace)

        embedding = self.llm.embed(clean)

        # ------------------ Duplicate detection ------------------
        best_match, best_score = None, 0.0
        for ticket_id, summary, b64vec in self.db.fetch_all_embeddings():
            stored_vec = b64_to_vec(b64vec)
            sim = cosine_sim(embedding, stored_vec)
            if sim > best_score:
                best_score = sim
                best_match = ticket_id

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

        # ------------------ NEW ERROR: Extract frames ------------------
        frames = parse_frames(trace)
        snippets = []

        normalized_dirs = [d.replace("\\", "/").lower() for d in CODEBASE_DIRS]

        project_frames = []
        for fr in frames:
            p = fr["path"].replace("\\", "/")

            if "/app/errors/" in p.lower():
                project_frames.append(fr)


        # extract per-frame code
        for fr in project_frames:
            resolved_path, resolved_line = resolve_frame_location(fr, CODEBASE_DIRS)

            func_code = self.extract_full_function(resolved_path, resolved_line)
            if func_code:
                snippets.append({
                    "path": resolved_path,
                    "line": resolved_line,
                    "snippet": func_code
                })
            else:
                small = extract_snippet(resolved_path, resolved_line)
                if small:
                    snippets.append({
                        "path": resolved_path,
                        "line": resolved_line,
                        "snippet": small
                    })

        # ---------------- Debug Logging ----------------
        print("\n📄 Code sent to LLM:")
        for s in snippets:
            print(f" - {s['path']}:{s['line']} ({len(s['snippet'])} chars)")

        print("\n=== STACK TRACE SENT ===")
        print(trace)
        print("========================\n")

        print("\n=== SNIPPET SENT ===")
        print(snippets)
        print("========================\n")

        # ---------------- LLM analysis ----------------
        analysis = self.llm.analyze(trace, snippets)

        ml_class, ml_probs = self.ml.predict(trace, snippets)
        print(f"🤖 ML Classifier: {ml_class} | Conf: {ml_probs}")

        summary = analysis["summary"]
        description = analysis["cause"]

        # priority normalization
        raw = analysis["priority"].lower()
        if any(k in raw for k in ["crit", "p1", "high"]):
            priority = "High"
        elif any(k in raw for k in ["p2", "medium"]):
            priority = "Medium"
        else:
            priority = "Low"

        jira_key = self.jira.create_ticket(
            summary, description, priority, analysis.get("suggestions", [])
        )

        # Save ticket
        ticket_id = self.db.add_new_ticket(
            jira_key=jira_key,
            summary=summary,
            embedding=vec_to_b64(embedding)
        )

        self.db.add_occurrence(ticket_id, trace)

        self.db.add_exception_details(
            ticket_id,
            analysis,
            trace,
            clean,
            ml_class,
            snippets[0]["snippet"] if snippets else "",
        )

        return {
            "duplicate": False,
            "analysis": analysis,
        }
