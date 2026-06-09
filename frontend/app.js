'use strict';
const API = 'http://localhost:8000/api/v1';
const PALETTE = ['#3b82f6','#8b5cf6','#10b981','#f59e0b','#ef4444','#06b6d4','#ec4899','#84cc16'];
let charts = {};
let tableState = {page:1,pageSize:50,sort:'',dir:'asc'};
let filterTimeout;

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', ()=>{
  lucide.createIcons();
  checkHealth();
  setInterval(checkHealth, 30000);
  loadOverview();
  loadFilterOptions();
  loadTable();
  loadColumnAnalytics();
  loadScatter();
  loadChurnAnalysis();
  document.getElementById('filter-search').addEventListener('input', ()=>{
    clearTimeout(filterTimeout);
    filterTimeout = setTimeout(loadTable, 400);
  });
});

// ── Health ────────────────────────────────────────────────────────────────────
async function checkHealth(){
  try {
    await fetch(`${API.replace('/v1','')}/health`);
    setStatus(true);
  } catch { setStatus(false); }
}
function setStatus(ok){
  const dot = document.getElementById('status-dot');
  const txt = document.getElementById('status-text');
  const mob = document.getElementById('mobile-status-dot');
  dot.className = 'status-dot ' + (ok?'online':'offline');
  if(mob) mob.className = 'mobile-status ' + (ok?'online':'');
  txt.textContent = ok ? 'Server Online' : 'Offline';
}

// ── Navigation ────────────────────────────────────────────────────────────────
function navigate(page){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('page-'+page).classList.add('active');
  document.getElementById('nav-'+page).classList.add('active');
  if(page==='analytics'){loadColumnAnalytics();loadScatter();}
  if(page==='churn'){loadChurnAnalysis();}
  document.getElementById('sidebar').classList.remove('open');
}
function toggleSidebar(){ document.getElementById('sidebar').classList.toggle('open'); }

// ── Overview ──────────────────────────────────────────────────────────────────
async function loadOverview(){
  try {
    const d = await get('/overview');
    setText('kpi-total-val', d.total_customers.toLocaleString());
    setText('kpi-churn-val', d.churned_customers.toLocaleString());
    setText('kpi-churn-pct', d.churn_rate_pct+'%');
    setText('kpi-credit-val', '$'+fmt(d.avg_credit_limit));
    setText('kpi-util-val', d.avg_utilization_pct+'%');
    setText('kpi-age-val', d.avg_age+' yrs');
    setText('kpi-trans-val', '$'+fmt(d.avg_transaction_amt));
    document.querySelectorAll('.kpi-card').forEach(c=>c.classList.remove('skeleton'));
    loadAllCharts();
  } catch(e){ toast('Failed to load overview','error'); }
}

async function loadAllCharts(){
  try {
    await Promise.all([
      makeDistChart('chart-type-split','Type','doughnut'),
      makeDistChart('chart-gender','gender','bar'),
      makeDistChart('chart-income','Income_Category','bar',true),
      makeDistChart('chart-geo','geography','bar'),
      makeDistChart('chart-card-cat','Card_Category','doughnut'),
    ]);
  } catch{}
}

async function makeDistChart(canvasId, col, type, horizontal=false){
  const data = await get('/analytics/distribution?column='+col);
  const labels = data.map(d=>d.label);
  const vals   = data.map(d=>d.count);
  const colors = labels.map((_,i)=>PALETTE[i%PALETTE.length]);
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId).getContext('2d');
  const cfg = {
    type: type==='bar'?'bar':'doughnut',
    data:{labels, datasets:[{data:vals, backgroundColor:colors, borderWidth:0,
      ...(type==='bar'?{borderRadius:6}:{})}]},
    options:{
      responsive:true, maintainAspectRatio:false,
      indexAxis: horizontal?'y':'x',
      plugins:{legend:{display:type!=='bar',labels:{color:'#94a3b8',font:{size:12}}},
        tooltip:{callbacks:{label:c=>` ${c.formattedValue} (${data[c.dataIndex].pct}%)`}}},
      scales: type==='bar'?{
        x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b',maxRotation:30,font:{size:11}}},
        y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b',font:{size:11}}}
      }:{},
    }
  };
  if(type!=='bar') cfg.options.cutout='65%';
  charts[canvasId] = new Chart(ctx,cfg);
}

