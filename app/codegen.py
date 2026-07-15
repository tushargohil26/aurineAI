import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .config import get_settings
from .llm import chat_completion


MAX_FILES = 40
MAX_FILE_CHARS = 30000


def is_website_request(prompt: str) -> bool:
    text = prompt.lower()
    return bool(re.search(r"\b(website|web site|landing page|site|webpage|portfolio|restaurant|shop|saas|dashboard|blog|store|agency|clinic|school|gym|real estate|fitness)\b", text))


def enhanced_project_prompt(prompt: str) -> str:
    if not is_website_request(prompt):
        return prompt
    return f"""
USER REQUEST:
{prompt}

Aurine quality upgrade:
Build this as a premium, production-style website, not a basic demo.
Even if the prompt is vague, infer a polished concept and deliver a complete high-tech result.

Website requirements:
- Create a full responsive website with semantic HTML, advanced CSS, and real JavaScript interactions.
- Include at least 6 sections when relevant: immersive hero, features/services, showcase/gallery/cards, process/about, testimonials/stats, FAQ/contact/footer.
- Use a strong visual system: modern layout, glass/metal/neon accents, rich typography, spacing, hover states, responsive grids, mobile navigation.
- Include realistic domain-specific content, not placeholder lorem ipsum.
- Include interactive behavior: mobile menu, filter/tabs/carousel, form validation, smooth scrolling, theme/animation controls.
- Include assets as code-native gradients/SVG/CSS shapes. Do not depend on unknown remote assets.
- Must be previewable directly from index.html without a build step.
- Return multiple files: index.html, styles.css, script.js, README.md.
"""


def advanced_website_fallback(prompt: str) -> dict:
    topic = re.sub(r"\s+", " ", prompt.strip()) or "premium website"
    safe_topic = topic.replace("<", "").replace(">", "")
    name = safe_project_name(safe_topic)
    title = website_title_from_prompt(safe_topic)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <header class="site-header">
    <a class="brand" href="#top"><span></span>{title}</a>
    <button class="nav-toggle" aria-label="Toggle menu">Menu</button>
    <nav>
      <a href="#features">Features</a>
      <a href="#showcase">Showcase</a>
      <a href="#process">Process</a>
      <a href="#contact">Contact</a>
    </nav>
  </header>

  <main id="top">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Aurine premium build</p>
        <h1>{title} that feels engineered, alive, and ready to launch.</h1>
        <p class="lead">A high-tech responsive website generated from: <strong>{safe_topic}</strong>. It includes polished sections, interactive UI, and production-minded structure.</p>
        <div class="actions">
          <a class="primary" href="#contact">Start now</a>
          <a class="secondary" href="#showcase">View experience</a>
        </div>
      </div>
      <div class="hero-visual" aria-label="Interactive visual">
        <div class="orbit one"></div><div class="orbit two"></div><div class="panel">
          <strong>Live System</strong><span>Responsive</span><span>Interactive</span><span>Accessible</span>
        </div>
      </div>
    </section>

    <section id="features" class="section">
      <div class="section-head"><p class="eyebrow">Capabilities</p><h2>Built beyond a basic template</h2></div>
      <div class="feature-grid">
        <article><h3>Premium UI</h3><p>Layered visual hierarchy, fluid grids, modern color, and careful spacing.</p></article>
        <article><h3>Real Interactions</h3><p>Mobile navigation, scroll reveal, smart filters, and validated contact flow.</p></article>
        <article><h3>Responsive Core</h3><p>Designed for phones, tablets, desktops, and wide screens without layout breaks.</p></article>
        <article><h3>Launch Ready</h3><p>Clean files, readable structure, and simple preview through index.html.</p></article>
      </div>
    </section>

    <section id="showcase" class="section split">
      <div><p class="eyebrow">Showcase</p><h2>Interactive content cards</h2><p>Use the filters to preview how this site presents services, offers, products, or portfolio items.</p></div>
      <div class="filters">
        <button class="active" data-filter="all">All</button><button data-filter="design">Design</button><button data-filter="growth">Growth</button><button data-filter="tech">Tech</button>
      </div>
      <div class="card-grid">
        <article data-kind="design"><span>Design</span><h3>Immersive first impression</h3><p>Hero, visual depth, and strong CTA structure.</p></article>
        <article data-kind="growth"><span>Growth</span><h3>Conversion focused flow</h3><p>Sections arranged for trust, clarity, and action.</p></article>
        <article data-kind="tech"><span>Tech</span><h3>Fast static architecture</h3><p>No heavy dependencies required for preview.</p></article>
      </div>
    </section>

    <section id="process" class="section timeline">
      <p class="eyebrow">Process</p><h2>How the experience works</h2>
      <ol><li>Clarify the offer</li><li>Present value with rich UI</li><li>Build trust with proof</li><li>Capture leads with validation</li></ol>
    </section>

    <section class="section stats">
      <div><strong>100%</strong><span>Responsive</span></div><div><strong>6+</strong><span>Sections</span></div><div><strong>0</strong><span>Build steps</span></div>
    </section>

    <section id="contact" class="section contact">
      <div><p class="eyebrow">Contact</p><h2>Ready to customize</h2><p>Edit the content, colors, and sections to match the final brand.</p></div>
      <form id="contactForm"><input placeholder="Name" required /><input type="email" placeholder="Email" required /><textarea placeholder="Project details" required></textarea><button>Send request</button><p class="form-status"></p></form>
    </section>
  </main>

  <footer>Built by Aurine AI Assistant</footer>
  <script src="script.js"></script>
