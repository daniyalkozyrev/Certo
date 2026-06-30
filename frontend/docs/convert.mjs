import { readFileSync, writeFileSync } from "node:fs";

const md = readFileSync(process.argv[2], "utf8");

function inline(s) {
  return s
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
}

const lines = md.split(/\r?\n/);
let html = "";
let i = 0;
let para = [];
const flushPara = () => { if (para.length) { html += `<p>${inline(para.join(" "))}</p>\n`; para = []; } };

while (i < lines.length) {
  const line = lines[i];

  // fenced code
  if (line.startsWith("```")) {
    flushPara();
    i++;
    let code = "";
    while (i < lines.length && !lines[i].startsWith("```")) { code += lines[i] + "\n"; i++; }
    i++;
    html += `<pre><code>${code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</code></pre>\n`;
    continue;
  }

  // table
  if (line.trim().startsWith("|") && i + 1 < lines.length && /^\s*\|?\s*-/.test(lines[i + 1]) && lines[i + 1].includes("-")) {
    flushPara();
    const header = line.split("|").slice(1, -1).map((c) => c.trim());
    i += 2;
    const rows = [];
    while (i < lines.length && lines[i].trim().startsWith("|")) {
      rows.push(lines[i].split("|").slice(1, -1).map((c) => c.trim()));
      i++;
    }
    html += "<table><thead><tr>" + header.map((h) => `<th>${inline(h)}</th>`).join("") + "</tr></thead><tbody>";
    for (const r of rows) html += "<tr>" + r.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>";
    html += "</tbody></table>\n";
    continue;
  }

  // heading
  const h = line.match(/^(#{1,6})\s+(.*)$/);
  if (h) { flushPara(); const lvl = h[1].length; html += `<h${lvl}>${inline(h[2])}</h${lvl}>\n`; i++; continue; }

  // hr
  if (/^---+\s*$/.test(line)) { flushPara(); html += "<hr/>\n"; i++; continue; }

  // blockquote
  if (line.startsWith(">")) {
    flushPara();
    let bq = "";
    while (i < lines.length && lines[i].startsWith(">")) { bq += lines[i].replace(/^>\s?/, "") + " "; i++; }
    html += `<blockquote>${inline(bq.trim())}</blockquote>\n`;
    continue;
  }

  // unordered list
  if (/^\s*[-*]\s+/.test(line)) {
    flushPara();
    html += "<ul>";
    while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { html += `<li>${inline(lines[i].replace(/^\s*[-*]\s+/, ""))}</li>`; i++; }
    html += "</ul>\n";
    continue;
  }

  // ordered list
  if (/^\s*\d+\.\s+/.test(line)) {
    flushPara();
    html += "<ol>";
    while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) { html += `<li>${inline(lines[i].replace(/^\s*\d+\.\s+/, ""))}</li>`; i++; }
    html += "</ol>\n";
    continue;
  }

  // blank
  if (line.trim() === "") { flushPara(); i++; continue; }

  para.push(line);
  i++;
}
flushPara();

const doc = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>NURDACERTO</title>
<style>
:root{--ink:#0b1220;--muted:#5b6677;--line:#e4e8ef;--soft:#f5f7fb;--accent:#4f46e5;--accent2:#06b6d4;}
*{box-sizing:border-box}html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;font-family:"Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif;color:var(--ink);font-size:11px;line-height:1.6}
@page{size:A4;margin:15mm 14mm}
h1{font-size:30px;letter-spacing:-.6px;margin:0 0 4px;background:linear-gradient(120deg,#4f46e5,#06b6d4);-webkit-background-clip:text;background-clip:text;color:transparent}
h2{font-size:17px;margin:22px 0 8px;padding-bottom:6px;border-bottom:2px solid var(--line);letter-spacing:-.3px}
h3{font-size:13px;margin:14px 0 4px;color:#1b2440}
h4{font-size:11.5px;margin:10px 0 3px}
p{margin:6px 0}ul,ol{margin:6px 0;padding-left:20px}li{margin:3px 0}
strong{color:#0b1220}em{color:var(--muted)}
code{background:#eef1f7;padding:1px 5px;border-radius:4px;font-family:"Cascadia Code",Consolas,monospace;font-size:10px}
pre{background:#0c1024;color:#d7def0;border-radius:10px;padding:13px 15px;font-size:9.4px;line-height:1.5;overflow:hidden;font-family:"Cascadia Code",Consolas,monospace;margin:9px 0;white-space:pre-wrap}
pre code{background:none;color:inherit;padding:0}
blockquote{margin:10px 0;padding:10px 14px;border-left:3px solid var(--accent);background:var(--soft);border-radius:0 8px 8px 0;color:#23304d}
table{width:100%;border-collapse:collapse;margin:9px 0;font-size:10.2px}
th{background:var(--soft);text-align:left;font-weight:700;color:#2b3340}
th,td{border:1px solid var(--line);padding:6px 9px;vertical-align:top}
tr{break-inside:avoid}h2,h3{break-after:avoid}
hr{border:none;border-top:1px solid var(--line);margin:18px 0}
.cover{background:radial-gradient(120% 120% at 20% -10%,#1b2150,#0c1024 55%,#070a18);color:#fff;border-radius:16px;padding:30px 32px;margin-bottom:8px}
.cover h1{font-size:42px;color:#fff;background:none;-webkit-text-fill-color:#fff}
.cover .p{background:linear-gradient(120deg,#a5b4fc,#22d3ee);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
</style></head><body>
<div class="cover"><h1>NURDA<span class="p">CERTO</span></h1><div style="color:#aeb8cc;font-size:13px;margin-top:4px">Техническая документация Certo «под капотом» — для защиты в ISSAI SRP</div></div>
${html}
</body></html>`;

writeFileSync(process.argv[3], doc, "utf8");
console.log("HTML written:", process.argv[3]);
