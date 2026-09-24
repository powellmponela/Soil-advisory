const ids=["district","crop","season","scenario"];

function cell(v){return v===null||v===undefined||v===""?"—":v}
function number(v,d=1){const n=Number(v);return Number.isFinite(n)?n.toFixed(d):"—"}

async function loadSummary(){
  const r=await fetch("/api/public/summary");
  const s=await r.json();
  document.getElementById("metric-records").textContent=s.records;
  document.getElementById("metric-districts").textContent=s.districts;
  document.getElementById("metric-scenarios").textContent=s.scenarios;
  document.getElementById("metric-crops").textContent=s.crops;
  document.getElementById("version-badge").textContent=s.versions.length?("Published: "+s.versions.join(", ")):s.status;
}

async function loadFilters(){
  const r=await fetch("/api/public/filters");
  const f=await r.json();
  const map={district:"districts",crop:"crops",season:"seasons",scenario:"scenarios"};
  for(const id of ids){
    const el=document.getElementById(id);
    for(const value of f[map[id]]){
      const o=document.createElement("option");
      o.value=value;o.textContent=value;el.appendChild(o);
    }
  }
}

function renderCards(rows){
  const wrap=document.getElementById("result-cards");
  wrap.innerHTML="";
  if(!rows.length)return;
  const yields=rows.map(x=>Number(x.yield_predicted_t_ha)).filter(Number.isFinite);
  const nRates=rows.map(x=>Number(x.n_rate_kg_ha)).filter(Number.isFinite);
  const reductions=rows.map(x=>Number(x.n_reduction_kg_ha)).filter(Number.isFinite);
  const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;
  const cards=[
    ["Mean predicted yield",number(mean(yields)),"t/ha"],
    ["Mean mineral N rate",number(mean(nRates),0),"kg N/ha"],
    ["Mean potential N reduction",number(mean(reductions),0),"kg N/ha"],
    ["Scenarios shown",new Set(rows.map(x=>x.scenario)).size,"management alternatives"]
  ];
  for(const [label,value,unit] of cards){
    const a=document.createElement("article");
    a.innerHTML=`<small>${label}</small><strong>${value}</strong><span>${unit}</span>`;
    wrap.appendChild(a);
  }
}

async function runAdvisory(){
  const q=new URLSearchParams();
  for(const id of ids){const v=document.getElementById(id).value;if(v)q.set(id,v)}
  const r=await fetch("/api/public/advisory?"+q);
  const p=await r.json();
  document.getElementById("summary").innerHTML=`<strong>${p.count}</strong> approved result${p.count===1?"":"s"} match the current selection.`;
  renderCards(p.results);
  const tb=document.querySelector("#results tbody");
  tb.innerHTML="";
  for(const x of p.results){
    const tr=document.createElement("tr");
    const interval=(x.prediction_lower_t_ha!==""&&x.prediction_upper_t_ha!=="")?`${number(x.prediction_lower_t_ha)}–${number(x.prediction_upper_t_ha)}`:"—";
    const vals=[x.district,x.municipality,x.crop,x.scenario,number(x.yield_predicted_t_ha),number(x.n_rate_kg_ha,0),number(x.ae_n_kg_grain_per_kg_n),number(x.pfp_n_kg_grain_per_kg_n),number(x.n_reduction_kg_ha,0),interval,x.published_version];
    for(const v of vals){const td=document.createElement("td");td.textContent=cell(v);tr.appendChild(td)}
    tb.appendChild(tr);
  }
}

document.getElementById("run").addEventListener("click",runAdvisory);
Promise.all([loadSummary(),loadFilters()]).then(runAdvisory).catch(err=>{
  document.getElementById("summary").textContent="Published results could not be loaded.";
  console.error(err);
});