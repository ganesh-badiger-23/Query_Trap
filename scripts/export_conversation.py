"""Export the complete conversation history from transcript_full.jsonl into a comprehensive document."""
import json
import re
from datetime import datetime
from pathlib import Path

TRANSCRIPT_PATH = Path(r"C:\Users\GANESH BADIGER\.gemini\antigravity\brain\4c0ba09a-0ebb-4823-b06d-10344befccf3\.system_generated\logs\transcript_full.jsonl")
OUTPUT_MD_PATH = Path(r"d:\Projects\Query_Trap\CONVERSATION_HISTORY.md")

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Strip excessive trailing/leading whitespace
    return text.strip()

def format_timestamp(ts_str: str) -> str:
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts_str or "Unknown time"

def export_conversation():
    if not TRANSCRIPT_PATH.exists():
        print(f"Error: {TRANSCRIPT_PATH} not found!")
        return

    entries = []
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(data)
            except Exception as e:
                print(f"Skipping line {line_num}: {e}")

    print(f"Loaded {len(entries)} transcript entries.")

    # Process into turns
    turns = []
    current_user_turn = None
    current_assistant_content = []
    current_actions = []

    for entry in entries:
        etype = entry.get("type")
        source = entry.get("source")
        content = entry.get("content") or ""
        created_at = entry.get("created_at") or ""
        tool_calls = entry.get("tool_calls") or []

        if etype == "USER_INPUT" and source == "USER_EXPLICIT":
            # If we had a previous turn accumulating, save it
            if current_user_turn:
                turns.append({
                    "user": current_user_turn,
                    "actions": current_actions,
                    "assistant": "\n\n".join(current_assistant_content),
                })
                current_actions = []
                current_assistant_content = []

            # Clean user content
            # Remove <CONTEXT_SUMMARY>...</CONTEXT_SUMMARY> wrapper if present in context injection
            cleaned_content = content
            if "<CONTEXT_SUMMARY>" in cleaned_content:
                parts = re.split(r"</CONTEXT_SUMMARY>\s*", cleaned_content, flags=re.DOTALL)
                if len(parts) > 1:
                    cleaned_content = parts[-1].strip()

            # Remove <USER_REQUEST> tags if present
            req_match = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", cleaned_content, flags=re.DOTALL)
            if req_match:
                cleaned_content = req_match.group(1).strip()

            current_user_turn = {
                "text": cleaned_content,
                "timestamp": format_timestamp(created_at),
                "step": entry.get("step_index"),
                "media": entry.get("media", [])
            }

        elif etype == "PLANNER_RESPONSE":
            # Capture assistant content text
            if content and isinstance(content, str) and content.strip():
                # Avoid duplicates
                if not current_assistant_content or current_assistant_content[-1] != content.strip():
                    current_assistant_content.append(content.strip())

            # Capture tool actions
            for tc in tool_calls:
                tname = tc.get("tool_name") or tc.get("name") or "tool"
                args = tc.get("args") or tc.get("parameters") or {}
                summary = args.get("toolSummary") or ""
                cmd = args.get("CommandLine") or ""
                path = args.get("Path") or ""
                
                desc = summary
                if not desc:
                    if cmd:
                        desc = f"`{cmd[:80]}`"
                    elif path:
                        desc = f"`{Path(path).name}`"
                    else:
                        desc = tname
                current_actions.append(f"{tname}: {desc}")

    # Add last turn
    if current_user_turn:
        turns.append({
            "user": current_user_turn,
            "actions": current_actions,
            "assistant": "\n\n".join(current_assistant_content),
        })

    print(f"Extracted {len(turns)} conversation turns.")

    # Build Markdown document
    doc = []
    doc.append("# Query Trap / Sentinel DB — Complete Project Conversation & Development History\n")
    doc.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    doc.append(f"**Conversation ID:** `4c0ba09a-0ebb-4823-b06d-10344befccf3`\n")
    doc.append(f"**Workspace:** `d:\\Projects\\Query_Trap`\n")
    doc.append(f"**Total Interactive Dialogue Turns:** {len(turns)}\n\n")

    doc.append("---\n\n")
    doc.append("## Executive Project Overview\n\n")
    doc.append("This document contains the complete, chronological conversation record of the development, architecture refactoring, deception engineering, and presentation preparation for **Sentinel DB / Query Trap**.\n\n")
    doc.append("### Major Milestones Accomplished in this Conversation:\n")
    doc.append("1. **Folder & Architectural Separation**: Clean separation of `backend/` (Flask, Sentinel Gateway, Synthetic Data) and `frontend/` (Templates, Static CSS/JS) with root backward-compatibility shims.\n")
    doc.append("2. **Stealth E-Commerce Facade Revamp**: Refactored the storefront into an authentic artisanal workspace brand (*Harbor & Pine*) and removed all artificial demo banners, disclosure text, and giveaway hints.\n")
    doc.append("3. **Dynamic Threat Risk Engine**: Interception of URL queries (`?q=...`) and port reconnaissance (`?port=5100`), calculating risk scores (0-100) and transparently isolating high-risk queries.\n")
    doc.append("4. **Authentic Corporate Honeypot**: Refactored the decoy environment into *Northstar Enterprise Data Hub* with realistic SQL execution displays and zero giveaway warnings.\n")
    doc.append("5. **Database Verification Architecture**: Established a 3-tier database model (`production.db`, `honeypot.db`, in-memory synthetic canary honeytokens) and built browser (`/api/db/inspect`) and terminal (`view_databases.py`) inspection tools.\n")
    doc.append("6. **SOC Analyst Operations Portal**: Enhanced `:5100` with query classification badges (`🛍️ Product Search`, `💉 SQLi`, `🚨 Credential Probe`), real-time search filters, audit modal inspector, and JSON export.\n")
    doc.append("7. **Presentation & Judge Playbooks**: Authored `quick_implementation.txt`, `demo_commands.txt`, and `implementation.txt` for live demonstration and judge technical defense.\n\n")

    doc.append("---\n\n")
    doc.append("## Full Chronological Dialogue History\n\n")

    for idx, turn in enumerate(turns, 1):
        u = turn["user"]
        actions = turn["actions"]
        assistant_resp = turn["assistant"]

        doc.append(f"### Turn {idx} · {u['timestamp']}\n\n")
        doc.append(f"#### 👤 User Request:\n\n")
        doc.append(f"> {u['text'].replace(chr(10), chr(10) + '> ')}\n\n")

        if actions:
            # Deduplicate actions while preserving order
            unique_actions = []
            seen = set()
            for a in actions:
                if a not in seen:
                    unique_actions.append(a)
                    seen.add(a)
            
            doc.append(f"<details><summary>🛠️ <b>Actions Executed ({len(unique_actions)} steps)</b></summary>\n\n")
            for a in unique_actions[:25]:  # show up to 25 primary actions
                doc.append(f"- {a}\n")
            if len(unique_actions) > 25:
                doc.append(f"- *...and {len(unique_actions) - 25} more operations.*\n")
            doc.append("\n</details>\n\n")

        doc.append(f"#### 🤖 Antigravity Response:\n\n")
        if assistant_resp.strip():
            doc.append(f"{assistant_resp}\n\n")
        else:
            doc.append("*(Tool execution and automated verification completed)*\n\n")

        doc.append("---\n\n")

    OUTPUT_MD_PATH.write_text("".join(doc), encoding="utf-8")
    print(f"Successfully exported conversation history to: {OUTPUT_MD_PATH}")
    print(f"File size: {OUTPUT_MD_PATH.stat().st_size:,} bytes")

    # Also generate an interactive HTML document
    OUTPUT_HTML_PATH = Path(r"d:\Projects\Query_Trap\CONVERSATION_HISTORY.html")
    escaped_md = json.dumps("".join(doc))
    html_content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Query Trap / Sentinel DB — Complete Conversation History</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&family=Manrope:wght@600;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {{
      --bg: #0b111a;
      --card: #111a26;
      --border: #1e2b3c;
      --text: #e2ebf4;
      --muted: #8292a4;
      --cyan: #38c9cf;
      --amber: #f59e0b;
      --rose: #f43f5e;
      --code-bg: #070d14;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      line-height: 1.6;
      padding: 32px 20px;
    }}
    .container {{
      max-width: 980px;
      margin: 0 auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 40px 48px;
      box-shadow: 0 12px 36px rgba(0,0,0,0.4);
    }}
    h1, h2, h3, h4 {{
      font-family: 'Manrope', sans-serif;
      color: #f0f6fc;
      margin-top: 1.6em;
      margin-bottom: 0.6em;
    }}
    h1 {{
      font-size: 28px;
      color: var(--cyan);
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
      margin-top: 0;
    }}
    h2 {{ font-size: 22px; color: #7dd3fc; border-bottom: 1px solid #1a2838; padding-bottom: 8px; }}
    h3 {{ font-size: 18px; color: #cbd5e1; margin-top: 2em; }}
    h4 {{ font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
    p, li {{ color: #cbd5e1; font-size: 14px; }}
    blockquote {{
      margin: 12px 0;
      padding: 12px 18px;
      background: #162232;
      border-left: 4px solid var(--cyan);
      border-radius: 4px;
      color: #e0f2fe;
    }}
    blockquote p {{ margin: 4px 0; font-size: 14px; font-weight: 500; }}
    code {{
      font-family: 'DM Mono', monospace;
      font-size: 12px;
      background: var(--code-bg);
      color: #5eead4;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid #1e2c3c;
    }}
    pre {{
      background: var(--code-bg);
      border: 1px solid var(--border);
      padding: 14px 16px;
      border-radius: 8px;
      overflow-x: auto;
    }}
    pre code {{
      background: transparent;
      border: none;
      padding: 0;
      color: #93c5fd;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
      font-size: 13px;
    }}
    th, td {{
      padding: 9px 12px;
      border: 1px solid var(--border);
      text-align: left;
    }}
    th {{
      background: #0d1622;
      color: #94a3b8;
      font-family: 'DM Mono', monospace;
      font-size: 11px;
    }}
    tr:nth-child(even) {{ background: #0c141f; }}
    details {{
      background: #0d1521;
      border: 1px solid #1a2737;
      border-radius: 6px;
      padding: 10px 14px;
      margin: 12px 0 20px;
    }}
    summary {{
      cursor: pointer;
      color: #94a3b8;
      font-size: 13px;
      user-select: none;
    }}
    summary:hover {{ color: var(--cyan); }}
    hr {{
      border: none;
      border-top: 1px solid var(--border);
      margin: 32px 0;
    }}
    .print-btn {{
      position: fixed;
      top: 20px;
      right: 24px;
      background: #1e3a4b;
      color: #7dd3fc;
      border: 1px solid #28556e;
      padding: 8px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-family: 'DM Sans', sans-serif;
      font-weight: 600;
      font-size: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    .print-btn:hover {{ background: #24495f; color: #bae6fd; }}
    @media print {{
      .print-btn {{ display: none; }}
      body {{ background: #fff; color: #000; padding: 0; }}
      .container {{ box-shadow: none; border: none; max-width: 100%; padding: 0; }}
      pre, blockquote, details {{ page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
  <div class="container" id="content"></div>
  <script>
    const markdownText = {escaped_md};
    document.getElementById('content').innerHTML = marked.parse(markdownText);
  </script>
</body>
</html>
"""
    OUTPUT_HTML_PATH.write_text(html_content, encoding="utf-8")
    print(f"Successfully generated interactive HTML to: {OUTPUT_HTML_PATH}")
    print(f"HTML File size: {OUTPUT_HTML_PATH.stat().st_size:,} bytes")

if __name__ == "__main__":
    export_conversation()
