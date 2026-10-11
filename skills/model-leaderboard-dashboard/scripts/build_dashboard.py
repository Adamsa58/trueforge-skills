#!/usr/bin/env python3
"""Build a self-contained interactive HTML dashboard from extract.py output.

Reads /opt/tf/work/models.json and tables.json, writes
/opt/tf/work/dashboard.html (no external scripts, works offline).

Usage: python3 build_dashboard.py [work_dir]
"""
import datetime
import json
import os
import sys

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open Model Leaderboard</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--text:#1b1f24;--muted:#5d6672;--line:#dde1e6;--accent:#3b6fe0;--bar:#6f93ea}
@media (prefers-color-scheme:dark){:root{--bg:#131619;--card:#1c2025;--text:#e6e9ed;--muted:#9aa3ad;--line:#2d333a;--accent:#7aa2ff;--bar:#4f74c9}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,Segoe UI,Roboto,sans-serif}
header{padding:20px 16px 8px;max-width:1280px;margin:auto}h1{margin:0 0 4px;font-size:22px}
.sub{color:var(--muted)}main{max-width:1280px;margin:auto;padding:0 16px 40px}
.tiles{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:140px}
.tile b{display:block;font-size:22px}.tabs{display:flex;gap:6px;margin:16px 0 10px;flex-wrap:wrap}
.tabs button,select,input{font:inherit;color:var(--text);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.tabs button.on{border-color:var(--accent);color:var(--accent);font-weight:600}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:14px}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.controls input{flex:1;min-width:180px}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{cursor:pointer;user-select:none;position:sticky;top:0;background:var(--card)}th:hover{color:var(--accent)}
td.num{text-align:right;font-variant-numeric:tabular-nums}.muted{color:var(--muted)}a{color:var(--accent)}
.bar{display:grid;grid-template-columns:minmax(120px,240px) 1fr 70px;gap:8px;align-items:center;margin:3px 0}
.bar .track{background:var(--line);border-radius:4px;height:14px}.bar .fill{background:var(--bar);height:14px;border-radius:4px}
.hidden{display:none}h2{font-size:16px;margin:0 0 8px}h3{font-size:14px;margin:14px 0 6px}
</style></head><body>
<header><h1>Open-weight &amp; open-source model leaderboard</h1>
<div class="sub">Built __BUILT__ from __NSRC__ sources. Values are copied from each source as published; sources measure different things, so compare within a column.</div>
<div class="tiles" id="tiles"></div></header>
<main>
<div class="tabs"><button class="on" data-tab="overview">Overview</button><button data-tab="chart">Chart</button><button data-tab="sources">Source tables</button></div>
<section id="overview" class="panel"><div class="controls">
<input id="q" placeholder="Search model or creator"><select id="creator"><option value="">All creators</option></select>
<select id="lic"><option value="">Any license</option></select></div>
<div class="scroll"><table id="ov"></table></div></section>
<section id="chart" class="panel hidden"><div class="controls"><select id="metric"></select></div><div id="bars"></div></section>
<section id="sources" class="panel hidden"><div id="srcs"></div></section>
</main>
<script>
const MODELS=__MODELS__, SOURCES=__SOURCES__;
const $=s=>document.querySelector(s), esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function num(v){if(v==null)return NaN;const m=String(v).replace(/,/g,"").match(/-?\d+(\.\d+)?/);if(!m)return NaN;let n=parseFloat(m[0]);
 const u=String(v).slice(m.index+m[0].length).trim().charAt(0).toUpperCase();return n*({K:1e3,M:1e6,B:1e9,T:1e12}[u]||1);}
const metricNames=[...new Set(MODELS.flatMap(m=>Object.keys(m.metrics)))].map(k=>[k,MODELS.filter(m=>m.metrics[k]).length]).sort((a,b)=>b[1]-a[1]).map(x=>x[0]);
const topMetrics=metricNames.slice(0,5);
const cols=[["name","Model"],["creator","Creator"]].concat(topMetrics.map(k=>["m:"+k,k]))
 .concat([["params","Parameters"],["context","Context"],["license","License"],["speed","Speed"],["price","Price"]].filter(([k])=>MODELS.some(m=>m[k])))
 .concat([["sources","Sources"]]);
const val=(m,k)=>k.startsWith("m:")?m.metrics[k.slice(2)]:k==="sources"?m.sources.join(", "):m[k];
let sortKey=topMetrics[0]?"m:"+topMetrics[0]:"name", sortDir=-1;
function cmp(a,b,k){const x=val(a,k),y=val(b,k),nx=num(x),ny=num(y);
 if(x==null||x==="")return 1; if(y==null||y==="")return -1;
 if(!isNaN(nx)&&!isNaN(ny)&&k!=="name"&&k!=="creator"&&k!=="license")return (nx-ny)*sortDir; return String(x).localeCompare(String(y))*sortDir;}
function renderOverview(){const q=$("#q").value.toLowerCase(),c=$("#creator").value,l=$("#lic").value;
 const rows=MODELS.filter(m=>(!q||(m.name+" "+(m.creator||"")).toLowerCase().includes(q))&&(!c||m.creator===c)&&(!l||m.license===l)).sort((a,b)=>cmp(a,b,sortKey));
 $("#ov").innerHTML="<thead><tr>"+cols.map(([k,t])=>`<th data-k="${esc(k)}">${esc(t)}${k===sortKey?(sortDir<0?" ▼":" ▲"):""}</th>`).join("")+"</tr></thead><tbody>"+
 rows.map(m=>"<tr>"+cols.map(([k])=>{const v=val(m,k);return `<td class="${k.startsWith("m:")?"num":""}">${v?esc(v):'<span class="muted">–</span>'}</td>`}).join("")+"</tr>").join("")+"</tbody>";
 $("#ov").querySelectorAll("th").forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortDir=k===sortKey?-sortDir:(k==="name"?1:-1);sortKey=k;renderOverview();});}
