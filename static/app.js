const q = (s) => document.querySelector(s);
const tokenKey = "Aurine_auth_token";

const loginScreen = q("#loginScreen");
const appShell = q("#appShell");
const loginForm = q("#loginForm");
const loginStatus = q("#loginStatus");
const demoLoginButton = q("#demoLoginButton");
const googleLoginButton = q("#googleLoginButton");
const loginName = q("#loginName");
const loginEmail = q("#loginEmail");
const loginPassword = q("#loginPassword");
const chatList = q("#chatList");
const agentRailList = q("#agentRailList");
const pluginRailList = q("#pluginRailList");
const browsePluginsButton = q("#browsePluginsButton");
const browsePluginsRow = q("#browsePluginsRow");
const browseAgentsButton = q("#browseAgentsButton");
const browseAgentsRow = q("#browseAgentsRow");
const messages = q("#messages");
const emptyState = q("#emptyState");
const homePluginGrid = q("#homePluginGrid");
const pluginsPage = q("#pluginsPage");
const agentsPage = q("#agentsPage");
const modelsPage = q("#modelsPage");
const apiKeysPage = q("#apiKeysPage");
const chatForm = q("#chatForm");
const floatingChatForm = q("#floatingChatForm");
const questionInput = q("#questionInput");
const floatingQuestionInput = q("#floatingQuestionInput");
const newChatButton = q("#newChatButton");
const clearDataButton = q("#clearDataButton");
const logoutButton = q("#logoutButton");
const composerModelButton = q("#composerModelButton");
const floatingModelButton = q("#floatingModelButton");
const fileInput = q("#fileInput");
const folderInput = q("#folderInput");
const fileInputInline = q("#fileInputInline");
const floatingFileInput = q("#floatingFileInput");
const agentChip = q("#agentChip");
const agentChipText = q("#agentChipText");
const floatingAgentChip = q("#floatingAgentChip");
const floatingAgentChipText = q("#floatingAgentChipText");
const cloudPanel = q("#cloudPanel");
const panelTitle = q("#panelTitle");
const panelBody = q("#panelBody");
const closePanel = q("#closePanel");
const workspaceButton = q("#workspaceButton");
const workspaceName = q("#workspaceName");
const workspaceUser = q("#workspaceUser");
const workspaceAvatar = q("#workspaceAvatar");
const topWorkspaceName = q("#topWorkspaceName");
const topMode = q("#topMode");
const settingsModal = q("#settingsModal");
const settingsForm = q("#settingsForm");
const modelModal = q("#modelModal");
const modelForm = q("#modelForm");
const agentCreateModal = q("#agentCreateModal");
const createAgentForm = q("#createAgentForm");
const closeAgentCreate = q("#closeAgentCreate");
const settingsName = q("#settingsName");
const settingsWorkspace = q("#settingsWorkspace");
const settingsTheme = q("#settingsTheme");
const closeSettings = q("#closeSettings");
const workspacePanel = q("#workspacePanel");
const workspaceTitle = q("#workspaceTitle");
const workspaceSubtitle = q("#workspaceSubtitle");
const workspaceFiles = q("#workspaceFiles");
const fileSelect = q("#fileSelect");
const fileEditor = q("#fileEditor");
const saveFileButton = q("#saveFileButton");
const closeWorkspace = q("#closeWorkspace");
const commandForm = q("#commandForm");
const commandInput = q("#commandInput");
const terminalOutput = q("#terminalOutput");
const previewPanel = q("#previewPanel");
const previewTitle = q("#previewTitle");
const previewFrame = q("#previewFrame");
const closePreview = q("#closePreview");
const settingsPage = q("#settingsPage");

let authToken = localStorage.getItem(tokenKey) || sessionStorage.getItem(tokenKey) || "";
let profile = null;
let chats = [];
let customAgents = [];
let activeChatId = null;
let activeProject = null;
let activeFile = "";
let lastArtifactId = "";
let pluginsCache = [];
let activePluginId = "";
let activeAgentsFilter = "";
let activeModelsFilter = "";
const modelSettingsKey = "Aurine_model_settings";
const customModelsKey = "Aurine_custom_models";
const nativeModelMigrationKey = "Aurine_native_model_default_v1";
const uploadAcceptTypes = [
  ".pdf", ".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".xml",
  ".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".py", ".java", ".kt", ".swift",
  ".go", ".rs", ".php", ".rb", ".c", ".cpp", ".cs", ".sql", ".sh", ".ps1", ".bat",
  ".log", ".docx", ".xlsx", ".zip", ".png", ".jpg", ".jpeg", ".webp", ".gif",
  ".svg", ".bmp", ".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v", ".mp3", ".wav",
  ".ogg", ".flac"
].join(",");

const MODEL_PRESETS = [
  { id: "aurine-native", label: "Aurine Native", provider: "aurine", model: "aurine-native", baseUrl: "" },
  { id: "aurine-coder", label: "Aurine Coder", provider: "aurine", model: "aurine-coder", baseUrl: "" },
  { id: "aurine-qwen", label: "Aurine Qwen Core", provider: "aurine", model: "qwen2.5-coder:7b", baseUrl: "" },
  { id: "aurine-llama", label: "Aurine Llama Core", provider: "aurine", model: "llama3.3", baseUrl: "" },
  { id: "aurine-reasoner", label: "Aurine Reasoner", provider: "aurine", model: "deepseek-r1", baseUrl: "" },
  { id: "openai-gpt4o-mini", label: "OpenAI GPT-4o mini", provider: "openai", model: "gpt-4o-mini", baseUrl: "" },
  { id: "openai-gpt4o", label: "OpenAI GPT-4o", provider: "openai", model: "gpt-4o", baseUrl: "" },
  { id: "codex", label: "Codex / OpenAI coding", provider: "codex", model: "gpt-4o", baseUrl: "" },
  { id: "claude-sonnet", label: "Claude Sonnet 4.6", provider: "anthropic", model: "claude-sonnet-4-6", baseUrl: "" },
  { id: "kimi-moonshot", label: "Kimi Moonshot V1", provider: "kimi", model: "moonshot-v1-8k", baseUrl: "https://api.moonshot.ai/v1" },
  { id: "openrouter-auto", label: "OpenRouter Auto", provider: "openrouter", model: "openrouter/auto", baseUrl: "https://openrouter.ai/api/v1" },
  { id: "groq-llama-31-8b", label: "Groq Llama 3.1 8B", provider: "groq", model: "llama-3.1-8b-instant", baseUrl: "https://api.groq.com/openai/v1" },
  { id: "groq-llama-33-70b", label: "Groq Llama 3.3 70B", provider: "groq", model: "llama-3.3-70b-versatile", baseUrl: "https://api.groq.com/openai/v1" },
  { id: "groq-gpt-oss-120b", label: "Groq GPT-OSS 120B", provider: "groq", model: "openai/gpt-oss-120b", baseUrl: "https://api.groq.com/openai/v1" },
  { id: "groq-gpt-oss-20b", label: "Groq GPT-OSS 20B", provider: "groq", model: "openai/gpt-oss-20b", baseUrl: "https://api.groq.com/openai/v1" },
  { id: "groq-llama-31-70b", label: "Groq Llama 3.1 70B", provider: "groq", model: "llama-3.1-70b-versatile", baseUrl: "https://api.groq.com/openai/v1" },
  { id: "groq-mixtral-8x7b", label: "Groq Mixtral 8x7B", provider: "groq", model: "mixtral-8x7b-32768", baseUrl: "https://api.groq.com/openai/v1" },
  { id: "groq-gemma2-9b", label: "Groq Gemma 2 9B", provider: "groq", model: "gemma2-9b-it", baseUrl: "https://api.groq.com/openai/v1" },
  { id: "local-llama-cpp", label: "Local Server: llama.cpp", provider: "custom", model: "local-model", baseUrl: "http://127.0.0.1:8080/v1" },
  { id: "local-lm-studio", label: "Local Server: LM Studio", provider: "custom", model: "local-model", baseUrl: "http://127.0.0.1:1234/v1" },
  { id: "local-vllm", label: "Local Server: vLLM", provider: "custom", model: "local-model", baseUrl: "http://127.0.0.1:8000/v1" },
  { id: "custom", label: "Custom model", provider: "custom", model: "", baseUrl: "" },
];

const QUICK_MODEL_IDS = [
  "aurine-native",
  "aurine-coder",
  "aurine-reasoner",
  "openai-gpt4o-mini",
  "openai-gpt4o",
  "claude-sonnet",
  "kimi-moonshot",
  "openrouter-auto",
  "groq-llama-33-70b",
  "groq-gpt-oss-120b",
  "local-lm-studio",
];

const MODE = {
  general: "Answer as Aurine, a Codex-style cloud workspace assistant. Do not invent facts, links, files, credentials, or execution results.",
  code: "Act as a coding agent. Give exact files, code, commands, tests, and verification. Do not claim work was done unless it was actually created in the workspace.",
  debug: "Act as a debug agent. Find causes, fixes, and verification commands. Say when evidence is missing.",
  app: "Act as an app/software builder. Prefer creating a real project when the user asks to build, create, make, generate, or scaffold software.",
  data: "Act as a data analytics agent. Include metrics, SQL/Python, charts, and insights.",
  migration: "Act as a data migration agent. Include mapping, validation, rollback, scripts, checklist.",
  image: "Create a real image artifact file. Do not only write a prompt.",
  video: "Create a real video-scene artifact file. Do not only write a prompt.",
  pdf: "Create a real PDF artifact file when the user asks for documents or reports.",
  rag: "Use uploaded files first, cite available chunks, and say clearly when the file does not contain the answer.",
  swarm: "Coordinate the task as a Ruflo-style agent swarm and execute practical workspace steps.",
  testgen: "Generate concrete tests, test files, commands, and expected results.",
  security: "Audit for security risks, exact fixes, and verification steps.",
  docs: "Create clear documentation, README content, examples, and release notes.",
};

const AGENTS = [
  { id: "general", name: "Ask Aurine", detail: "Normal chat without a pinned specialist." },
  { id: "code", name: "Coding agent", detail: "Files, code, commands, tests, and verification." },
  { id: "debug", name: "Debug agent", detail: "Find causes, fixes, and proof." },
  { id: "app", name: "App builder", detail: "Create real projects and runnable apps." },
  { id: "image", name: "Image creator", detail: "Create real image artifacts." },
  { id: "video", name: "Video creator", detail: "Create video scene/storyboard artifacts." },
  { id: "pdf", name: "PDF creator", detail: "Create real PDF documents." },
  { id: "data", name: "Data analytics", detail: "Metrics, SQL/Python, charts, and insights." },
  { id: "migration", name: "Data migration", detail: "Mapping, validation, rollback, scripts." },
  { id: "rag", name: "RAG memory", detail: "Uploaded-file answers and citations." },
  { id: "swarm", name: "Ruflo swarm", detail: "Coordinator mode for multi-agent work." },
  { id: "testgen", name: "Test generator", detail: "Missing tests and coverage plans." },
  { id: "security", name: "Security audit", detail: "Risks, fixes, and verification." },
  { id: "docs", name: "Docs agent", detail: "README, API docs, and release notes." },
  { id: "repo-web-research", name: "Web Research Agent", detail: "Research topics and synthesize structured reports.", industry: "General", framework: "LangGraph", instructions: "Act as a web research agent. Build a concise research report, separate verified facts from assumptions, and include search/query suggestions when live browsing is not available." },
  { id: "repo-code-review", name: "Code Review Agent", detail: "Review code for bugs, security, performance, and style.", industry: "Software Dev", framework: "LangChain", instructions: "Act as an expert code reviewer. Prioritize correctness, security, performance, maintainability, and missing tests. Give concrete file-level fixes." },
  { id: "repo-pdf-qa", name: "PDF Q&A Agent", detail: "Answer questions over PDF or uploaded documents.", industry: "Research", framework: "LlamaIndex", instructions: "Act as a PDF Q&A agent. Use uploaded document context first, cite what is present, and clearly say when the answer is not in the document." },
  { id: "repo-sql-query", name: "SQL Query Agent", detail: "Turn questions into SQL and explain results.", industry: "Data", framework: "LangChain", instructions: "Act as a SQL query agent. Write safe SQL, explain tables/assumptions, avoid destructive queries unless explicitly requested, and include validation steps." },
  { id: "repo-email-drafting", name: "Email Drafting Agent", detail: "Draft professional email responses and campaigns.", industry: "Communication", framework: "CrewAI", instructions: "Act as an email drafting agent. Extract intent, audience, tone, and desired outcome, then write polished email drafts with subject lines." },
  { id: "repo-news-summarizer", name: "News Summarizer Agent", detail: "Summarize news topics and key developments.", industry: "Media", framework: "LangChain", instructions: "Act as a news summarizer. Separate recent facts from background, flag uncertainty, and provide concise bullet summaries." },
  { id: "repo-github-triager", name: "GitHub Issue Triager", detail: "Classify issues, severity, labels, and next actions.", industry: "DevOps", framework: "LangGraph", instructions: "Act as a GitHub issue triager. Identify bug/feature/question, severity, reproduction gaps, labels, owner suggestions, and next debugging steps." },
  { id: "repo-data-analysis", name: "Data Analysis Agent", detail: "Analyze datasets, metrics, trends, and charts.", industry: "Analytics", framework: "LangChain", instructions: "Act as a data analysis agent. Propose metrics, Python/SQL steps, charts, caveats, and interpretation." },
  { id: "repo-resume-parser", name: "Resume Parser Agent", detail: "Extract resume skills, experience, fit, and gaps.", industry: "HR", framework: "LangChain", instructions: "Act as a resume parser. Extract structured profile, strengths, gaps, role fit, and interview signals." },
  { id: "repo-meeting-notes", name: "Meeting Notes Agent", detail: "Create meeting summaries, decisions, and action items.", industry: "Productivity", framework: "LangChain", instructions: "Act as a meeting notes agent. Produce summary, decisions, action items with owners/dates, risks, and follow-ups." },
  { id: "repo-stock-research", name: "Stock Research Agent", detail: "Research companies, tickers, and market narratives.", industry: "Finance", framework: "LangChain", instructions: "Act as a stock research agent. Avoid financial advice, distinguish data from opinion, and include risks, catalysts, and verification needs." },
  { id: "repo-travel-planner", name: "Travel Planner Agent", detail: "Plan itineraries, budgets, and destination research.", industry: "Travel", framework: "CrewAI", instructions: "Act as a travel planner. Build practical itineraries with timing, budget, constraints, and alternatives." },
  { id: "repo-customer-support", name: "Customer Support Agent", detail: "Answer support requests and route escalations.", industry: "Customer Service", framework: "LangGraph", instructions: "Act as a customer support agent. Be concise, empathetic, troubleshoot step-by-step, and escalate when needed." },
  { id: "repo-social-media", name: "Social Media Content Agent", detail: "Generate platform-ready posts and content calendars.", industry: "Marketing", framework: "CrewAI", instructions: "Act as a social media content agent. Create platform-specific copy, hooks, CTAs, and content calendar ideas." },
  { id: "repo-unit-test", name: "Unit Test Generator Agent", detail: "Generate tests and coverage plans.", industry: "Software Dev", framework: "LangChain", instructions: "Act as a unit test generator. Identify behavior, edge cases, fixtures, mocks, and write concrete tests." },
  { id: "repo-documentation", name: "Documentation Writer Agent", detail: "Write READMEs, docs, docstrings, and examples.", industry: "Software Dev", framework: "LangChain", instructions: "Act as a documentation writer. Produce clear README/API docs/examples with accurate commands and setup notes." },
  { id: "repo-recipe", name: "Recipe Recommendation Agent", detail: "Suggest recipes from ingredients and preferences.", industry: "Food", framework: "LangChain", instructions: "Act as a recipe recommendation agent. Consider ingredients, diet, time, serving count, substitutions, and steps." },
  { id: "repo-job-application", name: "Job Application Agent", detail: "Create cover letters, tailored bullets, and interview prep.", industry: "HR", framework: "CrewAI", instructions: "Act as a job application agent. Tailor resume bullets, cover letter, interview questions, and salary research caveats." },
  { id: "repo-competitive-analysis", name: "Competitive Analysis Agent", detail: "Analyze competitors and strategic positioning.", industry: "Business", framework: "LangGraph", instructions: "Act as a competitive analysis agent. Identify competitors, compare positioning, strengths, weaknesses, risks, and strategic moves." },
  { id: "repo-multi-agent-debate", name: "Multi-Agent Debate System", detail: "Debate topics from multiple viewpoints and judge tradeoffs.", industry: "Research", framework: "LangChain", instructions: "Act as a multi-agent debate system. Present pro/con arguments, rebuttals, judge tradeoffs, and finish with a balanced recommendation." },
];

