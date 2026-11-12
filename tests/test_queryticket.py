"""QueryTicket acceptance tests: stdlib only, no network, no credentials.

Run from the repo root:  python3 tests/test_queryticket.py
Covers the fixed-catalog gate, the owner approval step, the simulated
sample payment, locked/unlocked delivery with the integrity check, and
the HTTP token guard on the local app.
"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import core  # noqa: E402

passed = 0


def raises(fn, *args):
    try:
        fn(*args)
        return False
    except Exception:
        return True



def check(name, condition):
    global passed
    assert condition, name
    passed += 1
    print("ok -", name)


tmp = tempfile.mkdtemp(prefix="qt-test-")
db = str(Path(tmp) / "test.sqlite")
core.init(db)

# Gate: refuses personal, record-level, dated or filtered requests before any checkout.
for q in [
    "Show me John's battery tickets",
    "battery problems last week",
    "all raw records with email addresses",
    "battery and focus problems",
    "battery problems where id > 5",
]:
    r = core.parse_question(q)
    check("refuses: %r" % q, r["allowed"] is False)

# Gate: accepts exactly one topic, whole dataset, no filters.
r = core.parse_question("How widespread are battery charging problems?")
check("accepts single-topic question", r["allowed"] and r["topic"] == "battery")

rep = core.create_report(db, "How widespread are battery charging problems?")["report"]
check("new report starts in review", rep["status"] == "review")
check("download locked before payment", raises(core.delivery, db, rep["id"]))

core.transition(db, rep["id"], "approve")
check("approve moves review->approved", core.get_report(db, rep["id"])["status"] == "approved")
check("simulate requires approved", not raises(core.transition, db, rep["id"], "simulate"))

core.transition(db, rep["id"], "simulate")
unlocked = core.delivery(db, rep["id"])
check("sample payment unlocks delivery", unlocked["receipt"]["payment_mode"] == "simulation")
check("receipt discloses it is not signed", "not_a_signature" in unlocked["receipt"])
check("report is honest about synthetic data", "Synthetic" in unlocked["report"]["limitation"])

# Deterministic report contents.
rpt = unlocked["report"]
check("population is the full fixture set", rpt["population"] == 200)
check("counts add up", 0 < rpt["matching_count"] < rpt["population"])

# HTTP layer: token guard and localhost-only behaviour.
os.environ["QUERYTICKET_DB"] = str(Path(tmp) / "http.sqlite")
import app  # noqa: E402

server = app.ThreadingHTTPServer(("127.0.0.1", 8765), app.Handler)
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()
time.sleep(0.3)


def http(path, body=None, token=None):
    req = urllib.request.Request(
        "http://127.0.0.1:8765" + path,
        data=json.dumps(body).encode() if body is not None else None,
    )
    if token:
        req.add_header("X-QueryTicket-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=5) as x:
            return x.status, json.load(x)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


s, state = http("/api/state")
check("http state ok", s == 200 and "token" in state)
s, _ = http("/api/query", {"question": "battery charging problems?"}, token="wrong")
check("http rejects wrong token", s == 403)
s, q = http("/api/query", {"question": "How widespread are delivery delays?"}, token=state["token"])
check("http creates report", s == 200 and q["report"]["spec"]["topic"] == "delivery")
s, dl = http("/api/download/" + q["report"]["id"], token=state["token"])
check("http download locked pre-payment", s == 403)
s, sb = http("/api/sandbox/create", {"id": q["report"]["id"]}, token=state["token"])
check("sandbox-unconfigured is an honest error, not success", s in (400, 502))
server.shutdown()

print("\n%d checks passed" % passed)