function renderBars(){const k=$("#metric").value;const rows=MODELS.filter(m=>!isNaN(num(m.metrics[k]))).sort((a,b)=>num(b.metrics[k])-num(a.metrics[k])).slice(0,20);
 const max=Math.max(...rows.map(m=>num(m.metrics[k])),1);
 $("#bars").innerHTML=rows.length?rows.map(m=>`<div class="bar"><span>${esc(m.name)}</span><div class="track"><div class="fill" style="width:${(num(m.metrics[k])/max*100).toFixed(1)}%"></div></div><span class="num">${esc(m.metrics[k])}</span></div>`).join(""):'<p class="muted">No numeric values for this metric.</p>';}
function renderSources(){$("#srcs").innerHTML=SOURCES.map(s=>`<h2>${esc(s.title||s.url)}</h2><div class="muted"><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)}</a> · ${s.tables.length} tables</div>`+
 s.tables.map(t=>`<h3>${esc(t.heading||"Table")} <span class="muted">(${t.rows.length} rows)</span></h3><div class="scroll"><table class="src"><thead><tr>${t.columns.map(c=>`<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${
 t.rows.map(r=>"<tr>"+t.columns.map(c=>`<td>${esc(r[c])}</td>`).join("")+"</tr>").join("")}</tbody></table></div>`).join("")).join("<hr>");
 document.querySelectorAll("table.src").forEach(tb=>{let dir=1;tb.querySelectorAll("th").forEach((th,i)=>th.onclick=()=>{const body=tb.tBodies[0];dir=-dir;
 [...body.rows].sort((a,b)=>{const x=a.cells[i].textContent,y=b.cells[i].textContent,nx=num(x),ny=num(y);return(!isNaN(nx)&&!isNaN(ny)?nx-ny:x.localeCompare(y))*dir}).forEach(r=>body.appendChild(r));});});}
const uniq=k=>[...new Set(MODELS.map(m=>m[k]).filter(Boolean))].sort();
uniq("creator").forEach(c=>$("#creator").add(new Option(c,c)));uniq("license").forEach(c=>$("#lic").add(new Option(c,c)));
metricNames.forEach(k=>$("#metric").add(new Option(k,k)));
$("#tiles").innerHTML=[["Models",MODELS.length],["Sources",SOURCES.length],["Tables",SOURCES.reduce((a,s)=>a+s.tables.length,0)],["Metrics",metricNames.length]].map(([t,v])=>`<div class="tile"><b>${v}</b>${t}</div>`).join("");
["#q","#creator","#lic"].forEach(s=>$(s).oninput=renderOverview);$("#metric").onchange=renderBars;
document.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tabs button").forEach(x=>x.classList.toggle("on",x===b));
 ["overview","chart","sources"].forEach(id=>$("#"+id).classList.toggle("hidden",id!==b.dataset.tab));});
renderOverview();renderBars();renderSources();
</script></body></html>
"""


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else "/opt/tf/work"
    try:
        with open(os.path.join(work, "models.json"), encoding="utf-8") as f:
            models = json.load(f)
        with open(os.path.join(work, "tables.json"), encoding="utf-8") as f:
            sources = json.load(f)
    except FileNotFoundError as e:
        sys.exit("Missing %s. Run extract.py first." % e.filename)
    if not models:
        sys.exit("models.json is empty. Check the extract.py output.")

    def js(obj):
        # Keep the embedded JSON from closing the <script> tag early.
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    html = (TEMPLATE
            .replace("__MODELS__", js(models))
            .replace("__SOURCES__", js(sources))
            .replace("__NSRC__", str(len(sources)))
            .replace("__BUILT__", datetime.date.today().isoformat()))
    out = os.path.join(work, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote %s (%d models, %d sources, %d KB)" % (out, len(models), len(sources), os.path.getsize(out) // 1024))


if __name__ == "__main__":
    main()
