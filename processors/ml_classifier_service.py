import os
import joblib
import re

def clean_stack_trace(trace):
    if not isinstance(trace, str):
        return ""
    lines = trace.strip().split("\n")
    if len(lines) <= 20:
        return trace.strip()
    return "\n".join(lines[:10] + ["...\n"] + lines[-10:])

class MLClassifierService:
    def __init__(self):
        base = os.path.join(os.path.dirname(__file__), "..", "model_output")

        self.vectorizer = joblib.load(os.path.join(base, "tfidf_vectorizer.joblib"))
        self.model = joblib.load(os.path.join(base, "random_forest_model.joblib"))

    def preprocess(self, trace, snippets):
        clean_trace = clean_stack_trace(trace)
        snippet_text = "\n".join([s["snippet"] for s in snippets]) if snippets else ""
        full_text = clean_trace + "\n" + snippet_text
        return full_text

    def predict(self, trace, snippets):
        text = self.preprocess(trace, snippets)
        X = self.vectorizer.transform([text])

        predicted_label = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0].tolist()

        return predicted_label, probabilities