function allAgents() {
  return [...AGENTS, ...customAgents];
}

function agentById(id) {
  return allAgents().find((agent) => agent.id === id) || AGENTS[0];
}

function agentInstruction(id) {
  const agent = agentById(id);
  if (agent.instructions) return agent.instructions;
  return MODE[id] || MODE.general;
}

function currentAgentId() {
  return activeChat()?.agentMode || "general";
}

function modelSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(modelSettingsKey) || "{}");
    if (!localStorage.getItem(nativeModelMigrationKey) && (!saved.presetId || ["openai", "ollama"].includes(saved.provider))) {
      localStorage.setItem(nativeModelMigrationKey, "1");
      const native = MODEL_PRESETS[0];
      const settings = { ...native, presetId: native.id };
      localStorage.setItem(modelSettingsKey, JSON.stringify(settings));
      return settings;
    }
    const preset = [...MODEL_PRESETS, ...customModels()].find((item) => item.id === saved.presetId) || MODEL_PRESETS[0];
    return { ...preset, ...saved };
  } catch {
    return MODEL_PRESETS[0];
  }
}

function customModels() {
  try {
    return JSON.parse(localStorage.getItem(customModelsKey) || "[]");
  } catch {
    return [];
  }
}

function allModelOptions() {
  return [...MODEL_PRESETS, ...customModels()];
}

function quickModelOptions() {
  const all = allModelOptions();
  return QUICK_MODEL_IDS.map((id) => all.find((model) => model.id === id)).filter(Boolean);
}

function saveModelSettings(settings) {
  localStorage.setItem(modelSettingsKey, JSON.stringify(settings));
  renderModelButton();
}

function renderModelButton() {
  const settings = modelSettings();
  const label = settings.label || settings.model || settings.provider || "Model";
  [composerModelButton, floatingModelButton].forEach((button) => {
    if (!button) return;
    button.textContent = label.length > 18 ? `${label.slice(0, 17)}...` : label;
    button.title = `Model: ${label}`;
  });
}

function autoAgentForText(text) {
  const normalized = text.toLowerCase();
  const rules = [
    ["repo-code-review", /\b(review|audit|bug|security|refactor|performance|code quality)\b/],
    ["repo-unit-test", /\b(test|unit test|pytest|jest|coverage|spec)\b/],
    ["repo-documentation", /\b(readme|docs|documentation|docstring|api docs)\b/],
    ["repo-sql-query", /\b(sql|query|database|sqlite|postgres|mysql|table)\b/],
    ["repo-data-analysis", /\b(data|analytics|csv|excel|metric|chart|trend|analysis)\b/],
    ["repo-pdf-qa", /\b(pdf|document|uploaded file|file question)\b|pdf|document ke/i],
    ["repo-github-triager", /\b(github|issue|pull request|pr|triage)\b/],
    ["repo-email-drafting", /\b(email|mail|reply|subject line)\b/],
    ["repo-social-media", /\b(social|instagram|linkedin|twitter|post|content calendar|caption)\b/],
    ["repo-meeting-notes", /\b(meeting|minutes|transcript|action items|notes)\b/],
    ["repo-stock-research", /\b(stock|ticker|market|finance|investment|nvidia|tesla|aapl)\b/],
    ["repo-travel-planner", /\b(travel|trip|itinerary|hotel|flight|destination)\b/],
    ["repo-customer-support", /\b(customer|support|ticket|refund|complaint|escalate)\b/],
    ["repo-resume-parser", /\b(resume|cv|job fit|candidate|skills)\b/],
    ["repo-job-application", /\b(cover letter|job application|interview|salary)\b/],
    ["repo-competitive-analysis", /\b(competitor|competitive|market research|positioning)\b/],
    ["repo-news-summarizer", /\b(news|headlines|current events|summarize news)\b/],
    ["repo-recipe", /\b(recipe|cook|ingredients|diet|meal)\b/],
    ["repo-multi-agent-debate", /\b(debate|pros and cons|compare arguments|for and against)\b/],
    ["repo-web-research", /\b(research|find information|report|sources)\b/],
    ["image", /\b(image|photo|poster|logo|thumbnail)\b|tasveer|image banao/],
    ["video", /\b(video|animation|reel)\b|video banao/],
    ["pdf", /\b(report|invoice|pdf)\b|pdf banao/],
    ["app", /\b(build|create|make|scaffold).*\b(app|website|site|dashboard|api|tool|game|software)\b/],
  ];
  const match = rules.find(([, pattern]) => pattern.test(normalized));
  return match ? match[0] : "general";
}

function setCurrentAgent(agentId) {
  activeChat().agentMode = agentId === "general" ? "" : agentId;
  cloudPanel.hidden = true;
  render();
}

function clearCurrentAgent() {
  activeChat().agentMode = "";
  render();
}

function shouldCreateProject(text) {
  const mode = currentAgentId();
  const normalized = normalizeIntentText(text);
  if (["code", "app"].includes(mode)) return true;
  return /\b(build|create|make|generate|scaffold|develop|banao|bnao|banake|banaye|duild|bild)\b/.test(normalized)
    && /\b(app|web|website|web site|site|dashboard|api|tool|game|software|project|frontend|backend|saas|portfolio|potfolio|developer|devloper)\b/.test(normalized)
    || /\b(website|web site|web portfolio|portfolio|potfolio|dashboard|landing page|restaurant website|react app|mobile app)\b/.test(normalized);
}

function normalizeIntentText(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}\s._-]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isPreviewRequest(text) {
  const normalized = normalizeIntentText(text);
  return /\b(preview|preivw|priview|priew|live view|real preview|localhost|show output|open output)\b/.test(normalized)
    || /\b(show|open|run|give|de|do|dikha|dikhao|dikhana).*\b(preview|preivw|priview|priew|output|site|website)\b/.test(normalized);
}

function isImproveProjectRequest(text) {
  const normalized = normalizeIntentText(text);
  const project = latestProject();
  const improvementWords = /\b(proper|advance|advanced|high tech|premium|pura|full|complete|better|improve|upgrade|enhance|kuch bhi nahi|kuch hai hi nahi|sahi se|accha|acha|animation|animate|animated|motion|transition|different|differet|diffret|new design|design|redesign|badlo|change|modify|update|dalo|add)\b/;
  const projectWords = /\b(project|website|web site|site|app|page|portfolio|design|ui|layout|section|hero|banao|bana|banado|do|redo|again)\b/;
  return improvementWords.test(normalized) && (projectWords.test(normalized) || Boolean(project));
}

function lastBuildPrompt() {
  const ignored = /^(preview|preivw|priview|priew|show|open|run|zip|download|terminal|debug|create it|make it|build it|generate it|kar do|kardo)\b/i;
  const message = [...activeChat().messages]
    .reverse()
    .find((item) => item.role === "user" && item.content && !ignored.test(normalizeIntentText(item.content)));
  return message?.content || "";
}

function fallbackPreviewPrompt() {
  const buildPrompt = lastBuildPrompt();
  if (buildPrompt) return buildPrompt;
  const assistantMessage = [...activeChat().messages]
    .reverse()
    .find((item) => item.role === "assistant" && item.content && item.content.length > 40);
  if (assistantMessage) {
    return `Create a real previewable website project from this previous assistant response. Turn any HTML/CSS/JS instructions into actual files with index.html, styles.css, script.js, and README.md. Make it polished and responsive.\n\n${assistantMessage.content}`;
  }
  return "Create a premium responsive portfolio website with animations, projects, skills, contact form, index.html, styles.css, script.js, and README.md.";
}

function isCreateItRequest(text) {
  return /^(create it|make it|build it|generate it|banao ise|isko banao|isse banao|kar do|kardo)$/i.test(normalizeIntentText(text));
}

function artifactType(text) {
  const normalized = normalizeIntentText(text);
  const mode = currentAgentId();
  if (/\b(zip|archive|bundle)\b/.test(normalized)) return "zip";
  if (mode === "image" || /\b(image|photo|picture|poster|logo|banner|thumbnail|wallpaper|cat|dog)\b/.test(normalized) || /tasveer|billi|photo banao|image banao/.test(normalized)) return "image";
  if (mode === "video" || /\b(video|vidio|reel|shorts|movie|clip)\b/.test(normalized) || /video banao/.test(normalized)) return "video";
  if (mode === "pdf" || /\b(pdf|report|invoice|resume|document)\b/.test(normalized) || /pdf banao|report banao/.test(normalized)) return "pdf";
  if (/\b(excel|xlsx|spreadsheet|sheet)\b/.test(normalized) || /excel banao|sheet banao/.test(normalized)) return "excel";
  if (/\b(markdown|txt|note|file)\b/.test(normalized)) return "document";
  if (lastArtifactId && /\b(change|edit|modify|update|make it|isko|isey|isse)\b/.test(normalized)) return "image";
  return "";
}

function artifactUrl(artifact, file) {
  return `/artifacts/${artifact.id}/download/${encodeURIComponent(file.name)}`;
}

function artifactMessage(artifact) {
  return `Created ${artifact.type}: ${artifact.prompt}`;
}

function projectMessage(project) {
  const files = (project.files || []).slice(0, 10).map((file) => `- ${file}`).join("\n");
  return [
    `Project created: ${project.name}`,
    project.description || "The project files were generated in the workspace.",
    files ? `Files created:\n${files}` : "",
    project.run_instructions ? `Run instructions:\n${project.run_instructions}` : ""
  ].filter(Boolean).join("\n\n");
}

function projectCodeFiles(project) {
  const files = project.files || [];
  const preferred = ["README.md", "index.html", "styles.css", "style.css", "app.js", "script.js", "main.js"];
  const picked = [];
  preferred.forEach((name) => {
    const match = files.find((file) => file.toLowerCase() === name.toLowerCase() || file.toLowerCase().endsWith(`/${name.toLowerCase()}`));
    if (match && !picked.includes(match)) picked.push(match);
  });
  files.forEach((file) => {
    if (picked.length < 3 && /\.(html|css|js|py|md|json)$/i.test(file) && !picked.includes(file)) picked.push(file);
  });
  return picked.slice(0, 3);
}

async function projectChatMessage(project) {
  const snippets = [];
  for (const file of projectCodeFiles(project)) {
    try {
      const data = await api(`/code-projects/${project.id}/files/read?path=${encodeURIComponent(file)}`);
      const content = String(data.content || "").slice(0, 1800);
      const ext = file.split(".").pop()?.toLowerCase() || "";
      snippets.push(`${file}\n\`\`\`${ext}\n${content}${String(data.content || "").length > 1800 ? "\n...trimmed" : ""}\n\`\`\``);
    } catch {
      // Keep the creation response useful even if a snippet cannot be read.
    }
  }
  const code = snippets.length ? `Key implementation files:\n\n${snippets.join("\n\n")}` : "";
  return [projectMessage(project), code].filter(Boolean).join("\n\n");
}

