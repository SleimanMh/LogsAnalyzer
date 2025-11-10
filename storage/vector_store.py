import numpy as np
import base64

def vec_to_b64(v):
    v = np.array(v, dtype=np.float32)  # ✅ ensure numpy array
    return base64.b64encode(v.tobytes()).decode("utf8")

def b64_to_vec(b):
    raw = base64.b64decode(b)
    return np.frombuffer(raw, dtype=np.float32)

def cosine_sim(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
