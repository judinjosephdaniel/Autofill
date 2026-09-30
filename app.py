"""
Form AutoFill Studio  -  fills the enquiry form row by row; YOU click ENQUIRY.
Run:  python app.py   ->  open http://127.0.0.1:5000
"""
import os, threading
from flask import Flask, request, jsonify
import pandas as pd
from playwright.sync_api import sync_playwright

# ===================== PATH / CONFIG (EDIT THESE) =====================
TARGET_URL = "https://bpoautoaccept.com/"

# OPTIONAL: Set this to your exact CSV file path if you want it to load automatically.
# Leave it as "" to use the drag-and-drop upload box in the web interface.
DATA_FILE_PATH = r""  # Example: r"C:\Users\Admin\Downloads\files\sample_form_test_dataset_100.csv"

# Browser to open. Options: "chrome", "msedge", or "" for Playwright's bundled Chromium
BROWSER_CHANNEL = "chrome"

# Optional: full path to a browser .exe (overrides BROWSER_CHANNEL if set)
BROWSER_EXE_PATH = r""        # Example: r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# Folder where uploaded sheets are saved
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
# ======================================================================

os.makedirs(UPLOAD_DIR, exist_ok=True)
app = Flask(__name__)
S = {"rows": [], "status": "idle", "index": -1, "stop": False, "log": [], "file": ""}