function renderProjectCard(project) {
  if (!project?.id) return "";
  const files = project.files?.length ? `${project.files.length} files` : "Project files";
  return `
    <div class="artifact-card project-card" data-project-card="${escapeHtml(project.id)}">
      <div class="artifact-file project-file">Code project</div>
      <div class="artifact-meta">
        <strong>${escapeHtml(project.name || "Created project")}</strong>
        <span>${escapeHtml(files)}</span>
        <div class="project-actions">
          <button type="button" data-open-chat-project="${escapeHtml(project.id)}">Open</button>
          <button type="button" data-preview-chat-project="${escapeHtml(project.id)}">Preview</button>
          <a class="artifact-download" href="/code-projects/${encodeURIComponent(project.id)}/download" download>Zip</a>
        </div>
      </div>
    </div>`;
}

function renderArtifactCard(artifact) {
  const file = artifact.files?.[0];
  if (!file) return "";
  const href = artifactUrl(artifact, file);
  const preview = file.kind?.startsWith("image/")
    ? `<img class="artifact-preview" src="${href}" alt="${escapeHtml(artifact.prompt)}" />`
    : file.kind === "text/html"
      ? `<iframe class="artifact-preview artifact-frame" src="${href}" title="${escapeHtml(artifact.title)}"></iframe>`
      : `<div class="artifact-file">${escapeHtml(file.name)}</div>`;
  return `
    <div class="artifact-card">
      ${preview}
      <div class="artifact-meta">
        <strong>${escapeHtml(artifact.title || "Created artifact")}</strong>
        <span>${escapeHtml(file.name)}</span>
        <a class="artifact-download" href="${href}" download>Download</a>
      </div>
    </div>`;
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_match, lang, code) => `<pre><code class="language-${lang || "text"}">${code.trim()}</code></pre>`)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br>");
}

function renderMarkdown(text) {
  if (!text) return "";
  if (typeof marked === "undefined") return escapeHtml(text);
  try {
    marked.setOptions({
      breaks: true,
      gfm: true,
      highlight: function(code, lang) {
        if (typeof hljs !== "undefined" && lang && hljs.getLanguage(lang)) {
          try { return hljs.highlight(code, { language: lang }).value; } catch {}
        }
        if (typeof hljs !== "undefined") {
          try { return hljs.highlightAuto(code).value; } catch {}
        }
        return escapeHtml(code);
      },
    });
    const html = marked.parse(text);
    return html;
  } catch {
    return escapeHtml(text);
  }
}

function addCopyButtons(container) {
  container.querySelectorAll("pre").forEach((pre) => {
    if (pre.querySelector(".copy-code-btn")) return;
    const btn = document.createElement("button");
    btn.className = "copy-code-btn";
    btn.type = "button";
    btn.textContent = "Copy";
    btn.onclick = async () => {
      const code = pre.querySelector("code");
      const text = code ? code.textContent : pre.textContent;
      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = "Copy"; }, 2000);
      } catch {
        btn.textContent = "Failed";
        setTimeout(() => { btn.textContent = "Copy"; }, 2000);
      }
    };
    pre.style.position = "relative";
    pre.appendChild(btn);
  });
}

function showApp() {
  loginScreen.hidden = true;
  appShell.hidden = false;
}

function showLogin(message = "") {
  loginScreen.hidden = false;
  appShell.hidden = true;
  loginStatus.textContent = message;
}

function applyProfile(data) {
  profile = data;
  const user = data.user;
  const settings = data.settings || {};
  const label = settings.workspace_name || "Aurine";
  const themeMap = { "aurora-cloud": "aurora-3d", "obsidian-mint": "beauty", "solar-ink": "normal" };
  const theme = themeMap[settings.theme] || settings.theme || "aurora-3d";
  workspaceName.textContent = user.name || "Aurine User";
  topWorkspaceName.textContent = "Aurine";
  workspaceUser.textContent = user.email;
  workspaceAvatar.textContent = (user.name || "A").slice(0, 2).toUpperCase();
  settingsName.value = user.name || "";
  settingsWorkspace.value = label;
  settingsTheme.value = theme;
  document.body.dataset.theme = theme;
}

function createLocalChat(title = "New chat", agentMode = "") {
  const chat = { id: crypto.randomUUID(), title, agentMode, messages: [], createdAt: new Date().toISOString() };
  chats.unshift(chat);
  activeChatId = chat.id;
  return chat;
}

function activeChat() {
  if (!chats.length) createLocalChat();
  return chats.find((chat) => chat.id === activeChatId) || chats[0];
}

function renderChats() {
  chatList.innerHTML = "";
  chats.forEach((chat) => {
    const button = document.createElement("button");
    button.className = `chat-item${chat.id === activeChatId ? " active" : ""}`;
    button.type = "button";
    button.innerHTML = `<span>${escapeHtml(chat.title)}</span><span>now</span>`;
    button.onclick = () => {
      activeChatId = chat.id;
      render();
    };
    chatList.appendChild(button);
  });
}

function renderAgentRail() {
  if (!agentRailList) return;
  agentRailList.innerHTML = "";
  customAgents.forEach((agent) => {
    const button = document.createElement("button");
    button.className = `rail-agent${currentAgentId() === agent.id ? " active" : ""}`;
    button.type = "button";
    button.title = agent.detail || agent.name;
    button.innerHTML = `<span>${escapeHtml(agent.name)}</span><small>${escapeHtml(agent.detail || "Custom agent")}</small>`;
    button.onclick = () => openAgentChat(agent.id);
    agentRailList.appendChild(button);
  });
}

const PLUGIN_ICONS = {
  "git": "G", "github": "GH", "web-search": "W", "code-runner": "C", "file-manager": "F",
  "image-gen": "I", "data-analyzer": "D", "terminal": "T", "database": "DB", "documents": "DOC",
  "media": "M", "sites": "S", "weather": "W", "calculator": "=", "api-tester": "A",
  "system": "SYS", "markdown": "MD", "email-draft": "E", "scheduler": "SCH",
  "ruflo-core": "R", "ruflo-swarm": "RS", "ruflo-autopilot": "RA", "ruflo-goals": "RG",
  "ruflo-testgen": "RT", "ruflo-security": "RS", "ruflo-browser": "RB", "ruflo-cost": "RC",
  "ruflo-observability": "RO", "ruflo-plugin-creator": "RP",
};

const SIDEBAR_PLUGINS = ["git", "github", "web-search", "code-runner", "terminal", "file-manager"];
const HOME_PLUGINS = ["git", "github", "web-search", "code-runner", "terminal", "file-manager", "image-gen", "data-analyzer", "database", "weather", "media", "sites", "api-tester", "system", "email-draft", "scheduler", "documents", "markdown", "calculator"];

async function loadPlugins() {
  try {
    const data = await api("/plugins");
    pluginsCache = data.plugins || [];
  } catch {
    pluginsCache = [];
  }
}

function pluginIcon(pluginId) {
  return PLUGIN_ICONS[pluginId] || (pluginId || "P").slice(0, 2).toUpperCase();
}

function renderPluginRail() {
  if (!pluginRailList) return;
  pluginRailList.innerHTML = "";
  SIDEBAR_PLUGINS.forEach((pid) => {
    const plugin = pluginsCache.find((p) => p.id === pid);
    if (!plugin) return;
    const button = document.createElement("button");
    button.className = "rail-plugin";
    button.type = "button";
    button.title = plugin.name;
    button.innerHTML = `<span class="plugin-rail-icon">${pluginIcon(pid)}</span><span>${escapeHtml(plugin.name)}</span>`;
    button.onclick = () => openPluginActionPanel(pid);
    pluginRailList.appendChild(button);
  });
}

function renderHomePluginGrid() {
  if (!homePluginGrid) return;
  const plugins = HOME_PLUGINS.map((pid) => pluginsCache.find((p) => p.id === pid)).filter(Boolean);
  if (!plugins.length) {
    homePluginGrid.innerHTML = "";
    return;
  }
  homePluginGrid.innerHTML = `
    <div class="home-plugin-section">
      <div class="home-plugin-header">
        <strong>Plugins</strong>
        <button id="homePluginsAll" type="button" class="home-plugins-link">View all</button>
      </div>
      <div class="home-plugin-cards">
        ${plugins.slice(0, 9).map((plugin) => `
          <button class="home-plugin-card" data-home-plugin="${escapeHtml(plugin.id)}" type="button">
            <span class="home-plugin-icon">${pluginIcon(plugin.id)}</span>
            <strong>${escapeHtml(plugin.name)}</strong>
            <small>${escapeHtml((plugin.description || "").slice(0, 50))}</small>
          </button>
        `).join("")}
      </div>
    </div>
  `;
  homePluginGrid.querySelectorAll("[data-home-plugin]").forEach((btn) => {
    btn.onclick = () => openPluginActionPanel(btn.dataset.homePlugin);
  });
  const allBtn = q("#homePluginsAll");
  if (allBtn) allBtn.onclick = () => openPanel("plugins");
}

async function openPluginActionPanel(pluginId) {
  const plugin = pluginsCache.find((p) => p.id === pluginId);
  if (!plugin) {
    await loadPlugins();
    const p2 = pluginsCache.find((pp) => pp.id === pluginId);
    if (!p2) return;
    return openPluginActionPanel(pluginId);
  }
  cloudPanel.hidden = false;
  panelTitle.textContent = plugin.name;
  const actions = plugin.actions || ["status"];
  panelBody.innerHTML = `
    <div class="plugin-action-shell">
      <div class="plugin-action-head">
        <span class="plugin-action-icon">${pluginIcon(pluginId)}</span>
        <div>
          <strong>${escapeHtml(plugin.name)}</strong>
          <small>${escapeHtml(plugin.description || "")}</small>
        </div>
        <span class="plugin-status-pill ${plugin.connected ? "enabled" : "disabled"}">${plugin.connected ? "Ready" : "Setup"}</span>
      </div>
      <div class="plugin-action-buttons">
        ${actions.map((a) => `<button class="plugin-action-btn" data-plugin-action="${escapeHtml(a)}" type="button">${escapeHtml(a.replace(/_/g, " "))}</button>`).join("")}
      </div>
      <div class="plugin-action-input-area" id="pluginActionInputArea">
        <textarea id="pluginActionInput" rows="2" placeholder="Enter parameters (JSON) or leave empty for default action..."></textarea>
        <button id="pluginRunAction" class="plugin-primary" type="button">Run</button>
      </div>
      <pre id="pluginActionResult" class="plugin-output">Click an action to run it.</pre>
    </div>
  `;
  let selectedAction = actions[0] || "status";
  panelBody.querySelectorAll("[data-plugin-action]").forEach((btn) => {
    btn.onclick = () => {
      selectedAction = btn.dataset.pluginAction;
      panelBody.querySelectorAll(".plugin-action-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      q("#pluginActionInput").placeholder = `Parameters for "${selectedAction}" (JSON)`;
    };
  });
  q("#pluginRunAction").onclick = async () => {
    const output = q("#pluginActionResult");
    output.textContent = `Running ${selectedAction}...`;
    try {
      let params = {};
      const inputVal = q("#pluginActionInput").value.trim();
      if (inputVal) {
        try { params = JSON.parse(inputVal); } catch { params = { raw: inputVal }; }
      }
      const data = await api("/plugins/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_id: pluginId, action: selectedAction, params }),
      });
      output.textContent = data.output || "Action completed.";
    } catch (error) {
      output.textContent = `Error: ${error.message}`;
    }
  };
  const firstBtn = panelBody.querySelector("[data-plugin-action]");
  if (firstBtn) firstBtn.classList.add("active");
}

function renderMessages() {
  const chat = activeChat();
  messages.innerHTML = "";
  const hasWorkspaceOverlay = !workspacePanel.hidden || !pluginsPage.hidden || !agentsPage.hidden || !modelsPage.hidden || !apiKeysPage.hidden || !settingsPage.hidden;
  messages.hidden = !pluginsPage.hidden || !agentsPage.hidden || !modelsPage.hidden || !apiKeysPage.hidden || !settingsPage.hidden;
  emptyState.hidden = chat.messages.length > 0 || hasWorkspaceOverlay;
  floatingChatForm.hidden = chat.messages.length === 0 || hasWorkspaceOverlay;
  renderAgentChip();
  chat.messages.forEach((message) => {
    const row = document.createElement("div");
    row.className = `message-row ${message.role}`;
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = message.role === "user" ? "U" : "A";
    const bubble = document.createElement("article");
    bubble.className = "message" + (message.role === "assistant" ? " markdown-content" : "");
    if (message.role === "assistant") {
      bubble.innerHTML = renderMarkdown(message.content);
      addCopyButtons(bubble);
    } else {
      bubble.innerHTML = escapeHtml(message.content);
    }
    if (message.artifact) {
      bubble.innerHTML += renderArtifactCard(message.artifact);
    }
    if (message.project) {
      bubble.innerHTML += renderProjectCard(message.project);
    }
    if (message.toolCalls && message.toolCalls.length) {
      const toolDiv = document.createElement("div");
      toolDiv.className = "tool-calls";
      message.toolCalls.forEach((tc) => {
        const toolEl = document.createElement("div");
        toolEl.className = "tool-call-indicator";
        toolEl.innerHTML = `<span class="tool-icon">🔧</span> <strong>${escapeHtml(tc.name)}</strong>`;
        toolDiv.appendChild(toolEl);
      });
      bubble.insertBefore(toolDiv, bubble.firstChild);
    }
    if (message.sources?.length) {
      const sources = document.createElement("div");
      sources.className = "sources";
      sources.textContent = `Sources: ${message.sources.map((s) => `${s.source} chunk ${s.chunk}`).join(", ")}`;
      bubble.appendChild(sources);
    }
    row.append(avatar, bubble);
    messages.appendChild(row);
  });
  bindMessageProjectActions();
  messages.scrollTop = messages.scrollHeight;
}

function render() {
  renderAgentRail();
  renderPluginRail();
  renderHomePluginGrid();
  renderChats();
  renderMessages();
}

