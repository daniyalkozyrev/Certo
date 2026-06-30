"""Quick standalone test of the Certo SDK — does NOT touch Hermes or any real agent.

It sends 3 made-up steps (a fake trajectory) to Certo so you can see a trace
appear and get scored. Run it, then open http://localhost:3000/traces.

HOW TO RUN (PowerShell):
    1. Paste your token below (F12 on localhost:3000 -> Application ->
       Local Storage -> certo.token -> copy the value).
    2. Run:
       C:\\Users\\user\\Desktop\\Certo\\backend\\.venv\\Scripts\\python.exe C:\\Users\\user\\Desktop\\Certo\\try_certo.py
"""

import sys

sys.path.insert(0, r"C:\Users\user\Desktop\Certo\sdk")  # so `import certo` is found
import certo

# ── paste your token here ────────────────────────────────────────────────
TOKEN = "PASTE_YOUR_TOKEN_HERE"
# ─────────────────────────────────────────────────────────────────────────

with certo.trace(
    "Find the population of Tokyo, report the number in millions",
    api_key=TOKEN,
    base_url="http://localhost:8000",
    name="my first trace",
) as t:
    t.log_span("llm", "planner", input="how to answer?", output="search web, then report")
    t.log_span("tool", "web_search", input={"q": "Tokyo population"}, output="~14 million")
    t.log_span("agent", "reporter", output="14 million")
    res = t.finish("Tokyo's population is about 14 million")

print("Done! Trace:", res["id"], "-> open http://localhost:3000/traces")
