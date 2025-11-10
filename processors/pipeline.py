from processors.frame_parser import parse_frames
from processors.code_snippet import extract_snippet
from processors.compressor import shorten_trace
from processors.canonicalizer import canonicalize_exception

from llm.openai_client import LLMClient
from jira.jira_client import JiraClient
from storage.ticket_store import TicketStore
from storage.vector_store import cosine_sim, vec_to_b64, b64_to_vec
from config.settings import SIMILARITY_THRESHOLD


class ErrorPipeline:

    def __init__(self):
        self.llm = LLMClient()
        self.jira = JiraClient()
        self.db = TicketStore()

    def process_exception(self, trace):

        # ✅ minimize / normalize trace
        clean = canonicalize_exception(trace)

        # ✅ embed canonical trace
        embedding = self.llm.embed(clean)
        if embedding is None:
            print("⚠️ LLM returned no embedding — skipping")
            return None

        # ✅ cosine search in DB
        best_match = None
        best_score = 0.0

        for ticket_id, summary, b64vec in self.db.fetch_all_embeddings():
            stored_vec = b64_to_vec(b64vec)

            sim = cosine_sim(embedding, stored_vec)
            if sim > best_score:
                best_score = sim
                best_match = ticket_id

        # ✅ Duplicate found
        if best_score >= SIMILARITY_THRESHOLD:
            jira_key = self._get_jira_key(best_match)

            # ✅ Log new occurrence
            self.db.add_occurrence(best_match, trace)

            # ✅ Store detailed occurrence
            self.db.add_exception_details(
                ticket_id=best_match,
                analysis={"priority": "", "summary": "", "cause": "", "suggestions": []},
                trace=trace,
                canonical=clean,
                snippet=""
            )

            # ✅ add Jira comment
            self.jira.add_comment(
                jira_key,
                f"⚠️ Error occurred again (similarity={best_score:.3f}). Auto-logged."
            )

            return {
                "duplicate": True,
                "ticket_id": best_match,
                "jira_key": jira_key,
                "similarity": best_score,
            }

        # ✅ Not duplicate → do LLM analysis
        frames = parse_frames(trace)

        snippets = []
        for fr in frames[:2]:
            snip = extract_snippet(fr["path"], fr["line"])
            if snip:
                snippets.append({
                    "path": fr["path"],
                    "line": fr["line"],
                    "snippet": snip
                })

        analysis = self.llm.analyze(trace, snippets)

        # ✅ Priority normalization
        raw_prio = str(analysis.get("priority", "")).lower()
        if any(x in raw_prio for x in ["p1", "critical", "crit", "high"]):
            priority = "High"
        elif any(x in raw_prio for x in ["p2", "medium", "med"]):
            priority = "Medium"
        else:
            priority = "Low"

        summary = analysis.get("summary", "Unhandled exception")
        description = analysis.get("cause", "No cause provided by LLM")

        # ✅ Create Jira ticket
        jira_key = self.jira.create_ticket(
            summary=summary,
            description=description,
            priority=priority
        )

        # ✅ Store new ticket
        ticket_id = self.db.add_new_ticket(
            jira_key=jira_key,
            summary=summary,
            embedding=vec_to_b64(embedding)
        )

        # ✅ store occurrence
        self.db.add_occurrence(ticket_id, trace)

        # ✅ store exception details
        snippet_text = snippets[0]["snippet"] if snippets else ""
        self.db.add_exception_details(
            ticket_id=ticket_id,
            analysis=analysis,
            trace=trace,
            canonical=clean,
            snippet=snippet_text
        )

        return {
            "duplicate": False,
            "ticket_id": ticket_id,
            "jira_key": jira_key,
            "analysis": analysis,
        }

    def _get_jira_key(self, ticket_id):
        cur = self.db.conn.cursor()
        cur.execute("SELECT jira_key FROM tickets WHERE id = ?", (ticket_id,))
        row = cur.fetchone()
        return row[0] if row else None
