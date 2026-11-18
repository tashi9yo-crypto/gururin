#!/usr/bin/env python3
"""소설/*.md 와 부록을 읽어 webapp/index.html 한 파일로 묶는다.

사용법:  python3 webapp/build.py
템플릿:  webapp/template.html  ( /*__BOOK__*/ 자리에 책 데이터가 들어간다 )
"""
import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "webapp")

PARTS = {
    0: ("제1부", "연꽃에서 태어난 자"),
    7: ("제2부", "설산을 넘는 길"),
    16: ("제3부", "붉은 바위의 왕"),
    20: ("제4부", "법을 구하는 사람들"),
    26: ("제5부", "구리빛 산으로"),
}

APPENDICES = [
    ("부록_사실과_각색.md", "부록 1 — 장별 출처와 각색"),
    ("부록_영상화_노트.md", "부록 2 — 영상화 노트"),
]


def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    # 링크는 본문 밖 파일을 가리키므로 글자만 남긴다
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = t.replace("`", "")
    return t


def md_to_html(md: str, drop_title: bool = True):
    """이 원고에서 쓰는 마크다운만 처리한다: 제목, 인용(게송), 구분선, 표, 목록, 문단."""
    lines = md.strip("\n").split("\n")
    out = []
    title = None
    epigraph = None
    i = 0
    if lines and lines[0].startswith("## "):
        title = lines[0][3:].strip()
        i = 1
    # 장 머리의 게송 한 줄
    j = i
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j < len(lines) and re.match(r"^> \*.*\*\s*$", lines[j]):
        epigraph = inline(lines[j][2:].strip().strip("*"))
        i = j + 1

    para = []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush()
            i += 1
            continue
        if s == "---":
            flush()
            out.append('<div class="ornament" aria-hidden="true">❋</div>')
            i += 1
            continue
        if s.startswith("#"):
            flush()
            level = len(s) - len(s.lstrip("#"))
            tag = "h3" if level <= 3 else "h4"
            out.append(f"<{tag}>{inline(s.lstrip('#').strip())}</{tag}>")
            i += 1
            continue
        if s.startswith(">"):
            flush()
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip()[1:].strip())
                i += 1
            stanzas, cur = [], []
            for b in block:
                if b:
                    cur.append(inline(b))
                elif cur:
                    stanzas.append(cur)
                    cur = []
            if cur:
                stanzas.append(cur)
            inner = "".join("<p>" + "<br>".join(st) + "</p>" for st in stanzas)
            out.append(f'<blockquote class="verse">{inner}</blockquote>')
            continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            body = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            if body:
                head, rest = body[0], body[1:]
                h = "".join(f"<th>{inline(c)}</th>" for c in head)
                b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rest)
                out.append(f'<div class="table-wrap"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>')
            continue
        if re.match(r"^[-*] ", s):
            flush()
            items = []
            while i < len(lines) and re.match(r"^\s*[-*] ", lines[i]):
                items.append(inline(re.sub(r"^\s*[-*] ", "", lines[i])))
                i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue
        para.append(s)
        i += 1
    flush()
    return title, epigraph, "\n".join(out)


def split_title(t: str):
    m = re.match(r"^(제\d+장|서장|종장)\.\s*(.+)$", t)
    if m:
        return m.group(1), m.group(2)
    return "", t


def main():
    chapters = []
    for path in sorted(glob.glob(os.path.join(ROOT, "소설", "*.md"))):
        n = int(os.path.basename(path)[:2])
        md = open(path, encoding="utf-8").read()
        title, epi, body = md_to_html(md)
        label, name = split_title(title or "")
        part = PARTS.get(n)
        chapters.append({
            "id": f"c{n:02d}",
            "label": label,
            "title": name,
            "epigraph": epi,
            "part": {"label": part[0], "title": part[1]} if part else None,
            "html": body,
            "chars": len(re.sub(r"<[^>]+>", "", body)),
        })
    for fname, t in APPENDICES:
        md = open(os.path.join(ROOT, fname), encoding="utf-8").read()
        md = re.sub(r"^# .*\n", "", md, count=1)
        _, _, body = md_to_html("## x\n" + md)
        chapters.append({
            "id": "a" + str(len([c for c in chapters if c["id"].startswith("a")]) + 1),
            "label": "부록",
            "title": t.split("—", 1)[1].strip(),
            "epigraph": None,
            "part": {"label": "부록", "title": "책 뒤에"} if fname == APPENDICES[0][0] else None,
            "html": body,
            "chars": len(re.sub(r"<[^>]+>", "", body)),
            "appendix": True,
        })
    book = {
        "title": "연화생전",
        "hanja": "蓮花生傳",
        "subtitle": "설산을 넘는 스승",
        "blurb": "낮에 쌓은 절이 밤마다 무너지는 눈의 나라. 왕의 부름을 받은 한 수행자가 히말라야를 넘는다. 그는 귀신을 죽이지 않는다. 맹세하게 만든다.",
        "chapters": chapters,
    }
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    data = json.dumps(book, ensure_ascii=False).replace("</", "<\\/")
    out = tpl.replace("/*__BOOK__*/null", data)
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(out)
    total = sum(c["chars"] for c in chapters if not c.get("appendix"))
    print(f"webapp/index.html: {len(chapters)}개 장, 본문 {total:,}자, {len(out.encode()):,} bytes")


if __name__ == "__main__":
    main()