function renderAgentChip() {
  const selected = currentAgentId();
  const agent = agentById(selected);
  const visible = selected !== "general";
  [agentChip, floatingAgentChip].forEach((chip) => {
    if (!chip) return;
    chip.hidden = !visible;
  });
  if (agentChipText) agentChipText.textContent = `Agent: ${agent.name}`;
  if (floatingAgentChipText) floatingAgentChipText.textContent = agent.name;
}

async function startNewChat() {
  try {
    const data = await api("/chats", { method: "POST" });
    chats.unshift(data.chat);
    activeChatId = data.chat.id;
  } catch {
    createLocalChat();
  }
  workspacePanel.hidden = true;
  pluginsPage.hidden = true;
  agentsPage.hidden = true;
  modelsPage.hidden = true;
  apiKeysPage.hidden = true;
  settingsPage.hidden = true;
  cloudPanel.hidden = true;
  questionInput.value = "";
  floatingQuestionInput.value = "";
  document.querySelectorAll(".nav-action").forEach((b) => b.classList.toggle("active", b.dataset.panel === "chat"));
  render();
  questionInput.focus();
}

async function openAgentChat(agentId) {
  const agent = agentById(agentId);
  if (agentId === "general") {
    await startNewChat();
    return;
  }
  const existing = chats.find((chat) => chat.agentMode === agentId);
  if (existing) {
    activeChatId = existing.id;
  } else {
    try {
      const data = await api("/chats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: `${agent.name} chat`, agent_mode: agentId }),
      });
      chats.unshift(data.chat);
      activeChatId = data.chat.id;
    } catch {
      createLocalChat(`${agent.name} chat`, agentId);
    }
  }
  workspacePanel.hidden = true;
  pluginsPage.hidden = true;
  agentsPage.hidden = true;
  modelsPage.hidden = true;
  apiKeysPage.hidden = true;
  settingsPage.hidden = true;
  cloudPanel.hidden = true;
  document.querySelectorAll(".nav-action").forEach((b) => b.classList.toggle("active", b.dataset.panel === "chat"));
  render();
  questionInput.focus();
}

function addMessage(role, content, sources = []) {
  const chat = activeChat();
  chat.messages.push({ role, content, sources, createdAt: new Date().toISOString() });
  if (role === "user" && chat.title === "New chat") chat.title = content.slice(0, 44) || "New chat";
  render();
}

function addProjectMessage(project) {
  const chat = activeChat();
  chat.messages.push({
    role: "assistant",
    content: projectMessage(project),
    project,
    sources: [],
    createdAt: new Date().toISOString(),
  });
  render();
}

function latestProject() {
  const chatProject = [...activeChat().messages].reverse().find((message) => message.project || message.projectRef);
  const project = chatProject?.project || chatProject?.projectRef;
  return activeProject || project || null;
}

async function openProjectById(projectId) {
  const data = await api("/code-projects");
  const project = (data.projects || []).find((item) => item.id === projectId);
  if (!project) throw new Error("Project not found.");
  await openProject(project);
}

function bindMessageProjectActions() {
  messages.querySelectorAll("[data-open-chat-project]").forEach((button) => {
    button.onclick = async () => {
      button.disabled = true;
      try {
        await openProjectById(button.dataset.openChatProject);
      } catch (error) {
        addMessage("assistant", `Error: ${error.message}`);
      } finally {
        button.disabled = false;
      }
    };
  });
  messages.querySelectorAll("[data-preview-chat-project]").forEach((button) => {
    button.onclick = async () => {
      button.disabled = true;
      try {
        await previewProjectById(button.dataset.previewChatProject);
      } catch (error) {
        addMessage("assistant", `Error: ${error.message}`);
      } finally {
        button.disabled = false;
      }
    };
  });
}

async function ask(text) {
  if (!text.trim()) return;
  const chat = activeChat();
  addMessage("user", text);
  const pendingId = crypto.randomUUID();
  chat.messages.push({ id: pendingId, role: "assistant", content: "Aurine is working..." });
  render();
  try {
    const normalizedText = normalizeIntentText(text);
    if (/^(zip|download zip|project zip|zip do|zip de|zip chahiye|zip dedo|give zip file|give the zip file|create a zip of this)$/i.test(normalizedText)) {
      const project = latestProject();
      const pending = chat.messages.find((m) => m.id === pendingId);
      if (!project) {
        pending.content = "Creating a real ZIP file now...";
        render();
        const data = await api("/artifacts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text, artifact_type: "zip" }),
        });
        pending.content = artifactMessage(data.artifact);
        pending.artifact = data.artifact;
        await openPanel("project");
      } else {
        pending.content = `Zip is ready for ${project.name}.\n\nDownload:\n/code-projects/${project.id}/download`;
      }
      render();
      return;
    }
    if (shouldCreateProject(text) || isCreateItRequest(text)) {
      const pending = chat.messages.find((m) => m.id === pendingId);
      const prompt = isCreateItRequest(text) ? lastBuildPrompt() : text;
      if (!prompt || !shouldCreateProject(prompt)) {
        pending.content = "Create karne ke liye project/website prompt nahi mila. Example: create a portfolio website for Tushar.";
        render();
        return;
      }
      pending.content = "Creating the real project files now...";
      render();
      const projectData = await api("/code-projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      activeProject = projectData.project;
      pending.content = await projectChatMessage(projectData.project);
      pending.projectRef = projectData.project;
      pending.sources = [];
      await openProject(projectData.project);
      if (isPreviewRequest(text)) {
        await previewProject(projectData.project, true);
      }
      render();
      return;
    }
    if (isPreviewRequest(text)) {
      const project = latestProject();
      const pending = chat.messages.find((m) => m.id === pendingId);
      if (!project) {
        const prompt = fallbackPreviewPrompt();
        pending.content = "No open project found, so I am creating a real preview project now...";
        render();
        const projectData = await api("/code-projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt }),
        });
        activeProject = projectData.project;
        pending.projectRef = projectData.project;
        await previewProject(projectData.project);
        pending.content = `Preview opened for ${projectData.project.name}.`;
      } else {
        await previewProject(project);
        pending.content = `Preview opened for ${project.name}.`;
      }
      render();
      return;
    }
    if (/^\s*(terminal|open terminal|run command|debug|debug karo)\s*$/i.test(text)) {
      const project = latestProject();
      const pending = chat.messages.find((m) => m.id === pendingId);
      if (!project) {
        pending.content = "Error: No project is open yet. Create or open a project first.";
      } else {
        await openProject(project);
        commandInput.focus();
        pending.content = `Project tools opened for ${project.name}.`;
      }
      render();
      return;
    }
    if (isImproveProjectRequest(text)) {
      const pending = chat.messages.find((m) => m.id === pendingId);
      const project = latestProject();
      const basePrompt = project?.prompt || lastBuildPrompt() || text;
      const rebuildPrompt = `${basePrompt}\n\nRebuild this from scratch as a premium, complete, advanced, high-tech project. Do not make a basic template and do not repeat the same visual layout. Use a different design direction, richer animations, animated hero elements, scroll reveal, hover effects, modern sections, polished responsive UI, and production-quality content. User correction: ${text}`;
      pending.content = "Rebuilding the project properly with advanced full files...";
      render();
      const projectData = await api("/code-projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: rebuildPrompt }),
      });
      activeProject = projectData.project;
      pending.content = await projectChatMessage(projectData.project);
      pending.projectRef = projectData.project;
      pending.sources = [];
      await openProject(projectData.project);
      await previewProject(projectData.project, true);
      render();
      return;
    }
    const type = artifactType(text);
    if (type) {
      const pending = chat.messages.find((m) => m.id === pendingId);
      pending.content = `Creating real ${type} file now...`;
      render();
      const data = await api("/artifacts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text, artifact_type: type, previous_artifact_id: lastArtifactId }),
      });
      lastArtifactId = data.artifact.id;
      pending.content = artifactMessage(data.artifact);
      pending.artifact = data.artifact;
      pending.sources = [];
      await openPanel("project");
      render();
      return;
    }
    const history = chat.messages
      .filter((m) => m.content !== "Aurine is working..." && m.content !== "Aurine is working...")
      .slice(-16)
      .map((m) => ({ role: m.role, content: m.content }));
    const selectedAgent = currentAgentId() === "general" ? autoAgentForText(text) : currentAgentId();
    activeChat().agentMode = selectedAgent === "general" ? "" : selectedAgent;
    const question = `${agentInstruction(selectedAgent)}\n\nUser task:\n${text}`;
    const selectedModel = modelSettings();
    const pending = chat.messages.find((m) => m.id === pendingId);
    pending.content = "";
    render();

    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        user_text: text,
        history,
        chat_id: activeChatId,
        agent_mode: selectedAgent === "general" ? "" : selectedAgent,
        model_provider: selectedModel.provider || "",
        model_name: selectedModel.model || "",
        model_base_url: selectedModel.baseUrl || "",
        model_api_key: selectedModel.apiKey || "",
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({ detail: "Stream failed" }));
      throw new Error(errData.detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (!payload || payload === "[DONE]") continue;
        try {
          const data = JSON.parse(payload);
          if (data.error) {
            pending.content = `Error: ${data.error}`;
            break;
          }
          if (data.chunk) {
            pending.content += data.chunk;
            render();
          }
          if (data.chat_id) {
            activeChatId = data.chat_id;
          }
          if (data.done) {
            activeChatId = data.chat_id || activeChatId;
          }
        } catch {}
      }
    }

    if (!pending.content) pending.content = "No response received.";
  } catch (error) {
    chat.messages.find((m) => m.id === pendingId).content = `Error: ${error.message}`;
  }
  render();
}

async function loadChats() {
  await loadCustomAgents();
  const data = await api("/chats");
  chats = data.chats?.length ? data.chats : [];
  if (!chats.length) createLocalChat();
  activeChatId = chats[0].id;
  render();
}

async function loadCustomAgents() {
  try {
    const data = await api("/agents");
    customAgents = data.agents || [];
  } catch {
    customAgents = [];
  }
}

async function uploadSelected(file) {
  return uploadSelectedFiles(file ? [file] : []);
}

async function uploadSelectedFiles(fileList) {
  const files = Array.from(fileList || []).filter(Boolean);
  if (!files.length) return;
  openPanel("project");
  const status = panelBody.querySelector("#uploadStatus");
  const uploaded = [];
  for (const [index, file] of files.entries()) {
    status?.replaceChildren(document.createTextNode(`Uploading ${index + 1}/${files.length}: ${file.webkitRelativePath || file.name}...`));
    const form = new FormData();
    const uploadName = file.webkitRelativePath || file.name;
    form.append("file", file, uploadName);
    const data = await api("/upload", { method: "POST", body: form });
    uploaded.push(data);
  }
  await renderProjectPanel();
  const totalChunks = uploaded.reduce((sum, item) => sum + Number(item.chunks || 0), 0);
  const names = uploaded.slice(0, 5).map((item) => item.filename).join(", ");
  const extra = uploaded.length > 5 ? ` and ${uploaded.length - 5} more` : "";
  addMessage("assistant", `Uploaded ${uploaded.length} file${uploaded.length === 1 ? "" : "s"} (${names}${extra}) and indexed ${totalChunks} chunks. You can ask questions about them now.`);
}

async function openProject(project) {
  activeProject = project;
  pluginsPage.hidden = true;
  cloudPanel.hidden = true;
  workspacePanel.hidden = false;
  workspaceTitle.textContent = project.name;
  workspaceSubtitle.textContent = project.description || project.run_instructions || "Project files";
  terminalOutput.textContent = project.run_instructions || "";
  const data = await api(`/code-projects/${project.id}/files`);
  workspaceFiles.innerHTML = "";
  fileSelect.innerHTML = "";
  (data.files || []).forEach((path) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = path;
    button.onclick = () => loadFile(path);
    workspaceFiles.appendChild(button);
    const option = document.createElement("option");
    option.value = path;
    option.textContent = path;
    fileSelect.appendChild(option);
  });
  if (data.files?.[0]) await loadFile(data.files[0]);
  render();
}

async function previewProjectById(projectId) {
  const data = await api("/code-projects");
  const project = (data.projects || []).find((item) => item.id === projectId);
  if (!project) throw new Error("Project not found.");
  await previewProject(project);
}

async function previewProject(project, silent = false) {
  if (!project?.preview_path && !(project.files || []).some((file) => file.toLowerCase().endsWith(".html"))) {
    if (!silent) throw new Error("No HTML preview file found for this project.");
    return;
  }
  previewTitle.textContent = project.name || "Preview";
  previewFrame.src = `/code-projects/${encodeURIComponent(project.id)}/preview?v=${Date.now()}`;
  previewPanel.hidden = false;
}

async function loadFile(path) {
  activeFile = path;
  fileSelect.value = path;
  const data = await api(`/code-projects/${activeProject.id}/files/read?path=${encodeURIComponent(path)}`);
  fileEditor.value = data.content || "";
}

function panelCard(title, detail, action = "") {
  return `<div class="panel-card"><div class="panel-row"><strong>${escapeHtml(title)}</strong>${action}</div><small>${escapeHtml(detail || "")}</small></div>`;
}

function pluginInitial(name) {
  return String(name || "P").trim().slice(0, 1).toUpperCase();
}

function pluginCatalog(plugin) {
  if (plugin.id?.startsWith("ruflo-")) return "Ruflo";
  if (["git", "github", "vscode"].includes(plugin.id)) return "Desktop";
  return "Aurine";
}

function pluginConfigKey(pluginId) {
  return `Aurine_plugin_config_${pluginId}`;
}

function pluginSavedConfig(pluginId) {
  try {
    return JSON.parse(localStorage.getItem(pluginConfigKey(pluginId)) || "{}");
  } catch {
    return {};
  }
}