def load(path):
    df = pd.read_csv(path) if path.lower().endswith(".csv") else pd.read_excel(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    def col(key):
        return next((c for c in df.columns if key in c), None)
    m = {k: col(k) for k in ("name", "email", "phone", "message")}
    if not all(m.values()):
        raise ValueError("Need columns: Name, Email, Phone Number, Message")
    return [{"name": str(r[m["name"]]), "email": str(r[m["email"]]),
             "phone": str(r[m["phone"]]), "message": str(r[m["message"]]),
             "state": "pending"} for _, r in df.fillna("").iterrows()]


def log(msg):
    S["log"].append(msg); S["log"] = S["log"][-200:]


def worker(url):
    S.update(status="running", stop=False)
    clicked = threading.Event()
    try:
        with sync_playwright() as p:
            opts = {"headless": False, "args": ["--start-maximized"]}
            if BROWSER_EXE_PATH:
                opts["executable_path"] = BROWSER_EXE_PATH
            elif BROWSER_CHANNEL:
                opts["channel"] = BROWSER_CHANNEL
            
            browser = p.chromium.launch(**opts)
            
            # Create a fresh context and page to ensure a clean window
            context = browser.new_context(no_viewport=True)
            page = context.new_page()

            # Fires when YOU click the ENQUIRY button
            page.expose_function("rowSubmitted", lambda: clicked.set())
            page.add_init_script("""
                document.addEventListener('click', e => {
                    const b = e.target.closest('button');
                    if (b && /enquiry/i.test(b.innerText)) window.rowSubmitted();
                }, true);
            """)

            for i, r in enumerate(S["rows"]):
                if S["stop"]:
                    break
                if r["state"] == "done":
                    continue
                S["index"] = i
                r["state"] = "running"
                clicked.clear()
                try:
                    page.bring_to_front() # Pop the browser window to the front
                    page.goto(url, wait_until="domcontentloaded")
                    
                    # Use .first to avoid strict mode violations if multiple placeholders exist
                    page.get_by_placeholder("Your full name").first.fill(r["name"])
                    page.get_by_placeholder("you@example.com").first.fill(r["email"])
                    page.get_by_placeholder("+1 555 000 0000").first.fill(r["phone"])
                    page.get_by_placeholder("How can we help you?").first.fill(r["message"])
                    
                    log(f"Row {i+1}: filled {r['name']} - PLEASE CLICK 'ENQUIRY' IN THE BROWSER")

                    while not clicked.is_set() and not S["stop"]:
                        page.wait_for_timeout(300)
                    if S["stop"]:
                        r["state"] = "pending"
                        break

                    page.wait_for_timeout(4000) # Wait 4 seconds for the site to process
                    r["state"] = "done"
                    log(f"Row {i+1}: submitted {r['name']}")
                except Exception as e:
                    r["state"] = "failed"
                    log(f"Row {i+1}: failed - {str(e)[:90]}")
                    if page.is_closed():
                        break
            context.close()
            browser.close()
    except Exception as e:
        log(f"Browser error: {e}")
    S["status"] = "stopped" if S["stop"] else "finished"


@app.post("/upload")
def upload():
    try:
        f = request.files["file"]
        path = os.path.join(UPLOAD_DIR, os.path.basename(f.filename))
        f.save(path)
        S["rows"] = load(path)
        S.update(status="ready", index=-1, log=[], file=os.path.basename(path))
        return jsonify(ok=True, count=len(S["rows"]))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400


@app.post("/start")
def start():
    d = request.json
    if S["status"] == "running" or not S["rows"]:
        return jsonify(ok=False), 400
    threading.Thread(target=worker, daemon=True, args=(d.get("url") or TARGET_URL,)).start()
    return jsonify(ok=True)


@app.post("/stop")
def stop():
    S["stop"] = True
    return jsonify(ok=True)


@app.get("/status")
def status():
    return jsonify(S)


@app.get("/")
def home():
    return HTML.replace("__URL__", TARGET_URL)


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>Form AutoFill Studio</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600&display=swap" rel="stylesheet">
<style>
:root{--bg:#050d1f;--card:rgba(255,255,255,.05);--line:rgba(255,255,255,.1);--gold:#f3c969;--gold2:#d9a73c;--txt:#e8edf7;--mut:#8b99b5;--ok:#4ade80;--bad:#f87171}
*{box-sizing:border-box}body{margin:0;font-family:Inter,sans-serif;color:var(--txt);min-height:100vh;
background:radial-gradient(900px 500px at 10% -10%,#16356b55,transparent),radial-gradient(700px 500px at 100% 10%,#d9a73c22,transparent),var(--bg)}
.wrap{max-width:1150px;margin:auto;padding:40px 24px}
h1{font-family:'Playfair Display',serif;font-size:38px;margin:0}h1 span{color:var(--gold)}
.sub{color:var(--mut);margin:6px 0 30px}
.grid{display:grid;grid-template-columns:380px 1fr;gap:22px}@media(max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;backdrop-filter:blur(14px);box-shadow:0 20px 50px #0006}
.card h3{margin:0 0 14px;font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
.drop{border:2px dashed #ffffff30;border-radius:14px;padding:30px 12px;text-align:center;cursor:pointer;transition:.2s}
.drop:hover,.drop.on{border-color:var(--gold);background:#f3c96910}.drop b{color:var(--gold)}.drop small{color:var(--mut)}
label{display:block;font-size:12px;color:var(--mut);margin:14px 0 6px}
input[type=text]{width:100%;padding:11px 13px;border-radius:10px;border:1px solid var(--line);background:#0a1a3a;color:var(--txt);font:inherit}
.chk{display:flex;gap:10px;align-items:flex-start;font-size:12.5px;color:var(--mut);margin-top:14px;line-height:1.45}
.chk input{margin-top:3px;accent-color:var(--gold)}
.btn{width:100%;padding:14px;border:0;border-radius:12px;font-weight:700;letter-spacing:.08em;cursor:pointer;margin-top:18px;
background:linear-gradient(135deg,var(--gold),var(--gold2));color:#1a1400;box-shadow:0 8px 24px #d9a73c55;transition:.2s}
.btn:hover{transform:translateY(-1px)}.btn:disabled{opacity:.4;cursor:not-allowed;transform:none}
.btn.ghost{background:transparent;color:var(--txt);border:1px solid var(--line);box-shadow:none;margin-top:10px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.stat{background:#ffffff08;border:1px solid var(--line);border-radius:12px;padding:14px}
.stat div{font-size:26px;font-weight:700}.stat span{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.1em}
.bar{height:8px;background:#ffffff14;border-radius:99px;overflow:hidden;margin-bottom:16px}
.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--gold2),var(--gold));transition:width .4s}
.tbl{max-height:340px;overflow:auto;border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px 12px;text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:#0b1d42;color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.1em}
tr:nth-child(even) td{background:#ffffff05}tr.cur td{background:#f3c96914}
.b{padding:3px 10px;border-radius:99px;font-size:11px;font-weight:600}
.pending{background:#ffffff14;color:var(--mut)}.running{background:#f3c96926;color:var(--gold)}
.done{background:#4ade8022;color:var(--ok)}.failed{background:#f8717122;color:var(--bad)}
.log{margin-top:16px;font:12px ui-monospace,monospace;color:var(--mut);max-height:110px;overflow:auto;line-height:1.7}
</style></head><body><div class="wrap">
<h1>Form AutoFill <span>Studio</span></h1><div class="sub">Each form is filled for you. Click ENQUIRY in the browser and the next row loads automatically.</div>
<div class="grid"><div>
<div class="card"><h3>1 · Data</h3>
<div class="drop" id="drop"><div style="font-size:30px">⬆</div><b>Drop CSV / Excel</b><br><small id="fn">or click to browse</small></div>
<input type="file" id="file" accept=".csv,.xlsx,.xls" hidden>
<h3 style="margin-top:22px">2 · Target</h3>
<label>Form URL</label><input type="text" id="url" value="__URL__">
<div class="chk"><input type="checkbox" id="perm"><span>I own this website or have permission to submit test enquiries to it.</span></div>
<button class="btn" id="start" disabled>START AUTOMATION</button>
<button class="btn ghost" id="stop">Stop</button></div></div>
<div class="card"><h3>Progress</h3>
<div class="stats"><div class="stat"><div id="sT">0</div><span>Total</span></div><div class="stat"><div id="sD" style="color:var(--ok)">0</div><span>Done</span></div>
<div class="stat"><div id="sF" style="color:var(--bad)">0</div><span>Failed</span></div><div class="stat"><div id="sS">idle</div><span>Status</span></div></div>
<div class="bar"><i id="pb"></i></div>
<div class="tbl"><table><thead><tr><th>#</th><th>Name</th><th>Email</th><th>Phone</th><th>Status</th></tr></thead><tbody id="tb"></tbody></table></div>
<div class="log" id="log"></div></div></div></div>
<script>
const $=id=>document.getElementById(id);let ready=false;
const chk=()=>$('start').disabled=!(ready&&$('perm').checked);$('perm').onchange=chk;
$('drop').onclick=()=>$('file').click();
['dragover','dragleave','drop'].forEach(e=>$('drop').addEventListener(e,ev=>{ev.preventDefault();$('drop').classList.toggle('on',e=='dragover');
 if(e=='drop'&&ev.dataTransfer.files[0])up(ev.dataTransfer.files[0])}));
$('file').onchange=e=>e.target.files[0]&&up(e.target.files[0]);
async function up(f){const fd=new FormData();fd.append('file',f);const r=await fetch('/upload',{method:'POST',body:fd});const j=await r.json();
 if(!j.ok){alert(j.error);return}$('fn').textContent=f.name+' · '+j.count+' rows';ready=true;chk()}
$('start').onclick=()=>fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:$('url').value})});
$('stop').onclick=()=>fetch('/stop',{method:'POST'});
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
async function poll(){try{const s=await (await fetch('/status')).json();const R=s.rows;
 if(R.length&&!ready){ready=true;$('fn').textContent=(s.file||'sheet')+' · '+R.length+' rows';chk()}
 const d=R.filter(r=>r.state=='done').length,f=R.filter(r=>r.state=='failed').length;
 $('sT').textContent=R.length;$('sD').textContent=d;$('sF').textContent=f;$('sS').textContent=s.status;
 $('pb').style.width=(R.length?(d+f)/R.length*100:0)+'%';
 $('tb').innerHTML=R.map((r,i)=>`<tr class="${i==s.index&&r.state=='running'?'cur':''}"><td>${i+1}</td><td>${esc(r.name)}</td><td>${esc(r.email)}</td><td>${esc(r.phone)}</td><td><span class="b ${r.state}">${r.state}</span></td></tr>`).join('');
 $('log').innerHTML=s.log.slice(-6).map(esc).join('<br>');
 const cur=document.querySelector('tr.cur');cur&&cur.scrollIntoView({block:'nearest'});}catch(e){}
 setTimeout(poll,1000)}
poll();
</script></body></html>"""

if __name__ == "__main__":
    if DATA_FILE_PATH and os.path.exists(DATA_FILE_PATH):
        S["rows"] = load(DATA_FILE_PATH)
        S.update(status="ready", file=os.path.basename(DATA_FILE_PATH))
        print(f"Loaded {len(S['rows'])} rows from {DATA_FILE_PATH}")
    app.run(port=5000)