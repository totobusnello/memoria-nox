"""Per-arm system prompt assembly from the captured OpenClaw template (spec §4).

Rules (frozen; declared limits in spec §8): file sections are rebuilt in template order for the owner
agent; the brief section is the only arm-dependent part; in the generated tail, `Current date` is set to
the date of t, `Conversation Context` is kept only for stratum R (forge Discord, as captured), and the
`Runtime:` line is reduced to `agent=<owner> | host=openclaw` (session ids are per-run noise).
"""
import os
import re

WS = "/root/.openclaw/workspace"
FILE_HDR = re.compile(r"^## (/root/\.openclaw/workspace/\S+\.md)$")
TAIL_HDR = "## Temporal Context"
ORDER = ["AGENTS.md", "SOUL.md", "IDENTITY.md", "USER.md", "brief/MEMORY.md", "MEMORY.md"]
BOOTSTRAP = [n for n in ORDER if n != "brief/MEMORY.md"]


def agent_root(agent):
    return WS if agent == "main" else f"{WS}/agents/{agent}"


def parse_template(text):
    if text.count("\n" + TAIL_HDR + "\n") != 1:
        raise ValueError("template must contain exactly one tail header")
    head, sections, tail, cur, in_tail = [], [], [], None, False
    for ln in text.split("\n"):
        if in_tail:
            tail.append(ln)
            continue
        if ln == TAIL_HDR:
            in_tail = True
            tail.append(ln)
            continue
        m = FILE_HDR.match(ln)
        if m:
            cur = [m.group(1), []]
            sections.append(cur)
            continue
        (cur[1] if cur else head).append(ln)
    # Blank lines between the last file and the tail are OpenClaw's separator, not file content.
    sep = 0
    if sections:
        while sections[-1][1] and sections[-1][1][-1] == "":
            sections[-1][1].pop()
            sep += 1
    return {"head": head, "sections": [(p, "\n".join(c)) for p, c in sections], "tail": tail, "sep": sep}


def _tail(lines, agent, date, keep_conversation):
    out, skip = [], False
    for ln in lines:
        if ln.startswith("## "):
            skip = ln == "## Conversation Context" and not keep_conversation
        if skip:
            continue
        if ln.startswith("Current date: "):
            ln = f"Current date: {date}"
        elif ln.startswith("Runtime: "):
            ln = f"Runtime: agent={agent} | host=openclaw"
        out.append(ln)
    return out


def build_prompt(tpl, agent, files, brief_block, date, keep_conversation):
    root = agent_root(agent)
    out = [f"Working directory: {root}" if l.startswith("Working directory: ") else l for l in tpl["head"]]
    for name in ORDER:
        if name == "brief/MEMORY.md":
            if brief_block is None:
                continue
            content = brief_block
        elif name in files:
            content = files[name]
        else:
            continue
        out += [f"## {root}/{name}", content.rstrip("\n")]
    out += [""] * tpl.get("sep", 0)
    out += _tail(tpl["tail"], agent, date, keep_conversation)
    return "\n".join(out)


def strip_brief(text, agent):
    root = agent_root(agent)
    out, skip = [], False
    for ln in text.split("\n"):
        if ln == f"## {root}/brief/MEMORY.md":
            skip = True
            continue
        if skip and (ln.startswith(f"## {root}/") or ln == TAIL_HDR):
            skip = False
        if not skip:
            out.append(ln)
    return "\n".join(out)


def assert_only_brief_differs(texts, agent):
    stripped = {arm: strip_brief(t, agent) for arm, t in texts.items()}
    first = next(iter(stripped.values()))
    for arm, s in stripped.items():
        assert s == first, f"arm {arm} differs outside the brief block"


def read_bootstrap(agent):
    root, files = agent_root(agent), {}
    for name in BOOTSTRAP:
        p = os.path.join(root, name)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                files[name] = f.read()
    return files