function setMainPage(panel) {
  workspacePanel.hidden = true;
  previewPanel.hidden = true;
  previewFrame.src = "about:blank";
  cloudPanel.hidden = true;
  pluginsPage.hidden = panel !== "plugins";
  agentsPage.hidden = panel !== "agents";
  modelsPage.hidden = panel !== "models";
  apiKeysPage.hidden = panel !== "apiKeys";
  settingsPage.hidden = panel !== "settings";
  document.querySelectorAll(".nav-action").forEach((b) => b.classList.toggle("active", b.dataset.panel === panel));
}

function closeMainPage() {
  pluginsPage.hidden = true;
  agentsPage.hidden = true;
  modelsPage.hidden = true;
  apiKeysPage.hidden = true;
  settingsPage.hidden = true;
  messages.hidden = false;
  document.querySelectorAll(".nav-action").forEach((b) => b.classList.toggle("active", b.dataset.panel === "chat"));
  render();
  questionInput.focus();
}

async function renderSearchPanel() {
  panelTitle.textContent = "Search";
  panelBody.innerHTML = `<input id="searchInput" placeholder="Search chats, files, projects..." /><div id="searchResults"></div>`;
  const input = q("#searchInput");
  const results = q("#searchResults");
  async function run() {
    const data = await api(`/search?q=${encodeURIComponent(input.value)}`);
    results.innerHTML = [
      ...(data.chats || []).map((x) => panelCard(`Chat: ${x.title}`, x.updated_at)),
      ...(data.messages || []).map((x) => panelCard(`Message: ${x.role}`, x.content.slice(0, 120))),
      ...(data.projects || []).map((x) => panelCard(`Project: ${x.name}`, `${x.files.length} files`)),
      ...(data.documents || []).map((x) => panelCard(`File: ${x.source}`, `${x.chunks} chunks`)),
    ].join("") || panelCard("No results", "Try another search.");
  }
  input.oninput = run;
  await run();
}

async function renderAgentsPanel() {
  await loadCustomAgents();
  setMainPage("agents");
  renderAgentsPage(activeAgentsFilter);
  render();
}

async function renderModelsPanel() {
  setMainPage("models");
  renderModelsPage(activeModelsFilter);
  render();
}

async function renderApiKeysPanel(newKey = "") {
  setMainPage("apiKeys");
  const data = await api("/api-keys");
  const endpoint = `${location.origin}/v1/chat/completions`;
  apiKeysPage.innerHTML = `
    <div class="api-keys-shell">
      <div class="models-toolbar">
        <div>
          <button id="apiKeysBackToChat" class="plugins-back" type="button">Back to chat</button>
          <h1>API keys</h1>
          <p>Use Aurine from other apps through an OpenAI-compatible endpoint. Aurine does not add its own rate limit.</p>
        </div>
        <div class="agents-toolbar-actions">
          <input id="apiKeyName" class="plugins-search" placeholder="Key name" />
          <button id="createApiKey" class="plugin-primary" type="button">Create key</button>
        </div>
      </div>
      ${newKey ? `
        <div class="api-key-created">
          <strong>New key created. Copy it now.</strong>
          <code>${escapeHtml(newKey)}</code>
        </div>
      ` : ""}
      <div class="api-endpoint-card">
        <strong>External setup</strong>
        <code>Base URL: ${escapeHtml(location.origin)}/v1</code>
        <code>Endpoint: ${escapeHtml(endpoint)}</code>
        <code>Model: aurine</code>
        <pre>curl ${endpoint} -H "Authorization: Bearer YOUR_AURINE_KEY" -H "Content-Type: application/json" -d "{\"model\":\"aurine\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello Aurine\"}]}"</pre>
      </div>
      <div class="models-grid">
        ${(data.keys || []).map((key) => `
          <div class="api-key-card">
            <span class="model-provider">${key.revoked ? "revoked" : "active"}</span>
            <strong>${escapeHtml(key.name)}</strong>
            <small>${escapeHtml(key.key_prefix)}...</small>
            <span>Created: ${escapeHtml(key.created_at || "")}</span>
            <span>Last used: ${escapeHtml(key.last_used_at || "Never")}</span>
            ${key.revoked ? "" : `<button data-revoke-api-key="${escapeHtml(key.id)}" type="button">Revoke</button>`}
          </div>
        `).join("") || `<div class="api-endpoint-card"><strong>No keys yet</strong><span>Create one above.</span></div>`}
      </div>
    </div>
  `;
  q("#apiKeysBackToChat").onclick = closeMainPage;
  q("#createApiKey").onclick = async () => {
    const created = await api("/api-keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: q("#apiKeyName").value || "External app" }),
    });
    await renderApiKeysPanel(created.key.key);
  };
  apiKeysPage.querySelectorAll("[data-revoke-api-key]").forEach((button) => {
    button.onclick = async () => {
      await api(`/api-keys/${button.dataset.revokeApiKey}/revoke`, { method: "POST" });
      await renderApiKeysPanel();
    };
  });
  render();
}

function agentInitial(name) {
  return String(name || "A").trim().slice(0, 1).toUpperCase();
}

function renderAgentsPage(filter = "") {
  activeAgentsFilter = filter;
  const selected = currentAgentId();
  const needle = filter.trim().toLowerCase();
  const agents = allAgents().filter((agent) => {
    const haystack = `${agent.name} ${agent.detail} ${agent.industry || ""} ${agent.framework || ""}`.toLowerCase();
    return !needle || haystack.includes(needle);
  });
  agentsPage.innerHTML = `
    <div class="agents-shell">
      <div class="agents-toolbar">
        <div>
          <button id="agentsBackToChat" class="plugins-back" type="button">Back to chat</button>
          <h1>Explore agents</h1>
          <p>Agents are built in. Aurine can auto-pick the right one from your message.</p>
        </div>
        <div class="agents-toolbar-actions">
          <input id="agentsSearch" class="plugins-search" value="${escapeHtml(filter)}" placeholder="Search agents" />
          <button id="showAgentCreate" class="plugin-primary" type="button">Create agent</button>
        </div>
      </div>
      <div id="agentCreateInline" class="agent-create-inline" hidden>
        <input id="inlineAgentName" placeholder="Agent name" />
        <input id="inlineAgentDetail" placeholder="Short description" />
        <textarea id="inlineAgentInstructions" rows="4" placeholder="Instructions, role, rules, and style"></textarea>
        <div class="plugin-button-row">
          <button id="inlineCreateAgent" type="button">Create</button>
          <button id="hideAgentCreate" type="button">Cancel</button>
        </div>
      </div>
      <div class="agent-auto-card">
        <strong>Auto agent routing is on</strong>
        <small>Ask for SQL, code review, test generation, docs, travel, finance, PDF Q&A, social posts, or app building and Aurine will attach the matching specialist automatically.</small>
      </div>
      <div class="agents-grid">
        ${agents.map((agent) => `
          <button class="agent-tile ${agent.id === selected ? "active" : ""}" data-agent="${escapeHtml(agent.id)}" type="button">
            <span class="agent-logo">${escapeHtml(agentInitial(agent.name))}</span>
            <strong>${escapeHtml(agent.name)}</strong>
            <small>${escapeHtml(agent.detail || "Specialist agent")}</small>
            <span class="agent-meta">${escapeHtml([agent.framework, agent.industry].filter(Boolean).join(" / ") || "Aurine")}</span>
          </button>
        `).join("")}
      </div>
    </div>
  `;
  q("#agentsBackToChat").onclick = closeMainPage;
  q("#agentsSearch").oninput = (event) => renderAgentsPage(event.target.value);
  q("#showAgentCreate").onclick = () => q("#agentCreateInline").hidden = false;
  q("#hideAgentCreate").onclick = () => q("#agentCreateInline").hidden = true;
  q("#inlineCreateAgent").onclick = createInlineAgent;
  agentsPage.querySelectorAll("[data-agent]").forEach((button) => {
    button.onclick = () => openAgentChat(button.dataset.agent);
  });
}

async function createInlineAgent() {
  const name = q("#inlineAgentName").value.trim();
  const detail = q("#inlineAgentDetail").value.trim();
  const instructions = q("#inlineAgentInstructions").value.trim();
  if (!name || !instructions) return;
  const data = await api("/agents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, detail, instructions }),
  });
  customAgents.unshift(data.agent);
  renderAgentRail();
  renderAgentsPage(activeAgentsFilter);
}

function modelCategory(model) {
  if (model.provider === "aurine") return "Aurine";
  if (model.provider === "ollama" || model.id.startsWith("local-")) return "Local";
  if (model.id.startsWith("openrouter") || model.id.startsWith("groq")) return "Provider API";
  if (model.id.startsWith("custom-") || model.id === "custom") return "Custom";
  return "Famous";
}

function isFreeModel(model) {
  if (model.provider === "aurine" || model.provider === "ollama") return true;
  if (model.id.startsWith("local-")) return true;
  if (model.id.startsWith("groq")) return true;
  if (model.id === "openrouter-auto") return true;
  return false;
}

let activeSettingsTab = "general";

function renderSettingsPage() {
  setMainPage("settings");
  const profileName = profile?.user?.name || settingsName?.value || "User";
  const profileEmail = profile?.user?.email || workspaceUser?.textContent || "";
  const currentTheme = document.body.dataset.theme || "aurora-3d";
  const currentModel = modelSettings();
  const connectedApps = [
    { id: "google", name: "Google", desc: "Sign in with Google, Calendar, Drive integration", icon: "G", connected: !!authToken },
    { id: "github", name: "GitHub", desc: "Repository access, issue tracking, code sync", icon: "GH", connected: false },
    { id: "slack", name: "Slack", desc: "Send messages, notifications, and updates to channels", icon: "S", connected: false },
    { id: "discord", name: "Discord", desc: "Bot integration and server notifications", icon: "D", connected: false },
    { id: "notion", name: "Notion", desc: "Read and write pages, databases, and docs", icon: "N", connected: false },
    { id: "vercel", name: "Vercel", desc: "Deploy projects and manage domains", icon: "V", connected: false },
  ];
  const devices = [
    { id: "desktop", name: "Desktop App", desc: "Local development environment", status: "Connected", icon: "D" },
    { id: "mobile", name: "Mobile Access", desc: "LAN access from phone or tablet", status: navigator.userAgent.includes("Mobi") ? "Connected" : "Available", icon: "M" },
    { id: "api", name: "API Access", desc: "OpenAI-compatible endpoint for external tools", status: "Active", icon: "A" },
  ];
  settingsPage.innerHTML = `
    <div class="settings-shell">
      <div style="display:flex;gap:24px;align-items:flex-start;">
        <nav class="settings-nav">
          <button class="settings-nav-item ${activeSettingsTab === "general" ? "active" : ""}" data-settings-tab="general">
            <span class="settings-nav-icon">G</span> General
          </button>
          <button class="settings-nav-item ${activeSettingsTab === "appearance" ? "active" : ""}" data-settings-tab="appearance">
            <span class="settings-nav-icon">T</span> Appearance
          </button>
          <button class="settings-nav-item ${activeSettingsTab === "models" ? "active" : ""}" data-settings-tab="models">
            <span class="settings-nav-icon">M</span> Models & API Keys
          </button>
          <button class="settings-nav-item ${activeSettingsTab === "apps" ? "active" : ""}" data-settings-tab="apps">
            <span class="settings-nav-icon">A</span> Connected Apps
          </button>
          <button class="settings-nav-item ${activeSettingsTab === "devices" ? "active" : ""}" data-settings-tab="devices">
            <span class="settings-nav-icon">D</span> Devices
          </button>
          <button class="settings-nav-item ${activeSettingsTab === "about" ? "active" : ""}" data-settings-tab="about">
            <span class="settings-nav-icon">I</span> About
          </button>
        </nav>
        <div class="settings-body">
          ${renderSettingsTab()}
        </div>
      </div>
    </div>
  `;
  q("#settingsBackToChat")?.addEventListener("click", closeMainPage);
  settingsPage.querySelectorAll("[data-settings-tab]").forEach((btn) => {
    btn.onclick = () => {
      activeSettingsTab = btn.dataset.settingsTab;
      renderSettingsPage();
    };
  });
  if (activeSettingsTab === "general") {
    const saveBtn = q("#settingsGeneralSave");
    if (saveBtn) saveBtn.onclick = async () => {
      await api("/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: q("#settingsGenName")?.value || "",
          workspace_name: q("#settingsGenWorkspace")?.value || "",
          theme: document.body.dataset.theme || "aurora-3d",
        }),
      });
      const data = await api("/me");
      applyProfile(data);
      renderSettingsPage();
    };
  }
  if (activeSettingsTab === "appearance") {
    settingsPage.querySelectorAll("[data-set-theme]").forEach((btn) => {
      btn.onclick = () => {
        document.body.dataset.theme = btn.dataset.setTheme;
        api("/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ theme: btn.dataset.setTheme }),
        });
        renderSettingsPage();
      };
    });
  }
  if (activeSettingsTab === "models") {
    const showKeyBtn = q("#settingsApiKeyToggle");
    if (showKeyBtn) {
      showKeyBtn.onclick = () => {
        const input = q("#settingsApiKeyInput");
        if (!input) return;
        const isPassword = input.type === "password";
        input.type = isPassword ? "text" : "password";
        showKeyBtn.textContent = isPassword ? "Hide" : "Show";
      };
    }
    settingsPage.querySelectorAll("[data-settings-model-id]").forEach((btn) => {
      btn.onclick = () => {
        const model = allModelOptions().find((m) => m.id === btn.dataset.settingsModelId);
        if (!model) return;
        saveModelSettings({ ...model, presetId: model.id });
        renderSettingsPage();
      };
    });
    const saveModelBtn = q("#settingsModelSave");
    if (saveModelBtn) {
      saveModelBtn.onclick = () => {
        const key = q("#settingsApiKeyInput")?.value || "";
        const baseUrl = q("#settingsBaseUrlInput")?.value || "";
        saveModelSettings({ ...currentModel, apiKey: key, baseUrl: baseUrl, presetId: currentModel.id });
        renderSettingsPage();
      };
    }
    const openAllModelsBtn = q("#settingsOpenAllModels");
    if (openAllModelsBtn) {
      openAllModelsBtn.onclick = () => {
        settingsPage.hidden = true;
        openPanel("models");
      };
    }
  }
  render();
}