</body>
</html>"""
    css = """*{box-sizing:border-box}body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#071016;color:#ecfeff}a{color:inherit;text-decoration:none}.site-header{position:sticky;top:0;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:18px clamp(18px,4vw,58px);background:rgba(7,16,22,.78);backdrop-filter:blur(18px);border-bottom:1px solid rgba(125,211,252,.18)}.brand{font-weight:900;letter-spacing:.02em;display:flex;gap:10px;align-items:center}.brand span{width:14px;height:14px;border-radius:50%;background:#2dd4bf;box-shadow:0 0 28px #2dd4bf}nav{display:flex;gap:22px;color:#c7e7ef}.nav-toggle{display:none}.hero{min-height:86vh;display:grid;grid-template-columns:1.08fr .92fr;gap:42px;align-items:center;padding:clamp(42px,7vw,92px) clamp(18px,5vw,74px);background:radial-gradient(circle at 80% 20%,rgba(45,212,191,.24),transparent 28%),linear-gradient(135deg,#071016,#10232d 48%,#201246)}.eyebrow{color:#67e8f9;text-transform:uppercase;font-weight:900;font-size:13px;letter-spacing:.16em}.hero h1{font-size:clamp(42px,7vw,86px);line-height:.96;margin:0 0 22px}.lead{font-size:clamp(18px,2vw,23px);line-height:1.65;color:#c6dce7;max-width:760px}.actions{display:flex;gap:14px;flex-wrap:wrap;margin-top:28px}.primary,.secondary,form button{border:0;border-radius:12px;padding:14px 18px;font-weight:900;cursor:pointer}.primary,form button{background:#5eead4;color:#042017}.secondary{border:1px solid rgba(255,255,255,.24);background:rgba(255,255,255,.08)}.hero-visual{min-height:460px;position:relative;display:grid;place-items:center}.panel{width:min(390px,90%);padding:28px;border:1px solid rgba(125,211,252,.28);border-radius:22px;background:linear-gradient(145deg,rgba(255,255,255,.14),rgba(255,255,255,.04));box-shadow:0 34px 120px rgba(0,0,0,.4);display:grid;gap:16px}.panel span{padding:14px;border-radius:12px;background:rgba(7,16,22,.6)}.orbit{position:absolute;border:1px solid rgba(94,234,212,.45);border-radius:50%;animation:spin 16s linear infinite}.orbit.one{width:340px;height:340px;top:-40px;right:-40px}.orbit.two{width:240px;height:240px;bottom:-20px;left:-20px;animation-direction:reverse;animation-duration:12s}@keyframes spin{to{transform:rotate(360deg)}}.section{padding:clamp(42px,8vw,100px) clamp(18px,5vw,74px)}.section-head{text-align:center;margin-bottom:42px}.feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:22px}.feature-grid article{padding:28px;border-radius:18px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08)}.feature-grid h3{margin:0 0 8px;color:#5eead4}.split{display:grid;grid-template-columns:1fr 1fr;gap:38px;align-items:start}.filters{display:flex;gap:10px;margin-bottom:20px}.filters button{padding:8px 16px;border-radius:999px;border:1px solid rgba(255,255,255,.2);background:transparent;color:#c7e7ef;cursor:pointer}.filters button.active{background:#5eead4;color:#042017}.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px}.card-grid article{padding:22px;border-radius:16px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08)}.card-grid span{color:#5eead4;font-size:12px;text-transform:uppercase}.timeline ol{list-style:none;padding:0;counter-reset:step;display:grid;gap:18px}.timeline li{counter-increment:step;padding:18px;border-radius:14px;background:rgba(255,255,255,.05);border-left:3px solid #5eead4}.timeline li::before{content:counter(step);display:inline-flex;width:32px;height:32px;align-items:center;justify-content:center;border-radius:50%;background:#5eead4;color:#042017;font-weight:900;margin-right:12px}.stats{display:flex;justify-content:center;gap:48px;text-align:center;padding:60px 0}.stats strong{display:block;font-size:clamp(36px,5vw,56px);color:#5eead4}.contact{display:grid;grid-template-columns:1fr 1fr;gap:42px;align-items:start}form{display:grid;gap:14px}form input,form textarea{padding:14px;border-radius:12px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.06);color:#ecfeff;font-size:16px}form textarea{min-height:120px;resize:vertical}.form-status{margin-top:8px;color:#5eead4}footer{text-align:center;padding:28px;border-top:1px solid rgba(255,255,255,.08);color:#6b8a9e;font-size:14px}.reveal{opacity:0;transform:translateY(24px);transition:opacity .6s,transform .6s}.reveal.visible{opacity:1;transform:none}@media(max-width:768px){.hero{grid-template-columns:1fr}.hero-visual{display:none}.split{grid-template-columns:1fr}.contact{grid-template-columns:1fr}.nav-toggle{display:block;background:transparent;border:0;color:#c7e7ef;font-size:18px;cursor:pointer}.site-header.open nav{display:flex;flex-direction:column;gap:14px;padding:18px 0}nav{display:none}}"""
    js = """const header=document.querySelector('.site-header');document.querySelector('.nav-toggle').onclick=()=>header.classList.toggle('open');document.querySelectorAll('a[href^="#"]').forEach(a=>a.onclick=e=>{e.preventDefault();document.querySelector(a.getAttribute('href'))?.scrollIntoView({behavior:'smooth'});header.classList.remove('open')});const cards=[...document.querySelectorAll('[data-kind]')];document.querySelectorAll('[data-filter]').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('[data-filter]').forEach(b=>b.classList.remove('active'));btn.classList.add('active');const f=btn.dataset.filter;cards.forEach(c=>c.style.display=f==='all'||c.dataset.kind===f?'block':'none')});const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('visible')}),{threshold:.14});document.querySelectorAll('.section article,.timeline li,.stats div').forEach(el=>{el.classList.add('reveal');io.observe(el)});document.querySelector('#contactForm').onsubmit=e=>{e.preventDefault();e.currentTarget.querySelector('.form-status').textContent='Request captured locally. Customize this form endpoint before launch.'};"""
    readme = f"""# {title}

Premium static website generated by Aurine AI Assistant.

## Preview
Open `index.html` directly in a browser or use Aurine Preview.

## Files
- `index.html` - semantic site structure
- `styles.css` - responsive premium visual system
- `script.js` - interactions, filters, reveal animation, form validation
"""
    return {
        "name": name,
        "description": f"Premium responsive website for {safe_topic}",
        "run_instructions": "Open index.html in a browser. No build step required.",
        "files": [
            {"path": "index.html", "content": html},
            {"path": "styles.css", "content": css},
            {"path": "script.js", "content": js},
            {"path": "README.md", "content": readme},
        ],
    }


