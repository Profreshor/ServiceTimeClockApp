const dashboard = document.getElementById('dashboard');
const currentTimeEl = document.getElementById('currentTime');
const lastUpdatedEl = document.getElementById('lastUpdated');
const summaryEl = document.getElementById('summary');
const themeToggle = document.getElementById('themeToggle');
let techs = [];

// -----------------------------------------------------------------------------
// Time helpers
// -----------------------------------------------------------------------------
function formatTime(value) {
  if (!value) return "00:00";

  // If it's already in "HH:MM" format, just return it as-is
  if (typeof value === "string" && value.includes(":")) return value;

  // Otherwise, treat it as minutes (number)
  const hrs = Math.floor(value / 60);
  const mins = value % 60;
  return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}`;
}

function parseTimeToMinutes(hhmm) {
  if (!hhmm || typeof hhmm !== "string" || !hhmm.includes(":")) return 0;
  const [hh, mm] = hhmm.split(":").map(v => parseInt(v) || 0);
  return hh * 60 + mm;
}

// -----------------------------------------------------------------------------
// Data fetch and preparation
// -----------------------------------------------------------------------------
async function fetchTechData() {
  try {
    const branchParam = new URLSearchParams(window.location.search).get('branch');
    const apiUrl = branchParam ? `/api/timeclock?branch=${branchParam}` : '/api/timeclock';
    const res = await fetch(apiUrl);
    const json = await res.json();

    json.data = (json.data || []).map(t => {
      const safe = {};
      for (const [k, v] of Object.entries(t)) {
        safe[k] = (v === null || Number.isNaN(v) || v === undefined) ? "" : v;
      }
      safe.CurrentIdle = safe.CurrentIdle || "00:00";
      safe.TotalIdle = safe.TotalIdle || "00:00";
      safe.CurrentActive = safe.CurrentActive || safe.TimeElapsed || "00:00";
      return safe;
    });

    techs = json.data.map(t => ({
      name: t.EmpName,
      status: t.OnWorkOrder === 'On RO'
        ? 'Active'
        : t.ClockStatus === 'Clocked-In'
          ? 'Idle'
          : 'Clocked Out',
      currentActive: t.CurrentActive, // formatted HH:MM
      currentIdle: parseTimeToMinutes(t.CurrentIdle),
      totalIdle: parseTimeToMinutes(t.TotalIdle),
      job: t.CurrentRO || '-',
      segment: t.Job || '',
      customer: t.CurrentCustomer || '-',
      roStartTime: t.ROStartTime || "",   // 👈 added line
      hrs: `${(Number(t.HrsActual) || 0).toFixed(1)} / ${(Number(t.HrsBill) || 0).toFixed(1)}`
    }));  

    render();
    updateLastUpdated();
  } catch (err) {
    console.error('Error fetching API data:', err);
  }
}

// -----------------------------------------------------------------------------
// Layout and card rendering
// -----------------------------------------------------------------------------
function adjustFontScaling() {
  const totalTechs = techs.length;
  let baseSize;
  if (totalTechs <= 6) baseSize = 18;
  else if (totalTechs <= 10) baseSize = 17;
  else if (totalTechs <= 15) baseSize = 16;
  else if (totalTechs <= 20) baseSize = 15;
  else baseSize = 14;
  document.documentElement.style.fontSize = baseSize + 'px';
}

function createCard(t) {
  const card = document.createElement('div');
  card.className = `card ${t.status.toLowerCase()}`;

  // Handle Clocked Out cards (no icon, simple layout)
  if (t.status === 'Clocked Out') {
    card.innerHTML = `
      <div class="tech-name">${t.name}</div>
      <div class="status">${t.status}</div>`;
    return card;
  }

  // Choose icon based on status
  const statusIcon =
    t.status === 'Active'
      ? "<span class='status-icon active-icon'>✅</span>"
      : t.status === 'Idle'
        ? "<span class='status-icon idle-icon'>⚠️</span>"
        : "";

  // Build the timing section
  const currentLine = t.status === 'Active'
    ? `
      <div>
        <div>
          <span>Current Active: <span style='color:#33ff99;font-weight:700;'>${t.currentActive || "00:00"}</span></span>
        </div>
        <div class="ro-start">Started at ${t.roStartTime || ""}</div>
      </div>
    `
    : `
      <div>
        <span>Current Idle: <span style='color:#ff4d4d;font-weight:700;'>${formatTime(t.currentIdle)}</span></span>
      </div>
    `;

  const totalLine = `<span>Today's Idle: <span style='color:#ff4d4d;font-weight:700;'>${formatTime(t.totalIdle)}</span></span>`;

  // Build full card HTML
  card.innerHTML = `
    <div class="tech-name">${t.name}</div>
    <div class="status">${statusIcon}${t.status}</div>
    <div class="timing">${currentLine}${totalLine}</div>
    <div class="details"><strong>${t.job}</strong> | Job ${t.segment} | ${t.customer}</div>
    <div class="details">Hrs (Actual/Bill): ${t.hrs}</div>`;

  return card;
}