function renderSettingsTab() {
  const currentModel = modelSettings();
  if (activeSettingsTab === "general") {
    return `
      <div class="settings-section">
        <button id="settingsBackToChat" class="plugins-back" type="button">Back to chat</button>
        <h2>General</h2>
        <p>Manage your workspace profile and preferences.</p>
        <div class="settings-field">
          <label>Your name</label>
          <input id="settingsGenName" value="${escapeHtml(profile?.user?.name || "")}" placeholder="Your name" />
        </div>
        <div class="settings-field">
          <label>Workspace name</label>
          <input id="settingsGenWorkspace" value="${escapeHtml(profile?.settings?.workspace_name || "Aurine Workspace")}" placeholder="Workspace name" />
        </div>
        <div class="settings-save-bar">
          <button id="settingsGeneralSave" class="save-primary" type="button">Save changes</button>
        </div>
      </div>
    `;
  }
  if (activeSettingsTab === "appearance") {
    const themes = [
      { id: "aurora-3d", label: "Aurora 3D", desc: "Dark teal + purple with 3D floating shapes" },
      { id: "coder-night", label: "Coder Night", desc: "Dark with code rain and circuit effects" },
      { id: "normal", label: "Normal", desc: "Clean light theme with subtle geometry" },
      { id: "beauty", label: "Beauty", desc: "Dark forest green with aurora accents" },
    ];
    return `
      <div class="settings-section">
        <button id="settingsBackToChat" class="plugins-back" type="button">Back to chat</button>
        <h2>Appearance</h2>
        <p>Choose a theme for your workspace.</p>
        <div class="settings-app-grid">
          ${themes.map((t) => `
            <button class="settings-app-card" data-set-theme="${t.id}" type="button" style="cursor:pointer;text-align:left;border:2px solid ${(document.body.dataset.theme || "aurora-3d") === t.id ? "var(--accent)" : "var(--line)"};">
              <div class="app-header">
                <div class="app-icon">${t.label[0]}</div>
                <div class="app-info">
                  <strong>${escapeHtml(t.label)}</strong>
                  <small>${escapeHtml(t.desc)}</small>
                </div>
              </div>
              ${(document.body.dataset.theme || "aurora-3d") === t.id ? '<span class="free-badge">Active</span>' : ""}
            </button>
          `).join("")}
        </div>
      </div>
    `;
  }
  if (activeSettingsTab === "models") {
    const freeModels = allModelOptions().filter(isFreeModel);
    const paidModels = allModelOptions().filter((m) => !isFreeModel(m));
    return `
      <div class="settings-section">
        <button id="settingsBackToChat" class="plugins-back" type="button">Back to chat</button>
        <h2>Models & API Keys</h2>
        <p>Configure which AI model powers your chats. Free models run locally or via free API tiers.</p>
        <div class="settings-row">
          <div>
            <strong>Current model</strong>
            <small>${escapeHtml(currentModel.label || currentModel.model || "Aurine Native")}</small>
          </div>
          <span class="free-badge">${isFreeModel(currentModel) ? "Free" : "Paid"}</span>
        </div>
        <div class="settings-section">
          <h3 style="margin:12px 0 0;font-size:15px;">Free models (no API key needed or free tier)</h3>
          <p>These models work out of the box or with free API keys.</p>
          <div class="settings-app-grid">
            ${freeModels.map((model) => `
              <div class="settings-app-card" style="cursor:pointer;${currentModel.presetId === model.id ? "border-color:var(--accent);background:rgba(45,212,191,.08);" : ""}" data-settings-model-id="${escapeHtml(model.id)}">
                <div class="app-header">
                  <div class="app-icon">${escapeHtml((model.label || "M")[0])}</div>
                  <div class="app-info">
                    <strong>${escapeHtml(model.label)}</strong>
                    <small>${escapeHtml(model.model)}</small>
                  </div>
                  <span class="free-badge">Free</span>
                </div>
                <small class="app-desc">Provider: ${escapeHtml(model.provider)}${model.baseUrl ? ` | ${escapeHtml(model.baseUrl)}` : " | Local"}</small>
                ${currentModel.presetId === model.id ? '<span class="free-badge" style="margin-top:4px;">Currently active</span>' : ""}
              </div>
            `).join("")}
          </div>
        </div>
        <div class="settings-section">
          <h3 style="margin:12px 0 0;font-size:15px;">Paid models (API key required)</h3>
          <div class="settings-app-grid">
            ${paidModels.map((model) => `
              <div class="settings-app-card" style="cursor:pointer;${currentModel.presetId === model.id ? "border-color:var(--accent);background:rgba(45,212,191,.08);" : ""}" data-settings-model-id="${escapeHtml(model.id)}">
                <div class="app-header">
                  <div class="app-icon">${escapeHtml((model.label || "M")[0])}</div>
                  <div class="app-info">
                    <strong>${escapeHtml(model.label)}</strong>
                    <small>${escapeHtml(model.model)}</small>
                  </div>
                  <span class="paid-badge">Paid</span>
                </div>
                <small class="app-desc">Provider: ${escapeHtml(model.provider)}${model.baseUrl ? ` | ${escapeHtml(model.baseUrl)}` : ""}</small>
                ${currentModel.presetId === model.id ? '<span class="free-badge" style="margin-top:4px;">Currently active</span>' : ""}
              </div>
            `).join("")}
          </div>
        </div>
        <div class="settings-section">
          <h3 style="margin:12px 0 0;font-size:15px;">API Key for current model</h3>
          <p>Enter or update the API key for paid cloud models. Free local models don't need a key.</p>
          <div class="settings-field">
            <label>API Key</label>
            <div class="api-key-input-wrap">
              <input id="settingsApiKeyInput" type="password" value="${escapeHtml(currentModel.apiKey || "")}" placeholder="Enter API key (not needed for free/local models)" />
              <button id="settingsApiKeyToggle" class="api-key-toggle" type="button">Show</button>
            </div>
          </div>
          <div class="settings-field">
            <label>Base URL (optional)</label>
            <input id="settingsBaseUrlInput" value="${escapeHtml(currentModel.baseUrl || "")}" placeholder="Custom base URL" />
          </div>
          <div class="settings-save-bar">
            <button id="settingsModelSave" class="save-primary" type="button">Save model settings</button>
          </div>
        </div>
        <div class="settings-section" style="margin-top:12px;">
          <button id="settingsOpenAllModels" class="save-secondary" type="button" style="border:1px solid var(--line);border-radius:10px;padding:10px 16px;background:rgba(255,255,255,.08);color:var(--ink);cursor:pointer;">Open full model library</button>
        </div>
      </div>
    `;
  }
  if (activeSettingsTab === "apps") {
    const connectedApps = [
      { id: "google", name: "Google", desc: "Sign in, Calendar, Drive, and Gmail integration", icon: "G", connected: true },
      { id: "github", name: "GitHub", desc: "Repository access, issue tracking, and code sync", icon: "GH", connected: false },
      { id: "slack", name: "Slack", desc: "Send messages, notifications, and channel updates", icon: "S", connected: false },
      { id: "discord", name: "Discord", desc: "Bot integration, server alerts, and moderation", icon: "D", connected: false },
      { id: "notion", name: "Notion", desc: "Read and write pages, databases, and documentation", icon: "N", connected: false },
      { id: "vercel", name: "Vercel", desc: "One-click deploy projects and manage custom domains", icon: "V", connected: false },
      { id: "aws", name: "AWS", desc: "Cloud infrastructure, S3, Lambda, and EC2 access", icon: "A", connected: false },
      { id: "openai", name: "OpenAI Platform", desc: "Direct OpenAI API access for GPT-4 and DALL-E", icon: "O", connected: false },
      { id: "anthropic", name: "Anthropic", desc: "Claude models access and conversation API", icon: "C", connected: false },
    ];
    return `
      <div class="settings-section">
        <button id="settingsBackToChat" class="plugins-back" type="button">Back to chat</button>
        <h2>Connected Apps</h2>
        <p>Connect external services to extend Aurine's capabilities.</p>
        <div class="settings-app-grid">
          ${connectedApps.map((app) => `
            <div class="settings-app-card">
              <div class="app-header">
                <div class="app-icon">${escapeHtml(app.icon)}</div>
                <div class="app-info">
                  <strong>${escapeHtml(app.name)}</strong>
                  <small>${escapeHtml(app.desc)}</small>
                </div>
              </div>
              <div style="display:flex;align-items:center;gap:8px;">
                <span class="app-status ${app.connected ? "connected" : "disconnected"}">${app.connected ? "Connected" : "Not connected"}</span>
                <button type="button" style="border:1px solid var(--line);border-radius:8px;padding:6px 12px;background:rgba(255,255,255,.08);color:var(--ink);font-size:12px;cursor:pointer;">${app.connected ? "Disconnect" : "Connect"}</button>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }
  if (activeSettingsTab === "devices") {
    const devices = [
      { id: "desktop", name: "Desktop App", desc: "Your local development environment running Aurine", status: "Connected", icon: "D" },
      { id: "mobile", name: "Mobile Access", desc: "Access Aurine from your phone or tablet on the same network", status: navigator.userAgent.includes("Mobi") ? "Connected" : "Available", icon: "M" },
      { id: "api", name: "API Endpoint", desc: `OpenAI-compatible API at ${location.origin}/v1/chat/completions`, status: "Active", icon: "A" },
      { id: "docker", name: "Docker Container", desc: "Run Aurine in a containerized environment", status: "Configured", icon: "DC" },
    ];
    return `
      <div class="settings-section">
        <button id="settingsBackToChat" class="plugins-back" type="button">Back to chat</button>
        <h2>Devices</h2>
        <p>Manage connected devices and access points for your workspace.</p>
        <div class="settings-app-grid">
          ${devices.map((d) => `
            <div class="settings-app-card">
              <div class="app-header">
                <div class="app-icon">${escapeHtml(d.icon)}</div>
                <div class="app-info">
                  <strong>${escapeHtml(d.name)}</strong>
                  <small>${escapeHtml(d.desc)}</small>
                </div>
              </div>
              <span class="app-status connected">${escapeHtml(d.status)}</span>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }
  if (activeSettingsTab === "about") {
    return `
      <div class="settings-section">
        <button id="settingsBackToChat" class="plugins-back" type="button">Back to chat</button>
        <h2>About Aurine</h2>
        <p>Your self-hosted AI workspace assistant.</p>
        <div class="settings-row">
          <div><strong>Version</strong><small>1.0.0</small></div>
        </div>
        <div class="settings-row">
          <div><strong>AI Provider</strong><small>Aurine (Local Ollama + Cloud APIs)</small></div>
        </div>
        <div class="settings-row">
          <div><strong>Runtime</strong><small>FastAPI + Vanilla JS</small></div>
        </div>
        <div class="settings-row">
          <div><strong>Models Available</strong><small>${allModelOptions().length} presets + custom models</small></div>
        </div>
        <div class="settings-row">
          <div><strong>Agents Available</strong><small>${allAgents().length} built-in + custom agents</small></div>
        </div>
        <div class="settings-row">
          <div><strong>Free Models</strong><small>${allModelOptions().filter(isFreeModel).length} models that work without paid API keys</small></div>
        </div>
      </div>
    `;
  }
  return "";
}

function renderModelsPage(filter = "") {
  activeModelsFilter = filter;
  const selected = modelSettings();
  const needle = filter.trim().toLowerCase();
  const models = allModelOptions().filter((model) => {
    const haystack = `${model.label} ${model.provider} ${model.model} ${model.baseUrl} ${modelCategory(model)}`.toLowerCase();
    return !needle || haystack.includes(needle);
  });
  modelsPage.innerHTML = `
    <div class="models-shell">
      <div class="models-toolbar">
        <div>
          <button id="modelsBackToChat" class="plugins-back" type="button">Back to chat</button>
          <h1>Models</h1>
          <p>Quick dropdown shows only famous real models. This page keeps the full model library and custom models.</p>
        </div>
        <div class="agents-toolbar-actions">
          <input id="modelsSearch" class="plugins-search" value="${escapeHtml(filter)}" placeholder="Search models" />
          <button id="showModelCreate" class="plugin-primary" type="button">Add model</button>
        </div>
      </div>
      <div id="modelCreateInline" class="model-create-inline" hidden>
        <input id="pageModelLabel" placeholder="Name, e.g. My OpenRouter Llama" required />
        <select id="pageModelProvider">
          <option value="custom">custom</option>
          <option value="openai">openai</option>
          <option value="anthropic">anthropic</option>
          <option value="openrouter">openrouter</option>
          <option value="groq">groq</option>
          <option value="mistral">mistral</option>
          <option value="cerebras">cerebras</option>
          <option value="nvidia">nvidia</option>
          <option value="ofox">ofox</option>
          <option value="vercel">vercel</option>
          <option value="fireworks">fireworks</option>
          <option value="sambanova">sambanova</option>
          <option value="cloudflare">cloudflare</option>
          <option value="kimi">kimi</option>
          <option value="codex">codex</option>
          <option value="ollama">ollama</option>
        </select>
        <input id="pageModelName" placeholder="Model name" required />
        <input id="pageModelBaseUrl" placeholder="Base URL, optional" />
        <input id="pageModelApiKey" type="password" placeholder="API key, optional" />
        <div class="plugin-button-row">
          <button id="pageCreateModel" type="button">Add and use</button>
          <button id="pageModelKeyToggle" type="button" style="border:1px solid var(--line);border-radius:10px;padding:9px 10px;background:rgba(238,247,255,.92);color:#06101d;">Show key</button>
          <button id="hideModelCreate" type="button">Cancel</button>
        </div>
      </div>
      <div class="models-grid">
        ${models.map((model) => `
          <button class="model-tile ${selected.presetId === model.id ? "active" : ""}" type="button" data-page-model-id="${escapeHtml(model.id)}">
            <span class="model-provider">${escapeHtml(model.provider || "custom")}</span>
            <strong>${escapeHtml(model.label || model.model)}</strong>
            <small>${escapeHtml(model.model || "Add model name before use")}</small>
            <span>${escapeHtml(modelCategory(model))} ${isFreeModel(model) ? '<span class="free-badge">Free</span>' : '<span class="paid-badge">Paid</span>'}</span>
          </button>
        `).join("")}
      </div>
    </div>
  `;
  q("#modelsBackToChat").onclick = closeMainPage;
  q("#modelsSearch").oninput = (event) => renderModelsPage(event.target.value);
  q("#showModelCreate").onclick = () => {
    q("#modelCreateInline").hidden = false;
    q("#pageModelLabel").focus();
  };
  q("#hideModelCreate").onclick = () => q("#modelCreateInline").hidden = true;
  q("#pageModelKeyToggle").onclick = () => {
    const input = q("#pageModelApiKey");
    if (!input) return;
    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";
    q("#pageModelKeyToggle").textContent = isPassword ? "Hide key" : "Show key";
  };
  q("#pageCreateModel").onclick = createPageModel;
  modelsPage.querySelectorAll("[data-page-model-id]").forEach((button) => {
    button.onclick = () => {
      const model = allModelOptions().find((item) => item.id === button.dataset.pageModelId);
      if (!model) return;
      saveModelSettings({ ...model, presetId: model.id });
      renderModelsPage(activeModelsFilter);
    };
  });
}