// ── Analytics ─────────────────────────────────────────────────────────────────
async function loadColumnAnalytics(){
  const col = document.getElementById('analytic-col').value;
  document.getElementById('hist-title').textContent = col.replace(/_/g,' ')+' Distribution';
  try {
    const d = await get('/analytics/numeric-stats?column='+col);
    setText('stat-mean',   fmtN(d.mean));
    setText('stat-median', fmtN(d.median));
    setText('stat-std',    fmtN(d.std));
    setText('stat-min',    fmtN(d.min));
    setText('stat-q25',    fmtN(d.q25));
    setText('stat-q75',    fmtN(d.q75));
    setText('stat-max',    fmtN(d.max));
    document.querySelectorAll('.skeleton-row').forEach(r=>r.classList.remove('skeleton-row'));
    // Histogram
    const counts = d.histogram.counts;
    const edges  = d.histogram.edges;
    const hlabels = edges.slice(0,-1).map((e,i)=>fmtN((e+edges[i+1])/2));
    destroyChart('chart-histogram');
    const ctx = document.getElementById('chart-histogram').getContext('2d');
    charts['chart-histogram'] = new Chart(ctx,{
      type:'bar',
      data:{labels:hlabels, datasets:[{data:counts, backgroundColor:'rgba(59,130,246,.6)', borderWidth:0, borderRadius:3}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b',maxTicksLimit:10,font:{size:10}}},
                y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b',font:{size:11}}}}}
    });
  } catch(e){ toast('Failed to load analytics','error'); }
}

async function loadScatter(){
  const x = document.getElementById('scatter-x').value;
  const y = document.getElementById('scatter-y').value;
  try {
    const pts = await get(`/analytics/scatter?x=${x}&y=${y}&color_by=Type&sample=500`);
    const ex = pts.filter(p=>p.Type==='Existing Customer');
    const ch = pts.filter(p=>p.Type==='Attrited Customer');
    const mkDataset = (arr, label, color)=>({label, data:arr.map(p=>({x:p[x],y:p[y]})),
      backgroundColor:color, pointRadius:3, pointHoverRadius:5});
    destroyChart('chart-scatter');
    const ctx = document.getElementById('chart-scatter').getContext('2d');
    charts['chart-scatter'] = new Chart(ctx,{
      type:'scatter',
      data:{datasets:[mkDataset(ex,'Existing','rgba(16,185,129,.5)'), mkDataset(ch,'Attrited','rgba(239,68,68,.5)')]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:'#94a3b8'}}},
        scales:{x:{title:{display:true,text:x.replace(/_/g,' '),color:'#64748b'},grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b'}},
                y:{title:{display:true,text:y.replace(/_/g,' '),color:'#64748b'},grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b'}}}}
    });
  } catch{}
}

// ── Table ─────────────────────────────────────────────────────────────────────
async function loadTable(){
  const p = tableState;
  const params = new URLSearchParams({
    page: p.page, page_size: p.pageSize,
    search: v('filter-search'), gender: v('filter-gender'),
    card_category: v('filter-card'), income_category: v('filter-income'),
    geography: v('filter-geo'), customer_type: v('filter-type'),
    ...(p.sort?{sort_by:p.sort, sort_dir:p.dir}:{})
  });
  // Remove empty
  [...params.keys()].forEach(k=>{ if(!params.get(k)) params.delete(k); });
  try {
    const d = await get('/records?'+params);
    renderTable(d);
  } catch{ toast('Failed to load table','error'); }
}

function renderTable(d){
  document.getElementById('table-info').textContent =
    `Showing ${((d.page-1)*d.page_size)+1}–${Math.min(d.page*d.page_size,d.total)} of ${d.total.toLocaleString()} records`;
  // Head
  const cols = d.records.length ? Object.keys(d.records[0]) : [];
  const head = document.getElementById('table-head');
  head.innerHTML = '<tr>'+cols.map(c=>`<th onclick="sortBy('${c}')">${c.replace(/_/g,' ')}</th>`).join('')+'<th>Action</th></tr>';
  // Body
  const body = document.getElementById('table-body');
  body.innerHTML = d.records.map((r,i)=>{
    const rowIdx = (d.page-1)*d.page_size + i;
    const cells = cols.map(c=>`<td title="${esc(String(r[c]??''))}">` + renderCell(c, r[c]) + '</td>').join('');
    return `<tr>${cells}<td><button class="delete-btn" onclick="deleteRecord(${rowIdx})">Delete</button></td></tr>`;
  }).join('');
  renderPagination(d);
  lucide.createIcons();
}

function renderCell(col, val){
  if(col==='Type'){
    return val==='Attrited Customer'
      ? `<span class="badge badge-red">Attrited</span>`
      : `<span class="badge badge-green">Existing</span>`;
  }
  if(col==='Card_Category'){
    const m={'Blue':'badge-blue','Silver':'badge-purple','Gold':'badge-amber','Platinum':'badge-green'};
    return `<span class="badge ${m[val]||'badge-blue'}">${esc(String(val??''))}</span>`;
  }
  if(col==='gender') return val==='M'?'♂ Male':'♀ Female';
  if(typeof val==='number') return fmtN(val);
  return esc(String(val??''));
}

function renderPagination(d){
  const ctrl = document.getElementById('pagination-controls');
  const {page, total_pages} = d;
  let html = `<button class="page-btn" onclick="changePage(${page-1})" ${page<=1?'disabled':''}>‹</button>`;
  const start = Math.max(1,page-2), end = Math.min(total_pages,start+4);
  for(let i=start;i<=end;i++){
    html+=`<button class="page-btn${i===page?' active':''}" onclick="changePage(${i})">${i}</button>`;
  }
  html+=`<button class="page-btn" onclick="changePage(${page+1})" ${page>=total_pages?'disabled':''}>›</button>`;
  ctrl.innerHTML = html;
}

function changePage(p){ tableState.page=p; loadTable(); }
function sortBy(col){
  if(tableState.sort===col) tableState.dir=tableState.dir==='asc'?'desc':'asc';
  else { tableState.sort=col; tableState.dir='asc'; }
  tableState.page=1; loadTable();
}
function debouncedLoad(){ clearTimeout(filterTimeout); filterTimeout=setTimeout(()=>{tableState.page=1;loadTable();},400); }
function clearFilters(){
  ['filter-search','filter-gender','filter-type','filter-card','filter-income','filter-geo']
    .forEach(id=>{ const el=document.getElementById(id); if(el) el.value=''; });
  tableState.page=1; loadTable();
}

async function loadFilterOptions(){
  try {
    const d = await get('/filters/options');
    populateSelect('filter-gender', d.gender, 'All Genders');
    populateSelect('filter-card',   d.card_category, 'All Card Categories');
    populateSelect('filter-income', d.income_category, 'All Income');
    populateSelect('filter-geo',    d.geography, 'All Geographies');
    populateSelect('filter-type',   d.customer_type, 'All Types');
  } catch{}
}

// ── Churn ─────────────────────────────────────────────────────────────────────
async function loadChurnAnalysis(){
  const col = document.getElementById('churn-col').value;
  try {
    const data = await get('/analytics/churn-by?column='+col);
    // Bar chart
    destroyChart('chart-churn-rate');
    let ctx = document.getElementById('chart-churn-rate').getContext('2d');
    charts['chart-churn-rate'] = new Chart(ctx,{
      type:'bar',
      data:{labels:data.map(d=>d.label),
        datasets:[{label:'Churn Rate %',data:data.map(d=>d.churn_rate),
          backgroundColor:data.map(d=>d.churn_rate>30?'rgba(239,68,68,.7)':d.churn_rate>20?'rgba(245,158,11,.7)':'rgba(16,185,129,.7)'),
          borderWidth:0,borderRadius:6}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b'}},
                y:{max:100,grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b',callback:v=>v+'%'}}}}
    });
    // Donut
    destroyChart('chart-churn-vol');
    ctx = document.getElementById('chart-churn-vol').getContext('2d');
    charts['chart-churn-vol'] = new Chart(ctx,{
      type:'doughnut',
      data:{labels:data.map(d=>d.label), datasets:[{data:data.map(d=>d.total),
        backgroundColor:PALETTE.slice(0,data.length), borderWidth:0}]},
      options:{responsive:true,maintainAspectRatio:false,cutout:'65%',
        plugins:{legend:{labels:{color:'#94a3b8',font:{size:11}}}}}
    });
    // Table
    document.getElementById('churn-tbody').innerHTML = data.map(d=>{
      const risk = d.churn_rate>30?'high':d.churn_rate>20?'med':'low';
      const color = risk==='high'?'var(--red)':risk==='med'?'var(--amber)':'var(--green)';
      return `<tr>
        <td><strong>${esc(d.label)}</strong></td>
        <td>${d.total.toLocaleString()}</td>
        <td>${d.churned.toLocaleString()}</td>
        <td><span style="color:${color};font-weight:700">${d.churn_rate}%</span></td>
        <td><div class="risk-bar">
          <div class="risk-fill ${risk}" style="width:${d.churn_rate}%;max-width:80px"></div>
          <span style="font-size:11px;color:var(--text2)">${risk.toUpperCase()}</span>
        </div></td>
      </tr>`;
    }).join('');
  } catch{ toast('Failed to load churn data','error'); }
}

// ── CRUD ──────────────────────────────────────────────────────────────────────
function openAddModal(){ document.getElementById('add-modal').classList.remove('hidden'); lucide.createIcons(); }
function closeAddModal(){ document.getElementById('add-modal').classList.add('hidden'); }
function closeModalOnOverlay(e){ if(e.target===e.currentTarget) closeAddModal(); }

async function submitRecord(e){
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  btn.disabled = true; btn.textContent = 'Saving…';
  try {
    const body = {
      clientID: v('f-clientID'), Type: v('f-type'), age: num('f-age'),
      gender: v('f-gender'), Dependent_count: num('f-dep'),
      Educational_Level: v('f-education'), Marital_Status: v('f-marital'),
      Income_Category: v('f-income'), Card_Category: v('f-card'),
      Months_on_book: num('f-months'), Total_Relationship_count: num('f-rel'),
      Month_Inactive_12_month: num('f-inactive'), Contacts_count_12_mon: num('f-contacts'),
      Credit_Limit: num('f-credit'), Total_Revolving_Bal: num('f-rev-bal'),
      Avg_Open_To_Buy: num('f-otb'), Total_Amt_chng_Q4_Q1: num('f-amt-chng'),
      Total_Trans_Amt: num('f-trans-amt'), Total_Trans_Ct: num('f-trans-ct'),
      Total_Ct_Chng_Q4_Q1: num('f-ct-chng'),
      Average_Utilization_Ratio: num('f-util'), geography: v('f-geo'),
    };
    await post('/records', body);
    toast('Record added successfully','success');
    closeAddModal();
    document.getElementById('add-form').reset();
    loadTable(); loadOverview();
  } catch(err){ toast('Failed: '+err.message,'error'); }
  finally { btn.disabled=false; btn.innerHTML='<i data-lucide="save"></i> Save Customer'; lucide.createIcons(); }
}

async function deleteRecord(idx){
  if(!confirm('Delete this record?')) return;
  try {
    await del('/records/'+idx);
    toast('Record deleted','info');
    loadTable(); loadOverview();
  } catch{ toast('Delete failed','error'); }
}

// ── Export ────────────────────────────────────────────────────────────────────
function exportData(fmt){
  window.open(`${API}/export/${fmt}`, '_blank');
  toast('Download started','info');
}

// ── Refresh ───────────────────────────────────────────────────────────────────
function refreshAll(){
  loadOverview(); loadTable();
  toast('Data refreshed','success');
}

// ── HTTP helpers ──────────────────────────────────────────────────────────────
async function get(path){
  const r = await fetch(API+path);
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
async function post(path, body){
  const r = await fetch(API+path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if(!r.ok){ const e=await r.json().catch(()=>({detail:'Unknown'})); throw new Error(e.detail); }
  return r.json();
}
async function del(path){
  const r = await fetch(API+path, {method:'DELETE'});
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function setText(id, val){ const el=document.getElementById(id); if(el) el.textContent=val; }
function v(id){ return document.getElementById(id)?.value.trim()||''; }
function num(id){ return parseFloat(document.getElementById(id)?.value)||0; }
function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmt(n){ return Number(n).toLocaleString(undefined,{maximumFractionDigits:2}); }
function fmtN(n){ return n===null||n===undefined?'—':Number(n).toLocaleString(undefined,{maximumFractionDigits:3}); }
function destroyChart(id){ if(charts[id]){ charts[id].destroy(); delete charts[id]; } }
function populateSelect(id, opts, placeholder){
  const el = document.getElementById(id); if(!el) return;
  el.innerHTML = `<option value="">${placeholder}</option>` + opts.map(o=>`<option>${esc(o)}</option>`).join('');
}
function toast(msg, type='info'){
  const t = document.createElement('div');
  t.className = 'toast '+type;
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(()=>t.remove(), 3500);
}