def website_title_from_prompt(prompt: str) -> str:
    text = re.sub(r"\s+", " ", prompt.strip())
    name_match = re.search(r"\bfor\s+([A-Z][a-zA-Z0-9_-]{1,24})\b", text)
    lower = text.lower()
    if "portfolio" in lower:
        person = name_match.group(1) if name_match else "Developer"
        return f"{person} Developer Portfolio"
    if "restaurant" in lower:
        return "Premium Restaurant Experience"
    if "saas" in lower or "dashboard" in lower:
        return "High Tech SaaS Platform"
    if "store" in lower or "shop" in lower or "ecommerce" in lower:
        return "Modern E-Commerce Store"
    if "blog" in lower:
        return "Creative Blog Platform"
    if "agency" in lower:
        return "Digital Agency Website"
    if "clinic" in lower or "hospital" in lower:
        return "Healthcare Platform"
    cleaned = re.sub(
        r"\b(create|make|build|generate|banao|website|web site|landing page|premium|advanced|high tech|responsive|with|for)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    words = re.findall(r"[a-zA-Z0-9]+", cleaned)[:4]
    return " ".join(word.capitalize() for word in words) or "Aurine Premium Website"


def is_basic_website_payload(payload: dict) -> bool:
    files = payload.get("files", [])
    if not isinstance(files, list):
        return True
    paths = {str(item.get("path", "")).lower() for item in files if isinstance(item, dict)}
    if not {"index.html", "styles.css", "script.js"}.issubset(paths):
        return True
    combined = "\n".join(str(item.get("content", "")) for item in files if isinstance(item, dict))
    if len(combined) < 9000:
        return True
    html = next((str(item.get("content", "")) for item in files if str(item.get("path", "")).lower() == "index.html"), "")
    section_count = len(re.findall(r"<section\b", html, flags=re.IGNORECASE))
    interactive_markers = ["addEventListener", "IntersectionObserver", "data-filter", "querySelector", "onsubmit"]
    if section_count < 5:
        return True
    if not any(marker in combined for marker in interactive_markers):
        return True
    return False


def normalized_payload_files(payload: dict, original_prompt: str) -> list[dict]:
    files = payload.get("files", [])
    if not isinstance(files, list):
        if is_website_request(original_prompt):
            return advanced_website_fallback(original_prompt)["files"]
        raise ValueError("The model returned an invalid files list.")

    normalized: list[dict] = []
    for index, item in enumerate(files):
        if isinstance(item, dict):
            path = str(item.get("path") or f"file-{index + 1}.txt")
            content = str(item.get("content") or "")
            normalized.append({"path": path, "content": content})
        elif isinstance(item, str) and item.strip():
            normalized.append({"path": f"model-output-{index + 1}.txt", "content": item})

    if not normalized:
        if is_website_request(original_prompt):
            return advanced_website_fallback(original_prompt)["files"]
        raise ValueError("The model did not return any project files.")
    return normalized

def safe_project_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip().lower()).strip("-")
    return cleaned[:60] or "ai-project"