function createPageModel() {
  const label = q("#pageModelLabel").value.trim();
  const modelName = q("#pageModelName").value.trim();
  if (!label || !modelName) return;
  const model = {
    id: `custom-${crypto.randomUUID()}`,
    label,
    provider: q("#pageModelProvider").value,
    model: modelName,
    baseUrl: q("#pageModelBaseUrl").value.trim(),
    apiKey: q("#pageModelApiKey").value.trim(),
  };
  const models = customModels();
  models.push(model);
  localStorage.setItem(customModelsKey, JSON.stringify(models));
  saveModelSettings({ ...model, presetId: model.id });
  renderModelsPage(activeModelsFilter);
}

async function renderLegacyAgentsPanel() {
  panelTitle.textContent = "Agents";
  await loadCustomAgents();
  const selected = currentAgentId();
  panelBody.innerHTML = `
    <div class="panel-card">
      <strong>Current chat agent</strong>
      <small>${escapeHtml(agentById(selected).name)}${selected === "general" ? " - no specialist pinned" : " - active for this chat"}</small>
      <button id="clearAgentFromPanel" type="button" title="Remove agent">×</button>
    </div>
    ${(AGENTS || []).map((agent) => `
      <button class="agent-option ${agent.id === selected ? "active" : ""}" data-agent="${agent.id}" type="button">
        <strong>${escapeHtml(agent.name)}</strong>
        <span>${escapeHtml(agent.detail)}</span>
      </button>
    `).join("")}
  `;
  q("#clearAgentFromPanel").onclick = clearCurrentAgent;
  panelBody.querySelectorAll("[data-agent]").forEach((button) => {
    button.onclick = () => openAgentChat(button.dataset.agent);
  });
}

function closeModelDropdown() {
  document.querySelector(".model-dropdown")?.remove();
}

function openModelDropdown(anchor) {
  closeModelDropdown();
  const selected = modelSettings();
  const menu = document.createElement("div");
  menu.className = "model-dropdown";
  menu.innerHTML = `
    <div class="model-dropdown-head">
      <strong>Select model</strong>
      <button type="button" data-close-model title="Close">×</button>
    </div>
    <div class="model-list">
      ${quickModelOptions().map((model) => `
        <button class="model-option ${selected.presetId === model.id ? "active" : ""}" type="button" data-model-id="${escapeHtml(model.id)}">
          <strong>${escapeHtml(model.label)} ${isFreeModel(model) ? '<span class="free-badge" style="font-size:10px;">Free</span>' : ""}</strong>
          <span>${escapeHtml([model.provider, model.model].filter(Boolean).join(" / "))}</span>
        </button>
      `).join("")}
    </div>
    <button class="model-add-toggle" type="button" data-open-models-page>All models and add new</button>
  `;
  document.body.appendChild(menu);
  const rect = anchor.getBoundingClientRect();
  const menuHeight = menu.offsetHeight || 400;
  const spaceBelow = window.innerHeight - rect.bottom;
  if (spaceBelow < menuHeight + 20) {
    menu.style.top = `${Math.max(12, rect.top - menuHeight - 8)}px`;
  } else {
    menu.style.top = `${Math.max(12, rect.bottom + 8)}px`;
  }
  menu.style.left = `${Math.max(12, Math.min(rect.left, window.innerWidth - 330))}px`;
  menu.querySelector("[data-close-model]").onclick = closeModelDropdown;
  menu.querySelector("[data-open-models-page]").onclick = () => {
    closeModelDropdown();
    openPanel("models");
  };
  menu.querySelectorAll("[data-model-id]").forEach((button) => {
    button.onclick = () => {
      const model = allModelOptions().find((item) => item.id === button.dataset.modelId);
      if (!model) return;
      saveModelSettings({ ...model, presetId: model.id });
      closeModelDropdown();
    };
  });
}

async function renderScheduledPanel() {
  panelTitle.textContent = "Scheduled";
  panelBody.innerHTML = `
    <div class="panel-card">
      <input id="scheduleTitle" placeholder="Task title" />
      <input id="scheduleDue" placeholder="Due time, e.g. tomorrow 10 AM" />
      <textarea id="scheduleDetail" placeholder="Details"></textarea>
      <button id="addSchedule">Add scheduled item</button>
    </div>
    <div id="scheduleList"></div>`;
  async function refresh() {
    const data = await api("/scheduled");
    q("#scheduleList").innerHTML = (data.items || [])
      .map((x) => panelCard(x.title, `${x.due_at || "No due time"} ${x.detail || ""}`))
      .join("") || panelCard("No scheduled items", "Add one above.");
  }
  q("#addSchedule").onclick = async () => {
    await api("/scheduled", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: q("#scheduleTitle").value,
        due_at: q("#scheduleDue").value,
        detail: q("#scheduleDetail").value,
      }),
    });
    await refresh();
  };
  await refresh();
}

async function renderPluginsPanel() {
  const data = await api("/plugins");
  pluginsCache = data.plugins || [];
  activePluginId = activePluginId && pluginsCache.some((plugin) => plugin.id === activePluginId) ? activePluginId : "";
  setMainPage("plugins");
  renderPluginsList();
  render();
}

function renderPluginsList(filter = "") {
  const needle = filter.trim().toLowerCase();
  const plugins = pluginsCache.filter((plugin) => {
    const haystack = `${plugin.name} ${plugin.description} ${plugin.status} ${pluginCatalog(plugin)}`.toLowerCase();
    return !needle || haystack.includes(needle);
  });
  pluginsPage.innerHTML = `
    <div class="plugins-shell">
      <div class="plugins-toolbar">
        <div>
          <button id="pluginsBackToChat" class="plugins-back" type="button">Back to chat</button>
          <h1>Plugins</h1>
        </div>
        <div class="plugins-search-wrap">
          <input id="pluginsSearch" class="plugins-search" value="${escapeHtml(filter)}" placeholder="Search plugins" />
          <button id="pluginsFilter" class="plugins-icon-button" type="button" title="Filter">F</button>
        </div>
      </div>
      <div class="plugins-table" role="table" aria-label="Plugins">
        <div class="plugins-row plugins-heading" role="row">
          <span>Name</span>
          <span>Status</span>
          <span>Installation policy</span>
          <span>Catalog</span>
          <span></span>
        </div>
        ${plugins.map((plugin) => `
          <div class="plugins-row" role="row" data-open-plugin="${escapeHtml(plugin.id)}">
            <span class="plugin-name-cell">
              <span class="plugin-logo">${escapeHtml(pluginInitial(plugin.name))}</span>
              <strong>${escapeHtml(plugin.name)}</strong>
            </span>
            <span><span class="plugin-status-pill ${plugin.enabled ? "enabled" : "disabled"}">${plugin.enabled ? "Enabled" : "Disabled"}</span></span>
            <span><button class="plugins-link" type="button" data-open-plugin="${escapeHtml(plugin.id)}">${plugin.connected ? "Available" : "Setup needed"}</button></span>
            <span class="plugins-muted">${escapeHtml(pluginCatalog(plugin))}</span>
            <span class="plugins-actions-cell">
              <button class="plugins-menu" type="button" data-open-plugin="${escapeHtml(plugin.id)}" title="Open plugin">...</button>
            </span>
          </div>
        `).join("") || `<div class="plugins-empty">No plugins found.</div>`}
      </div>
    </div>
  `;
  q("#pluginsBackToChat").onclick = closeMainPage;
  const search = q("#pluginsSearch");
  search.oninput = () => renderPluginsList(search.value);
  pluginsPage.querySelectorAll("[data-open-plugin]").forEach((element) => {
    element.onclick = (event) => {
      event.stopPropagation();
      openPluginSetup(element.dataset.openPlugin);
    };
  });
  search.focus();
}

function openPluginSetup(pluginId, output = "") {
  const plugin = pluginsCache.find((item) => item.id === pluginId);
  if (!plugin) return;
  activePluginId = pluginId;
  const config = pluginSavedConfig(pluginId);
  pluginsPage.innerHTML = `
    <div class="plugin-setup-shell">
      <div class="plugin-setup-head">
        <button id="pluginsBackToList" class="plugins-back" type="button">Back to plugins</button>
        <div class="plugin-setup-title">
          <span class="plugin-logo large">${escapeHtml(pluginInitial(plugin.name))}</span>
          <div>
            <h1>${escapeHtml(plugin.name)}</h1>
            <p>${escapeHtml(plugin.description || "")}</p>
          </div>
        </div>
        <button id="pluginEnableToggle" class="plugin-primary" type="button">${plugin.enabled ? "Disable" : "Enable"}</button>
      </div>
      <div class="plugin-setup-grid">
        <section class="plugin-setup-main">
          <div class="plugin-setting-row">
            <div>
              <strong>Status</strong>
              <small>${escapeHtml(plugin.status || "")}</small>
            </div>
            <span class="plugin-status-pill ${plugin.enabled ? "enabled" : "disabled"}">${plugin.enabled ? "Enabled" : "Disabled"}</span>
          </div>
          <div class="plugin-setting-row">
            <div>
              <strong>Catalog</strong>
              <small>${escapeHtml(pluginCatalog(plugin))}</small>
            </div>
            <button id="pluginConnect" type="button">Connect</button>
          </div>
          <label class="plugin-field">Workspace note
            <input id="pluginNote" value="${escapeHtml(config.note || "")}" placeholder="Token, workspace, repo, or setup note" />
          </label>
          <label class="plugin-field">Default action
            <select id="pluginDefaultAction">
              <option value="check" ${config.action === "check" ? "selected" : ""}>Run check</option>
              <option value="connect" ${config.action === "connect" ? "selected" : ""}>Connect</option>
              <option value="inside-app" ${config.action === "inside-app" ? "selected" : ""}>Use inside Aurine</option>
            </select>
          </label>
          <div class="plugin-button-row">
            <button id="pluginSaveSettings" type="button">Save setup</button>
            <button id="pluginRunCheck" type="button">Run check</button>
          </div>
        </section>
        <aside class="plugin-setup-side">
          <strong>Plugin details</strong>
          <dl>
            <dt>ID</dt><dd>${escapeHtml(plugin.id)}</dd>
            <dt>Installation policy</dt><dd>${plugin.connected ? "Available" : "Setup needed"}</dd>
            <dt>Connection</dt><dd>${plugin.connected ? "Connected" : "Not connected"}</dd>
          </dl>
          <pre id="pluginSetupOutput" class="plugin-output">${escapeHtml(output || plugin.status_detail || "")}</pre>
        </aside>
      </div>
    </div>
  `;
  q("#pluginsBackToList").onclick = () => {
    activePluginId = "";
    renderPluginsList(q("#pluginsSearch")?.value || "");
  };
  q("#pluginSaveSettings").onclick = () => {
    localStorage.setItem(pluginConfigKey(pluginId), JSON.stringify({
      note: q("#pluginNote").value,
      action: q("#pluginDefaultAction").value,
    }));
    q("#pluginSetupOutput").textContent = "Setup saved for this browser.";
  };
  q("#pluginRunCheck").onclick = () => runPluginAction(pluginId, "check");
  q("#pluginConnect").onclick = () => runPluginAction(pluginId, "connect");
  q("#pluginEnableToggle").onclick = () => togglePluginFromSetup(pluginId);
}

async function refreshPluginsAndKeepSetup(pluginId, output = "") {
  const data = await api("/plugins");
  pluginsCache = data.plugins || [];
  openPluginSetup(pluginId, output);
}

async function runPluginAction(pluginId, action = "check") {
  const output = q("#pluginSetupOutput");
  output.textContent = action === "connect" ? "Connecting..." : "Checking...";
  try {
    const data = await api("/plugins/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plugin_id: pluginId, action }),
    });
    output.textContent = data.url ? `${data.output}\n\nOpen: ${data.url}` : data.output;
  } catch (error) {
    output.textContent = error.message;
  }
}

async function togglePluginFromSetup(pluginId) {
  const plugin = pluginsCache.find((item) => item.id === pluginId);
  if (!plugin) return;
  const output = q("#pluginSetupOutput");
  const enabled = !plugin.enabled;
  if (enabled) {
    output.textContent = "Opening setup...";
    try {
      const data = await api("/plugins/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_id: pluginId, action: "connect" }),
      });
      output.textContent = data.url ? `${data.output}\n\nOpen: ${data.url}` : data.output;
    } catch (error) {
      output.textContent = error.message;
      return;
    }
  }
  await api("/plugins/toggle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plugin_id: pluginId, enabled }),
  });
  await refreshPluginsAndKeepSetup(pluginId, enabled ? "Enabled. Setup is ready inside this page." : "Disabled.");
}