// -----------------------------------------------------------------------------
// Render + dashboard summary
// -----------------------------------------------------------------------------
function render() {
  dashboard.innerHTML = '';
  adjustFontScaling();

  let counts = { active: 0, idle: 0, clockedout: 0 };
  let totalIdleMinutes = 0;

  const idleActive = techs.filter(t => t.status !== 'Clocked Out');
  const clockedOut = techs.filter(t => t.status === 'Clocked Out').sort((a,b)=>a.name.localeCompare(b.name));

  idleActive.sort((a,b)=>{
    const order={Idle:1,Active:2};
    const diff=order[a.status]-order[b.status];
    return diff!==0?diff:a.name.localeCompare(b.name);
  });

  idleActive.forEach(t=>{
    const card=createCard(t);
    dashboard.appendChild(card);
    if(t.status==='Idle') counts.idle++; else counts.active++;
    totalIdleMinutes+=t.totalIdle;
  });

  for(let i=0;i<clockedOut.length;i+=2){
    const container=document.createElement('div');
    container.className='clockedout-container';
    const sub1=document.createElement('div');
    sub1.className='sub-card';
    sub1.innerHTML=`<div class="tech-name">${clockedOut[i].name}</div><div class="status">${clockedOut[i].status}</div>`;
    container.appendChild(sub1);
    if(clockedOut[i+1]){
      const sub2=document.createElement('div');
      sub2.className='sub-card';
      sub2.innerHTML=`<div class="tech-name">${clockedOut[i+1].name}</div><div class="status">${clockedOut[i+1].status}</div>`;
      container.appendChild(sub2);
    }
    dashboard.appendChild(container);
    counts.clockedout+=(clockedOut[i+1]?2:1);
  }

  const totalHrs=Math.floor(totalIdleMinutes/60);
  const totalMins=totalIdleMinutes%60;
  summaryEl.innerHTML=`Active: ${counts.active} | Idle: ${counts.idle} | Clocked Out: ${counts.clockedout} | <span class='total-idle-footer'>Today's Idle Time: ${totalHrs}h ${totalMins}m</span>`;
}

// -----------------------------------------------------------------------------
// Timers and updates
// -----------------------------------------------------------------------------
function tickIdleTimes(){
  techs.forEach(t=>{
    if(t.status==='Idle'){
      t.currentIdle+=1;
      t.totalIdle+=1;
    }
  });
  render();
  updateLastUpdated();
}

function updateClock(){currentTimeEl.textContent=new Date().toLocaleTimeString();}
let lastUpdateSeconds=0;
function updateLastUpdated(){lastUpdateSeconds=0;lastUpdatedEl.textContent='Last updated: just now';}
function incrementLastUpdated(){lastUpdateSeconds++;lastUpdatedEl.textContent=`Last updated: ${lastUpdateSeconds}s ago`;}

// -----------------------------------------------------------------------------
// Theme handling
// -----------------------------------------------------------------------------
themeToggle.addEventListener('click',()=>{
  const current=document.body.getAttribute('data-theme');
  const next=current==='light'?'dark':'light';
  document.body.setAttribute('data-theme',next);
  localStorage.setItem('theme',next);
  themeToggle.textContent=next==='light'?'☀️':'🌙';
});

function initTheme(){
  const saved=localStorage.getItem('theme')||'dark';
  document.body.setAttribute('data-theme',saved);
  themeToggle.textContent=saved==='light'?'☀️':'🌙';
}

// -----------------------------------------------------------------------------
// Init
// -----------------------------------------------------------------------------
fetchTechData();
initTheme();
setInterval(updateClock,1000);
setInterval(tickIdleTimes,60000);
setInterval(incrementLastUpdated,1000);
setInterval(fetchTechData,60000);