def safe_project_id(project_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", project_id.strip()).strip("-")
    if not cleaned:
        raise FileNotFoundError("Project not found.")
    return cleaned


def safe_relative_path(path: str) -> Path:
    path = path.replace("\\", "/").strip().lstrip("/")
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe file path: {path}")
    return candidate


def projects_root() -> Path:
    settings = get_settings()
    settings.generated_projects_dir.mkdir(parents=True, exist_ok=True)
    return settings.generated_projects_dir


def project_summary(project_dir: Path) -> dict:
    files = [
        str(path.relative_to(project_dir)).replace("\\", "/")
        for path in project_dir.rglob("*")
        if path.is_file() and path.name != "project.json"
    ]
    metadata_path = project_dir / "project.json"
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return {
        "id": project_dir.name,
        "name": metadata.get("name", project_dir.name),
        "description": metadata.get("description", ""),
        "run_instructions": metadata.get("run_instructions", ""),
        "preview_path": preview_path(files),
        "created_at": metadata.get("created_at", ""),
        "prompt": metadata.get("prompt", ""),
        "files": files,
    }


def list_projects() -> list[dict]:
    root = projects_root()
    projects = [project_summary(path) for path in root.iterdir() if path.is_dir()]
    return sorted(projects, key=lambda item: item.get("created_at", ""), reverse=True)


def generate_project(prompt: str) -> dict:
    effective_prompt = enhanced_project_prompt(prompt)
    system_prompt = (
        "You are Aurine's elite full-stack coding agent with expert-level practical skill across all programming languages and frameworks.\n"
        "Generate a complete, polished, runnable code project from the user's request.\n"
        "Understand Hindi, Hinglish, English, mixed-language prompts, and misspelled words by inferring the user's intent.\n"
        "Support: websites, apps, dashboards, APIs, games, automation, data pipelines, ML models, "
        "Docker deployments, CI/CD, browser extensions, mobile apps, smart contracts — EVERYTHING.\n"
        "Return only valid JSON: {\"name\":\"project-name\",\"description\":\"short description\","
        "\"run_instructions\":\"how to run\",\"files\":[{\"path\":\"relative/path\",\"content\":\"file content\"}]}.\n"
        "RULES:\n"
        "1. Write COMPLETE, RUNNABLE code — no placeholders, no TODOs\n"
        "2. Include ALL imports, dependencies, error handling\n"
        "3. Use proper types, naming, and structure\n"
        "4. Include index.html for any frontend work\n"
        "5. Include README.md with setup and run instructions\n"
        "6. Add responsive UI, real interactions, professional design\n"
        "7. For backend: include config, validation, auth, error handling\n"
        "8. If the request is ambiguous, choose a sensible complete implementation\n"
        "9. Max 40 files, keep paths relative\n"
        "10. Never include secrets or overwrite system files\n"
        "11. Prefer modern UX, accessibility, validation, loading/error states, and useful sample data\n"
        "12. Include a previewable HTML entry point whenever the project has a frontend\n"
        "13. For websites, build a premium high-tech site with multiple sections, polished styling, and JavaScript interactions\n"
        "14. Website output must include index.html, styles.css, script.js, README.md and be directly previewable\n"
        "15. If the user gives a short prompt, enrich it with sensible domain-specific content and advanced UI\n"
        "16. For API projects: include OpenAPI/Swagger docs, proper error handling, rate limiting\n"
        "17. For ML projects: include training scripts, model saving, prediction examples\n"
        "18. Always include realistic sample data and test cases"
    )
    try:
        content = chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": effective_prompt},
            ],
            temperature=0.25,
            json_mode=True,
        )
        payload = json.loads(content or "{}")
    except Exception:
        if not is_website_request(prompt):
            raise
        payload = advanced_website_fallback(prompt)

    if is_website_request(prompt) and is_basic_website_payload(payload):
        payload = advanced_website_fallback(prompt)

    files = normalized_payload_files(payload, prompt)
    if len(files) > MAX_FILES:
        files = files[:MAX_FILES]

    name = safe_project_name(str(payload.get("name") or "ai-project"))
    project_id = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{name}-{uuid4().hex[:6]}"
    project_dir = projects_root() / project_id
    project_dir.mkdir(parents=True, exist_ok=False)

    written_files: list[str] = []
    for file_item in files:
        relative = safe_relative_path(str(file_item.get("path") or "README.md"))
        content = str(file_item.get("content") or "")
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n\n/* Truncated by generator size limit. */\n"
        target = project_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written_files.append(str(relative).replace("\\", "/"))

    metadata = {
        "id": project_id,
        "name": name,
        "description": str(payload.get("description") or ""),
        "run_instructions": str(payload.get("run_instructions") or ""),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "files": written_files,
        "prompt": effective_prompt,
    }
    (project_dir / "project.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return project_summary(project_dir) | {"run_instructions": metadata["run_instructions"]}


def get_project_dir(project_id: str) -> Path:
    root = projects_root()
    project_dir = root / safe_project_id(project_id)
    if not project_dir.exists() or not project_dir.is_dir():
        legacy = safe_project_name(project_id)
        matches = [path for path in root.iterdir() if path.is_dir() and path.name.startswith(legacy)]
        if len(matches) == 1:
            return matches[0]
        raise FileNotFoundError("Project not found.")
    return project_dir


def preview_path(files: list[str]) -> str:
    candidates = ["index.html", "public/index.html", "dist/index.html", "src/index.html"]
    lower_map = {item.lower(): item for item in files}
    for candidate in candidates:
        if candidate in lower_map:
            return lower_map[candidate]
    for item in files:
        if item.lower().endswith(".html"):
            return item
    return ""


def list_project_files(project_id: str) -> list[str]:
    project_dir = get_project_dir(project_id)
    return [
        str(path.relative_to(project_dir)).replace("\\", "/")
        for path in project_dir.rglob("*")
        if path.is_file() and path.name != "project.json"
    ]


def read_project_file(project_id: str, file_path: str) -> dict:
    project_dir = get_project_dir(project_id)
    relative = safe_relative_path(file_path)
    target = (project_dir / relative).resolve()
    if not str(target).startswith(str(project_dir.resolve())) or not target.is_file():
        raise FileNotFoundError("File not found.")
    return {"path": str(relative).replace("\\", "/"), "content": target.read_text(encoding="utf-8", errors="ignore")}


def write_project_file(project_id: str, file_path: str, content: str) -> dict:
    project_dir = get_project_dir(project_id)
    relative = safe_relative_path(file_path)
    target = (project_dir / relative).resolve()
    if not str(target).startswith(str(project_dir.resolve())):
        raise ValueError("Unsafe file path.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(relative).replace("\\", "/"), "saved": True}


def run_project_command(project_id: str, command: str) -> dict:
    blocked = ["rm ", "del ", "format ", "git reset", "rmdir ", "remove-item", "shutdown", "mkfs"]
    if any(item in command.lower() for item in blocked):
        raise ValueError("Blocked destructive command.")
    project_dir = get_project_dir(project_id)
    result = subprocess.run(
        command,
        cwd=project_dir,
        shell=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    output = (result.stdout + result.stderr).strip()
    return {"exit_code": result.returncode, "output": output[:40000] or f"Command exited with code {result.returncode}."}


def project_zip_path(project_id: str) -> Path:
    project_dir = get_project_dir(project_id)
    zip_path = projects_root() / f"{project_dir.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in project_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(project_dir))
    return zip_path


def delete_project(project_id: str) -> None:
    project_dir = get_project_dir(project_id)
    if project_dir.exists() and project_dir.is_dir():
        shutil.rmtree(project_dir)