async function renderLegacyPluginsPanel() {
  panelTitle.textContent = "Plugins";
  const data = await api("/plugins");
  panelBody.innerHTML = (data.plugins || []).map((plugin) => `
    <div class="panel-card plugin-card">
      <div class="panel-row">
        <strong>${escapeHtml(plugin.name)}</strong>
        <span class="plugin-state ${plugin.connected ? "ok" : "warn"}">${escapeHtml(plugin.status || (plugin.connected ? "Ready" : "Needs setup"))}</span>
      </div>
      <small>${escapeHtml(plugin.description)}</small>
      <div class="plugin-actions">
        <button data-run-plugin="${plugin.id}">Run check</button>
        <button data-connect-plugin="${plugin.id}">Connect</button>
        <button data-toggle-plugin="${plugin.id}" data-enabled="${plugin.enabled ? "1" : "0"}">${plugin.enabled ? "Disable" : "Enable"}</button>
      </div>
      <pre id="plugin-output-${plugin.id}" class="plugin-output">${escapeHtml(plugin.status_detail || "")}</pre>
    </div>`).join("");
  panelBody.querySelectorAll("[data-run-plugin]").forEach((button) => {
    button.onclick = async () => {
      const output = q(`#plugin-output-${button.dataset.runPlugin}`);
      output.textContent = "Checking...";
      try {
        const data = await api("/plugins/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plugin_id: button.dataset.runPlugin }),
        });
        output.textContent = data.output;
        if (data.url) window.open(data.url, "_blank", "noopener");
      } catch (error) {
        output.textContent = error.message;
      }
    };
  });
  panelBody.querySelectorAll("[data-connect-plugin]").forEach((button) => {
    button.onclick = async () => {
      const output = q(`#plugin-output-${button.dataset.connectPlugin}`);
      output.textContent = "Connecting...";
      try {
        const data = await api("/plugins/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plugin_id: button.dataset.connectPlugin, action: "connect" }),
        });
        output.textContent = data.output;
      } catch (error) {
        output.textContent = error.message;
      }
    };
  });
  panelBody.querySelectorAll("[data-toggle-plugin]").forEach((button) => {
    button.onclick = async () => {
      const output = q(`#plugin-output-${button.dataset.togglePlugin}`);
      const enabled = button.dataset.enabled !== "1";
      if (enabled) {
        output.textContent = "Connecting...";
        try {
          const data = await api("/plugins/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ plugin_id: button.dataset.togglePlugin, action: "connect" }),
          });
          output.textContent = data.output;
          if (data.url) window.open(data.url, "_blank", "noopener");
        } catch (error) {
          output.textContent = error.message;
          return;
        }
      }
      await api("/plugins/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_id: button.dataset.togglePlugin, enabled }),
      });
      await renderPluginsPanel();
    };
  });
}

async function renderSitesPanel() {
  panelTitle.textContent = "Sites";
  const data = await api("/sites");
  panelBody.innerHTML = (data.sites || []).map((site) =>
    panelCard(site.name, `${site.files.length} files`, `<button data-open-project="${site.id}">Open</button>`)
  ).join("") || panelCard("No sites yet", "Generate a website from Project.");
  bindProjectButtons(data.sites || []);
}

async function renderProjectPanel() {
  panelTitle.textContent = "Project";
  const docs = await api("/documents");
  const projects = await api("/code-projects");
  const artifacts = await api("/artifacts");
  panelBody.innerHTML = `
    <div class="panel-card">
      <strong>Files are always available</strong>
      <small>Use + File for photos, videos, PDFs, ZIPs, docs, code, data files, or use + Folder for a full folder.</small>
      <div id="uploadStatus">Ready for upload.</div>
    </div>
    <div class="panel-card">
      <textarea id="projectPrompt" placeholder="Describe app, software, website, API, game..."></textarea>
      <button id="generateProject">Generate project</button>
      <small id="projectStatus">Projects save here. Zip is also shown inside chat after generation.</small>
    </div>
    <h3>Uploaded data</h3>
    ${(docs.documents || []).map((x) => panelCard(x.source, `${x.chunks} chunks`)).join("") || panelCard("No uploaded files", "Add one with + File.")}
    <h3>Projects</h3>
    ${(projects.projects || []).map((p) => panelCard(p.name, `${p.files.length} files`, `<button data-open-project="${p.id}">Open</button><button data-preview-project="${p.id}">Preview</button><a class="zip-link" href="/code-projects/${p.id}/download">Zip</a>`)).join("") || panelCard("No projects", "Generate one above.")}
    <h3>Created artifacts</h3>
    ${(artifacts.artifacts || []).map((a) => panelCard(`${a.type}: ${a.title}`, a.prompt.slice(0, 120), (a.files || []).map((f) => `<a class="zip-link" href="/artifacts/${a.id}/download/${encodeURIComponent(f.name)}">${escapeHtml(f.name)}</a>`).join(" "))).join("") || panelCard("No artifacts", "Ask Aurine to create image, video, PDF, or document files.")}
  `;
  q("#generateProject").onclick = async () => {
    const prompt = q("#projectPrompt").value.trim();
    if (!prompt) return;
    q("#projectStatus").textContent = "Generating...";
    const data = await api("/code-projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    await renderProjectPanel();
    await openProject(data.project);
    await previewProject(data.project, true);
    addProjectMessage(data.project);
  };
  bindProjectButtons(projects.projects || []);
}

function bindProjectButtons(projects) {
  panelBody.querySelectorAll("[data-open-project]").forEach((button) => {
    button.onclick = () => openProject(projects.find((p) => p.id === button.dataset.openProject));
  });
  panelBody.querySelectorAll("[data-preview-project]").forEach((button) => {
    button.onclick = () => previewProject(projects.find((p) => p.id === button.dataset.previewProject));
  });
}

async function openPanel(panel) {
  document.querySelectorAll(".nav-action").forEach((b) => b.classList.toggle("active", b.dataset.panel === panel));
  if (panel !== "plugins") {
    pluginsPage.hidden = true;
    messages.hidden = false;
  }
  if (panel !== "agents") {
    agentsPage.hidden = true;
    messages.hidden = false;
  }
  if (panel !== "models") {
    modelsPage.hidden = true;
    messages.hidden = false;
  }
  if (panel !== "apiKeys") {
    apiKeysPage.hidden = true;
    messages.hidden = false;
  }
  if (panel !== "settings") {
    settingsPage.hidden = true;
    messages.hidden = false;
  }
  cloudPanel.hidden = false;
  if (panel === "search") return renderSearchPanel();
  if (panel === "models") return renderModelsPanel();
  if (panel === "apiKeys") return renderApiKeysPanel();
  if (panel === "agents") return renderAgentsPanel();
  if (panel === "scheduled") return renderScheduledPanel();
  if (panel === "plugins") return renderPluginsPanel();
  if (panel === "sites") return renderSitesPanel();
  if (panel === "project") return renderProjectPanel();
  if (panel === "settings") return renderSettingsPage();
  cloudPanel.hidden = true;
}

loginForm.onsubmit = async (event) => {
  event.preventDefault();
  loginStatus.textContent = "Signing in...";
  try {
    const data = await api("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: loginName.value, email: loginEmail.value, password: loginPassword.value }),
    });
    authToken = data.token;
    localStorage.setItem(tokenKey, authToken);
    applyProfile(data);
    showApp();
    await loadChats();
  } catch (error) {
    loginStatus.textContent = error.message;
  }
};

googleLoginButton.onclick = async () => {
  try {
    const status = await api("/auth/google/status");
    if (!status.configured) {
      loginStatus.textContent = "Opening Google demo workspace...";
      const data = await api("/auth/google/demo", { method: "POST" });
      authToken = data.token;
      localStorage.setItem(tokenKey, authToken);
      applyProfile(data);
      showApp();
      await loadChats();
      return;
    }
    loginStatus.textContent = `Opening Google. In Google Cloud, Authorized redirect URI must be: ${status.authorized_redirect_uri || status.redirect_uri}`;
    location.href = "/auth/google/start";
  } catch (error) {
    loginStatus.textContent = error.message;
  }
};

demoLoginButton.onclick = async () => {
  loginStatus.textContent = "Opening demo workspace...";
  try {
    const data = await api("/auth/demo", { method: "POST" });
    authToken = data.token;
    localStorage.setItem(tokenKey, authToken);
    applyProfile(data);
    showApp();
    await loadChats();
  } catch (error) {
    loginStatus.textContent = error.message;
  }
};

chatForm.onsubmit = (e) => {
  e.preventDefault();
  const text = questionInput.value;
  questionInput.value = "";
  ask(text);
};
floatingChatForm.onsubmit = (e) => {
  e.preventDefault();
  const text = floatingQuestionInput.value;
  floatingQuestionInput.value = "";
  ask(text);
};

newChatButton.onclick = startNewChat;
function openAgentCreate() {
  openPanel("agents").then(() => {
    const form = q("#agentCreateInline");
    if (form) form.hidden = false;
    q("#inlineAgentName")?.focus();
  });
}
if (browseAgentsButton) browseAgentsButton.onclick = openAgentCreate;
if (browseAgentsRow) browseAgentsRow.onclick = openAgentCreate;
function openBrowsePlugins() {
  openPanel("plugins");
}
if (browsePluginsButton) browsePluginsButton.onclick = openBrowsePlugins;
if (browsePluginsRow) browsePluginsRow.onclick = openBrowsePlugins;
clearDataButton.onclick = async () => {
  await api("/clear-data", { method: "POST" });
  chats = [];
  createLocalChat();
  render();
  await openPanel("project");
};
logoutButton.onclick = () => {
  sessionStorage.removeItem(tokenKey);
  localStorage.removeItem(tokenKey);
  authToken = "";
  showLogin("Logged out.");
};
closePanel.onclick = () => cloudPanel.hidden = true;
if (closeAgentCreate) closeAgentCreate.onclick = () => agentCreateModal.hidden = true;
if (createAgentForm) {
  createAgentForm.onsubmit = async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector("button[type='submit']");
    button.disabled = true;
    button.textContent = "Creating...";
    try {
      const data = await api("/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: q("#newAgentName").value,
          detail: q("#newAgentDetail").value,
          instructions: q("#newAgentInstructions").value,
        }),
      });
      customAgents.unshift(data.agent);
      renderAgentRail();
      createAgentForm.reset();
      agentCreateModal.hidden = true;
      await openAgentChat(data.agent.id);
    } catch (error) {
      button.textContent = error.message;
    } finally {
      button.disabled = false;
      if (button.textContent !== "Create agent") {
        setTimeout(() => { button.textContent = "Create agent"; }, 1400);
      }
    }
  };
}
document.querySelectorAll("[data-panel]").forEach((button) => {
  if (button.dataset.panel === "chat") {
    button.onclick = startNewChat;
  } else {
    button.onclick = () => openPanel(button.dataset.panel);
  }
});
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.onclick = () => {
    questionInput.value = button.dataset.prompt;
    questionInput.focus();
  };
});
[fileInput, fileInputInline, floatingFileInput].forEach((input) => {
  if (!input) return;
  input.accept = uploadAcceptTypes;
  input.multiple = true;
  input.onchange = () => uploadSelectedFiles(input.files);
});
if (folderInput) {
  folderInput.multiple = true;
  folderInput.webkitdirectory = true;
  folderInput.onchange = () => uploadSelectedFiles(folderInput.files);
}
agentChip.onclick = clearCurrentAgent;
floatingAgentChip.onclick = clearCurrentAgent;
workspaceButton.onclick = () => openPanel("settings");
closeSettings.onclick = () => settingsModal.hidden = true;
settingsForm.onsubmit = async (event) => {
  event.preventDefault();
  const data = await api("/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: settingsName.value,
      workspace_name: settingsWorkspace.value,
      theme: settingsTheme.value,
    }),
  });
  applyProfile(data);
  settingsModal.hidden = true;
};
fileSelect.onchange = () => loadFile(fileSelect.value);
saveFileButton.onclick = async () => {
  if (!activeProject || !activeFile) return;
  await api(`/code-projects/${activeProject.id}/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: activeFile, content: fileEditor.value }),
  });
  terminalOutput.textContent = `Saved ${activeFile}`;
};
commandForm.onsubmit = async (event) => {
  event.preventDefault();
  if (!activeProject || !commandInput.value.trim()) return;
  terminalOutput.textContent = `Running: ${commandInput.value}`;
  try {
    const data = await api(`/code-projects/${activeProject.id}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: commandInput.value.trim() }),
    });
    terminalOutput.textContent = data.output;
  } catch (error) {
    terminalOutput.textContent = error.message;
  }
};
closeWorkspace.onclick = () => {
  workspacePanel.hidden = true;
  render();
};
if (closePreview) {
  closePreview.onclick = () => {
    previewPanel.hidden = true;
    previewFrame.src = "about:blank";
  };
}
if (composerModelButton) composerModelButton.onclick = () => openModelDropdown(composerModelButton);
if (floatingModelButton) floatingModelButton.onclick = () => openModelDropdown(floatingModelButton);
document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  if (target.closest(".model-dropdown") || target.closest(".model-chip")) return;
  closeModelDropdown();
});
[questionInput, floatingQuestionInput].forEach((el) => {
  el.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      (el === questionInput ? chatForm : floatingChatForm).requestSubmit();
    }
  });
});

async function boot() {
  renderModelButton();
  if (!authToken) return showLogin();
  try {
    const data = await api("/me");
    if (!data.authenticated) return showLogin("Session expired. Login again.");
    applyProfile(data);
    showApp();
    await loadPlugins();
    await loadChats();
  } catch {
    showLogin("Login required.");
  }
}

boot();


