/* Findly — interactive frontend prototype. Data is stored locally in this browser only. */
const STORAGE = { items: 'findly_items_v1', notifications: 'findly_notifications_v1', claims: 'findly_claims_v1', saved: 'findly_saved_v1', users: 'findly_users_v1', session: 'findly_session_v1' };
const seedUsers = [
  {id:'U-1',name:'Pako Daniel',email:'pako@example.com',password:'findly123',campus:'Main Campus',createdAt:'2026-09-01T10:00:00'}
];
const seedItems = [
  {id:'LF-1048',type:'found',title:'Black laptop sleeve',category:'Electronics',colour:'Black',brand:'Lenovo',location:'Library, Main Campus',date:'2026-10-10',description:'A black padded laptop sleeve with a small grey logo near the zip.',emoji:'💻',visual:'laptop',owner:'Mpho K.',createdAt:'2026-10-10T10:40:00',status:'Open'},
  {id:'LF-1042',type:'lost',title:'Laptop carrying case',category:'Electronics',colour:'Black',brand:'Lenovo',location:'Library, Main Campus',date:'2026-10-09',description:'Black computer bag for a Lenovo laptop. Small grey mark by the zipper.',emoji:'💼',visual:'bag',owner:'Pako Daniel',createdAt:'2026-10-09T12:20:00',status:'Open'},
  {id:'LF-1046',type:'found',title:'Set of silver keys',category:'Accessories',colour:'Silver',brand:'',location:'Student Centre',date:'2026-10-10',description:'Three silver keys on a small round blue key ring.',emoji:'🔑',visual:'keys',owner:'Kabelo T.',createdAt:'2026-10-10T09:15:00',status:'Open'},
  {id:'LF-1038',type:'lost',title:'My key set',category:'Accessories',colour:'Silver',brand:'',location:'Student Centre',date:'2026-10-08',description:'Lost three keys together with a blue circular key ring.',emoji:'🗝️',visual:'keys',owner:'Amantle R.',createdAt:'2026-10-08T11:00:00',status:'Open'},
  {id:'LF-1040',type:'found',title:'Mint water bottle',category:'Drinkware',colour:'Mint green',brand:'Hydro Flask',location:'North Lecture Block',date:'2026-10-09',description:'Mint green insulated bottle with a silver lid.',emoji:'🧴',visual:'bottle',owner:'Neo M.',createdAt:'2026-10-09T14:05:00',status:'Open'},
  {id:'LF-1036',type:'lost',title:'Wireless headphones',category:'Electronics',colour:'Black',brand:'Sony',location:'Cafeteria',date:'2026-10-08',description:'Black over-ear Sony headphones in a soft case.',emoji:'🎧',visual:'headphones',owner:'Thato B.',createdAt:'2026-10-08T15:25:00',status:'Open'},
  {id:'LF-1034',type:'found',title:'Black headphones',category:'Electronics',colour:'Black',brand:'Sony',location:'Cafeteria',date:'2026-10-09',description:'Black Sony over-ear headphones found beside the cafeteria tables.',emoji:'🎧',visual:'headphones',owner:'Boitumelo P.',createdAt:'2026-10-09T16:10:00',status:'Open'},
  {id:'LF-1032',type:'found',title:'Blue phone',category:'Electronics',colour:'Blue',brand:'Samsung',location:'Computer Lab 2',date:'2026-10-07',description:'Blue Samsung phone in a clear protective case.',emoji:'📱',visual:'phone',owner:'Oratile S.',createdAt:'2026-10-07T13:35:00',status:'Open'},
  {id:'LF-1029',type:'lost',title:'Brown card wallet',category:'Personal items',colour:'Brown',brand:'',location:'Parking area',date:'2026-10-06',description:'Small brown wallet with a few cards inside.',emoji:'👛',visual:'wallet',owner:'Lesego D.',createdAt:'2026-10-06T10:00:00',status:'Open'},
  {id:'LF-1028',type:'found',title:'Student ID holder',category:'Personal items',colour:'Purple',brand:'',location:'Main Campus Reception',date:'2026-10-06',description:'Purple plastic ID holder with a lanyard.',emoji:'🪪',visual:'id',owner:'Karabo N.',createdAt:'2026-10-06T08:35:00',status:'Open'},
  {id:'LF-1025',type:'found',title:'Wireless earbuds case',category:'Electronics',colour:'White',brand:'Apple',location:'Lecture Theatre A',date:'2026-10-05',description:'White earbuds charging case, no earbuds visible.',emoji:'🎧',visual:'headphones',owner:'Tshepo G.',createdAt:'2026-10-05T12:00:00',status:'Open'},
  {id:'LF-1022',type:'lost',title:'Blue USB drive',category:'Electronics',colour:'Blue',brand:'SanDisk',location:'Computer Lab 1',date:'2026-10-04',description:'Small blue USB flash drive with coursework files.',emoji:'💾',visual:'phone',owner:'Kea M.',createdAt:'2026-10-04T09:00:00',status:'Open'}
];
const seedNotifications = [
  {id:'N-1',type:'match',title:'A strong match was found',body:'A found report may match your “Laptop carrying case” report.',time:'2026-10-10T11:10:00',read:false,itemId:'LF-1042'},
  {id:'N-2',type:'community',title:'New item near the library',body:'A black laptop sleeve was reported at the Library, Main Campus.',time:'2026-10-10T10:42:00',read:false,itemId:'LF-1048'},
  {id:'N-3',type:'tip',title:'Keep claims safe',body:'Always verify a distinctive detail privately before arranging a handover.',time:'2026-10-09T08:30:00',read:true}
];
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const safeParse = (raw, fallback) => { try { const val=JSON.parse(raw); return Array.isArray(val)?val:fallback; } catch { return fallback; } };
const readStore = (key, fallback) => { const raw=localStorage.getItem(key); return raw===null?fallback:safeParse(raw,fallback); };
const readObject = (key, fallback) => { try { const raw=localStorage.getItem(key); if(raw===null)return fallback; const val=JSON.parse(raw); return val&&typeof val==='object'&&!Array.isArray(val)?val:fallback; } catch { return fallback; } };
let items = readStore(STORAGE.items, seedItems);
let notifications = readStore(STORAGE.notifications, seedNotifications);
let claims = readStore(STORAGE.claims, []);
let saved = readStore(STORAGE.saved, []);
let users = (()=>{ const stored=readStore(STORAGE.users, null); if(stored===null){ localStorage.setItem(STORAGE.users,JSON.stringify(seedUsers)); return [...seedUsers]; } return stored.length?stored:[...seedUsers]; })();
let currentUser = null;
let currentView = 'explore';
let exploreFilter = 'all';
let searchQuery = '';
let selectedCategory = 'all';
let modalFocusReturn = null;
let currentPhotoData = '';
let authMode = 'login';

const categoryEmoji = {Electronics:'💻',Accessories:'🔑',Drinkware:'🧴','Personal items':'👛',Clothing:'🧥',Books:'📚',Other:'📦'};
const titleMap = {explore:'Explore items','my-reports':'My reports',matches:'Smart matches',notifications:'Notifications',claims:'Claim requests',profile:'Settings'};
const fmtDate = (date) => { if(!date)return 'Date not provided'; const d=new Date(date+'T12:00:00'); if(Number.isNaN(d.getTime()))return date; return d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}); };
const timeAgo = (date) => { const mins=Math.max(0,Math.floor((Date.now()-new Date(date).getTime())/60000)); if(!Number.isFinite(mins))return 'Recently'; if(mins<1)return 'Just now'; if(mins<60)return `${mins} min ago`; const hrs=Math.floor(mins/60); if(hrs<24)return `${hrs} hr${hrs===1?'':'s'} ago`; const days=Math.floor(hrs/24); if(days<7)return `${days} day${days===1?'':'s'} ago`; return fmtDate(date.slice(0,10)); };
const esc = (s='') => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const visualClass = (item) => `visual-${item.visual||'bag'}`;
const itemEmoji = (item) => item.emoji || categoryEmoji[item.category] || '📦';
const itemById = id => items.find(i=>i.id===id);
const saveAll = () => { localStorage.setItem(STORAGE.items,JSON.stringify(items)); localStorage.setItem(STORAGE.notifications,JSON.stringify(notifications)); localStorage.setItem(STORAGE.claims,JSON.stringify(claims)); localStorage.setItem(STORAGE.saved,JSON.stringify(saved)); };
const saveUsers = () => localStorage.setItem(STORAGE.users,JSON.stringify(users));
const userName = () => currentUser?.name || 'Guest';
const userInitials = (name=userName()) => { const parts=String(name).trim().split(/\s+/).filter(Boolean); if(!parts.length)return '??'; if(parts.length===1)return parts[0].slice(0,2).toUpperCase(); return (parts[0][0]+parts[parts.length-1][0]).toUpperCase(); };
const normalizeEmail = (email='') => String(email).trim().toLowerCase();

function setAuthError(id, message='') { const el=$(id); if(!el)return; if(!message){el.hidden=true;el.textContent='';return;} el.hidden=false; el.textContent=message; }
function showAuthTab(mode='login') {
  authMode=mode==='signup'?'signup':'login';
  $$('.auth-tab').forEach(tab=>{ const on=tab.dataset.authTab===authMode; tab.classList.toggle('active',on); tab.setAttribute('aria-selected',on?'true':'false'); });
  const loginPane=$('#loginPane'), signupPane=$('#signupPane');
  if(loginPane){ loginPane.hidden=authMode!=='login'; loginPane.classList.toggle('active',authMode==='login'); }
  if(signupPane){ signupPane.hidden=authMode!=='signup'; signupPane.classList.toggle('active',authMode==='signup'); }
  setAuthError('#loginError'); setAuthError('#signupError');
  const focusId=authMode==='signup'?'#signupName':'#loginEmail';
  setTimeout(()=>$(focusId)?.focus(),40);
}
function updateAccountChrome() {
  if(!currentUser)return;
  const initials=userInitials();
  const avatar=$('#sidebarAvatar'), top=$('#topAvatar'), nameEl=$('#sidebarName'), roleEl=$('#sidebarRole');
  if(avatar)avatar.textContent=initials;
  if(top)top.textContent=initials;
  if(nameEl)nameEl.textContent=currentUser.name;
  if(roleEl)roleEl.textContent=currentUser.campus?`${currentUser.campus}`:'Campus member';
}
function enterApp(user,{welcome=false}={}) {
  currentUser={id:user.id,name:user.name,email:user.email,campus:user.campus||'Main Campus'};
  localStorage.setItem(STORAGE.session,JSON.stringify({userId:user.id}));
  $('#authShell').hidden=true;
  $('#appShell').hidden=false;
  updateAccountChrome();
  currentView='explore';
  render();
  if(welcome)toast('Welcome',`Signed in as ${currentUser.name}.`);
}
function showAuthScreen(mode='login') {
  currentUser=null;
  localStorage.removeItem(STORAGE.session);
  $('#appShell').hidden=true;
  $('#authShell').hidden=false;
  closeModal();
  showAuthTab(mode);
}
function restoreSession() {
  const session=readObject(STORAGE.session,null);
  if(!session?.userId)return false;
  const user=users.find(u=>u.id===session.userId);
  if(!user){ localStorage.removeItem(STORAGE.session); return false; }
  enterApp(user);
  return true;
}
function handleLoginSubmit(form) {
  const fd=new FormData(form);
  const email=normalizeEmail(fd.get('email'));
  const password=String(fd.get('password')||'');
  if(!email||!password){ setAuthError('#loginError','Enter your email and password.'); return; }
  const user=users.find(u=>normalizeEmail(u.email)===email);
  if(!user||user.password!==password){ setAuthError('#loginError','Those details do not match an account in this demo.'); return; }
  setAuthError('#loginError');
  enterApp(user,{welcome:true});
}
function handleSignupSubmit(form) {
  const fd=new FormData(form);
  const name=String(fd.get('name')||'').trim();
  const email=normalizeEmail(fd.get('email'));
  const campus=String(fd.get('campus')||'').trim()||'Main Campus';
  const password=String(fd.get('password')||'');
  const confirm=String(fd.get('confirm')||'');
  if(!name||!email||!password){ setAuthError('#signupError','Please complete the required fields.'); return; }
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){ setAuthError('#signupError','Enter a valid email address.'); return; }
  if(password.length<6){ setAuthError('#signupError','Use a password with at least 6 characters.'); return; }
  if(password!==confirm){ setAuthError('#signupError','Passwords do not match.'); return; }
  if(users.some(u=>normalizeEmail(u.email)===email)){ setAuthError('#signupError','An account with that email already exists. Try logging in.'); return; }
  const user={id:`U-${Date.now()}`,name,email,password,campus,createdAt:new Date().toISOString()};
  users.push(user); saveUsers();
  setAuthError('#signupError');
  enterApp(user);
  toast('Account created',`Welcome to Findly, ${user.name}.`);
}

function descriptionTokens(txt='') { return new Set(txt.toLowerCase().replace(/[^a-z0-9\s]/g,' ').split(/\s+/).filter(w=>w.length>2)); }
function jaccard(a,b) { const A=descriptionTokens(a),B=descriptionTokens(b); if(!A.size||!B.size)return 0; let common=0; A.forEach(w=>{if(B.has(w))common++;}); return common/(A.size+B.size-common); }
function nearText(a,b) { a=(a||'').toLowerCase().trim(); b=(b||'').toLowerCase().trim(); if(!a||!b)return 0; if(a===b)return 1; if(a.includes(b)||b.includes(a))return .8; return jaccard(a,b); }
function matchScore(a,b) {
  if(!a||!b||a.type===b.type||a.status==='Returned'||b.status==='Returned')return 0;
  let score=0;
  score += (a.category&&b.category&&a.category===b.category)?20:0;
  score += (a.colour&&b.colour)? nearText(a.colour,b.colour)*14:0;
  score += (a.brand&&b.brand)? nearText(a.brand,b.brand)*14:0;
  score += (a.location&&b.location)? nearText(a.location,b.location)*17:0;
  score += jaccard(`${a.title} ${a.description}`,`${b.title} ${b.description}`)*25;
  if(a.date&&b.date){const gap=Math.abs(new Date(a.date)-new Date(b.date))/86400000;score += Math.max(0,10-gap*2.5);}
  return Math.round(Math.min(99,score));
}
function getMatches() {
  const lost=items.filter(i=>i.type==='lost'&&i.status!=='Returned');
  const found=items.filter(i=>i.type==='found'&&i.status!=='Returned');
  const matches=[];
  lost.forEach(l=>found.forEach(f=>{const score=matchScore(l,f); if(score>=28)matches.push({lost:l,found:f,score,id:`${l.id}_${f.id}`});}));
  return matches.sort((a,b)=>b.score-a.score);
}
function addNotification(data) { notifications.unshift({id:`N-${Date.now()}`,time:new Date().toISOString(),read:false,...data}); notifications=notifications.slice(0,60); saveAll(); }
function toast(title, message='') { const el=document.createElement('div'); el.className='toast'; el.innerHTML=`<span class="check">✓</span><span><strong>${esc(title)}</strong>${esc(message)}</span>`; $('#toastStack').appendChild(el); setTimeout(()=>{el.style.opacity='0';el.style.transform='translateX(10px)';setTimeout(()=>el.remove(),250);},3400); }
function itemVisual(item, card=false) { return `<div class="${card?'item-card-visual':'item-visual'} ${visualClass(item)}" ${item.imageData?`style="background-image:url('${item.imageData}');background-size:cover;background-position:center"`:''}>${item.imageData?'':`<span class="${card?'emoji':''}">${esc(itemEmoji(item))}</span>`}</div>`; }
function statCard(icon,kind,kicker,value,foot) { return `<article class="stat-card"><div class="stat-top"><span class="stat-icon ${kind}">${icon}</span><span class="stat-kicker">${kicker}</span></div><div class="stat-value">${value}</div><div class="stat-foot">${foot}</div></article>`; }
function pageHeading(eyebrow,title,description,button='') { return `<div class="page-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p>${description}</p></div>${button}</div>`; }
function itemCard(item) {
  const isSaved=saved.includes(item.id);
  return `<article class="item-card"><div class="item-card-media-wrap" style="position:relative">${itemVisual(item,true)}<span class="item-status ${item.type}">${item.type==='found'?'FOUND':'LOST'}</span><button class="item-bookmark ${isSaved?'saved':''}" data-action="save" data-id="${esc(item.id)}" aria-label="${isSaved?'Remove saved item':'Save item'}">${isSaved?'♥':'♡'}</button></div><div class="item-card-body"><div class="item-card-title"><h3>${esc(item.title)}</h3><span class="item-id">${esc(item.id)}</span></div><p>${esc(item.description)}</p><div class="item-location"><span>⌖</span>${esc(item.location)} <span>·</span> ${fmtDate(item.date)}</div><div class="item-card-foot"><span>Reported by ${esc(item.owner||'Community')}</span><button data-action="details" data-id="${esc(item.id)}">View details ↗</button></div></div></article>`;
}
function exploreView() {
  const filtered=items.filter(i=>{
    const text=`${i.title} ${i.description} ${i.location} ${i.brand} ${i.category} ${i.colour}`.toLowerCase();
    return (exploreFilter==='all'||i.type===exploreFilter) && (selectedCategory==='all'||i.category===selectedCategory) && (!searchQuery||text.includes(searchQuery.toLowerCase()));
  }).sort((a,b)=>new Date(b.createdAt)-new Date(a.createdAt));
  return `${pageHeading('CAMPUS DIRECTORY','Explore items','A little searching can go a long way. Browse reports from your community.',`<button class="btn btn-primary" data-action="report" data-type="lost">＋ Report an item</button>`)}
  <div class="filter-bar"><label class="filter-search"><span>⌕</span><input id="exploreSearch" value="${esc(searchQuery)}" placeholder="Try “black laptop”, “library”..." aria-label="Search item reports"></label><select id="categoryFilter" aria-label="Filter by category"><option value="all">All categories</option>${['Electronics','Accessories','Drinkware','Personal items','Clothing','Books','Other'].map(c=>`<option value="${c}" ${selectedCategory===c?'selected':''}>${c}</option>`).join('')}</select><div class="segmented" aria-label="Item type filter">${[['all','All items'],['lost','Lost'],['found','Found']].map(([v,l])=>`<button class="segment ${exploreFilter===v?'active':''}" data-action="filter-type" data-type="${v}">${l}</button>`).join('')}</div></div>
  <div class="results-line"><span><strong>${filtered.length} reports</strong> found ${searchQuery?`for “${esc(searchQuery)}”`:''}</span><span>Newest first ↓</span></div><div class="items-grid">${filtered.length?filtered.map(itemCard).join(''):`<div class="empty-state"><div class="empty-icon">⌕</div><h3>No reports found</h3><p>Try another keyword or category. Can't see your item? Add a report so the community can help.</p><button class="btn btn-primary" data-action="report" data-type="lost">Create a report</button></div>`}</div>`;
}
function matchesView() {
 const matches=getMatches().filter(m=>m.score>=25);
 return `${pageHeading('INTELLIGENT MATCHING','Smart matches','Potential lost-and-found pairs, ranked by how closely the details line up.')}<div class="split-banner"><div class="split-copy"><div class="split-spark">✳</div><div><h3>AI-assisted, human-verified</h3><p>Scores are recommendations, not proof of ownership. Always verify privately.</p></div></div><div class="match-score-large">${matches.length}<small>POTENTIAL PAIRS</small></div></div><div class="two-col"><section>${matches.length?matches.map(m=>`<article class="match-detail"><div class="match-detail-top"><strong>Potential pair · ${esc(m.lost.id)} / ${esc(m.found.id)}</strong><span class="status-pill ${m.score>=70?'':'pending'}">${m.score>=70?'Strong match':'Review details'}</span></div><div class="match-detail-pair"><div class="pair-item">${itemVisual(m.lost)}<div><strong>${esc(m.lost.title)}</strong><span>Lost · ${esc(m.lost.location)}</span></div></div><div class="pair-plus">↔</div><div class="pair-item">${itemVisual(m.found)}<div><strong>${esc(m.found.title)}</strong><span>Found · ${esc(m.found.location)}</span></div></div></div><div class="match-bar"><span style="width:${m.score}%;--bar-width:${m.score}%"></span></div><div class="match-detail-top" style="margin:8px 0 0"><span style="font-size:9px;color:#9ea3b7">Similarity score</span><strong style="color:#37a184">${m.score}%</strong></div><div class="match-card-actions"><button class="btn btn-light btn-small" data-action="details" data-id="${esc(m.lost.id)}">View lost report</button><button class="btn btn-primary btn-small" data-action="details" data-id="${esc(m.found.id)}">Review found item ↗</button></div></article>`).join(''):`<div class="empty-state"><div class="empty-icon">✳</div><h3>No potential matches yet</h3><p>As new reports are submitted, the matcher will compare their descriptions, categories, colours, locations and dates.</p></div>`}</section><aside class="side-note"><h3>How matching works</h3><p>Findly compares multiple item details to recommend reports that may refer to the same property.</p><div class="tip-row"><div class="tip-icon">Aa</div><div><strong>Description similarity</strong><span>Similar words and item details help identify related descriptions.</span></div></div><div class="tip-row"><div class="tip-icon">⌖</div><div><strong>Place and date</strong><span>Reports from nearby places and dates can be more relevant.</span></div></div><div class="tip-row"><div class="tip-icon">✓</div><div><strong>People make the decision</strong><span>A match score does not establish ownership. Verify claims before a handover.</span></div></div><div class="form-note" style="margin-top:13px">Demo note: these recommendations use a lightweight local similarity heuristic. Connect the FastAPI service and a semantic model for the full AI implementation.</div></aside></div>`;
}
function myReportsView() {
 const mine=items.filter(i=>i.owner===userName());
 return `${pageHeading('YOUR ACTIVITY','My reports','Keep track of the items you have reported.',`<button class="btn btn-primary" data-action="report" data-type="lost">＋ New report</button>`)}<div class="stats-grid">${statCard('▤','lilac','YOUR REPORTS',mine.length,'Items submitted by you')}${statCard('⌕','mint','LOST ITEMS',mine.filter(i=>i.type==='lost').length,'Reports to help you recover')}${statCard('✓','peach','ACTIVE CLAIMS',claims.filter(c=>c.owner===userName()&&c.status==='Pending').length,'Waiting for review')}${statCard('✳','blue','SAVED ITEMS',saved.length,'Reports bookmarked')}</div><div class="table-wrap"><table class="data-table"><thead><tr><th>Item</th><th>Type</th><th>Reported date</th><th>Status</th><th>Potential match</th><th></th></tr></thead><tbody>${mine.length?mine.map(i=>{const m=getMatches().find(x=>x.lost.id===i.id||x.found.id===i.id);return `<tr><td><div class="table-item">${itemVisual(i)}<div><strong>${esc(i.title)}</strong><small>${esc(i.id)}</small></div></div></td><td>${i.type==='lost'?'Lost item':'Found item'}</td><td>${fmtDate(i.createdAt?.slice(0,10)||i.date)}</td><td><span class="status-pill ${i.status==='Returned'?'closed':''}">${esc(i.status||'Open')}</span></td><td>${m?`<span class="status-pill">${m.score}% match</span>`:'—'}</td><td><button class="table-action" data-action="details" data-id="${esc(i.id)}">Open ↗</button></td></tr>`}).join(''):`<tr><td colspan="6"><div class="empty-message">You haven't created any reports yet. Start with a lost or found item.</div></td></tr>`}</tbody></table></div>`;
}
function notificationsView() {
 const types={match:['✳','purple'],community:['⌕','green'],tip:['✓','orange'],claim:['♧','blue'],report:['▤','purple']};
 return `${pageHeading('STAY IN THE LOOP','Notifications','Important updates about reports, potential matches and claims.',`<button class="btn btn-light" data-action="read-all">✓ Mark all as read</button>`)}<div class="notice-list">${notifications.length?notifications.map(n=>{const [icon,colour]=types[n.type]||['✦','purple'];return `<article class="notice ${n.read?'':'unread'}"><div class="notice-icon ${colour}">${icon}</div><div class="notice-main"><strong>${esc(n.title)}</strong><p>${esc(n.body)}</p><time>${timeAgo(n.time)}</time></div><div class="notice-actions">${n.itemId?`<button data-action="details" data-id="${esc(n.itemId)}">View item</button>`:''}${!n.read?`<button data-action="read-notice" data-id="${esc(n.id)}">Mark read</button>`:''}</div></article>`}).join(''):`<div class="empty-state"><div class="empty-icon">♧</div><h3>All quiet for now</h3><p>New activity will show up here.</p></div>`}</div>`;
}
function claimsView() {
 const statusMap={Pending:'pending',Approved:'',Rejected:'closed',Completed:'closed'};
 return `${pageHeading('SAFE HANDOVERS','Claim requests','Review requests and protect the details that prove ownership.',`<button class="btn btn-primary" data-action="claim-from-list">＋ Start a claim</button>`)}<div class="two-col"><section><div class="table-wrap"><table class="data-table"><thead><tr><th>Item</th><th>Claimant</th><th>Submitted</th><th>Status</th><th></th></tr></thead><tbody>${claims.length?claims.map(c=>{const it=itemById(c.itemId);return `<tr><td><div class="table-item">${it?itemVisual(it):'<div class="item-visual visual-bag">📦</div>'}<div><strong>${esc(it?.title||'Removed item')}</strong><small>${esc(c.id)}</small></div></div></td><td>${esc(c.claimant||'You')}</td><td>${fmtDate(c.createdAt?.slice(0,10))}</td><td><span class="status-pill ${statusMap[c.status]||'pending'}">${esc(c.status)}</span></td><td><button class="table-action" data-action="claim-details" data-id="${esc(c.id)}">Review ↗</button></td></tr>`}).join(''):`<tr><td colspan="5"><div class="empty-message">No claim requests yet. Open an item report to submit a claim.</div></td></tr>`}</tbody></table></div></section><aside class="side-note"><h3>Verification checklist</h3><p>Never rely on a match score alone. Keep distinctive details private until a claim is reviewed.</p><div class="claim-step"><div class="claim-step-icon">1</div><div><strong>Ask for a private detail</strong><p>Request a distinctive feature, mark, contents or other identifying information.</p></div></div><div class="claim-step"><div class="claim-step-icon">2</div><div><strong>Compare against the report</strong><p>Review the submitted claim and any proof available to the responsible person.</p></div></div><div class="claim-step"><div class="claim-step-icon">3</div><div><strong>Agree on a safe handover</strong><p>Human review should decide whether the item can be returned.</p></div></div></aside></div>`;
}
function profileView() {
 const mine=items.filter(i=>i.owner===userName()).length;
 const u=currentUser||{name:'Guest',email:'',campus:'Main Campus'};
 return `${pageHeading('YOUR SPACE','Profile & settings','A few details to keep your Findly experience organised.')}<div class="profile-layout"><aside class="profile-card"><div class="profile-large">${esc(userInitials(u.name))}</div><h3>${esc(u.name)}</h3><p>${esc(u.campus||'Campus member')} · Signed in</p><span class="profile-badge">✦ Community helper</span><div class="profile-metrics"><div><strong>${mine}</strong><span>Reports</span></div><div><strong>${saved.length}</strong><span>Saved</span></div><div><strong>${claims.length}</strong><span>Claims</span></div></div><div class="form-note" style="text-align:left;margin-top:20px">Local demo account. Sign-out clears this browser session only.</div><button class="btn btn-light" style="width:100%;margin-top:14px" data-action="logout">Log out</button></aside><section class="form-panel"><h3>Profile details</h3><form id="profileForm"><div class="field-grid"><div class="field"><label for="profileName">Full name</label><input id="profileName" name="name" value="${esc(u.name)}" required></div><div class="field"><label for="profileEmail">Email address</label><input id="profileEmail" name="email" type="email" value="${esc(u.email)}" required></div><div class="field"><label for="profileCampus">Campus / organisation</label><input id="profileCampus" name="campus" value="${esc(u.campus||'Main Campus')}"></div><div class="field"><label for="profileNotifications">Notification preference</label><select id="profileNotifications" name="notifications"><option>In-app notifications</option><option>Email and in-app</option><option>Important matches only</option></select></div></div><div class="form-actions"><button class="btn btn-primary" type="submit">Save preferences</button></div></form><div style="height:25px"></div><h3>Prototype data</h3><p style="font-size:10px;color:#989db1;line-height:1.7">Reports, saved items, notifications and claims are currently stored in this browser's local storage. They are not shared with other users or a cloud database.</p><button class="btn btn-light" data-action="reset-demo">Reset demo data</button></section></div>`;
}
function render() {
 if(!currentUser)return;
 const viewMap={explore:exploreView,'my-reports':myReportsView,matches:matchesView,notifications:notificationsView,claims:claimsView,profile:profileView};
 $('#breadcrumbTitle').textContent=titleMap[currentView]||'Explore items';
 $$('.nav-link[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===currentView));
 $('#notificationNavCount').textContent=notifications.filter(n=>!n.read).length;
 $('#notificationNavCount').style.display=notifications.some(n=>!n.read)?'':'none';
 $('#itemsNavCount').textContent=items.length;
 $('#pageContent').innerHTML=(viewMap[currentView]||exploreView)();
 $('#globalSearch').value=searchQuery;
}
function navigate(view) {
 if(!titleMap[view])return; currentView=view; $('#sidebar').classList.remove('open'); render(); window.scrollTo({top:0,behavior:'smooth'});
}
function openModal(title,eyebrow,html) {
 modalFocusReturn=document.activeElement; $('#modalTitle').textContent=title; $('#modalEyebrow').textContent=eyebrow; $('#modalBody').innerHTML=html; $('#modalBackdrop').hidden=false; document.body.style.overflow='hidden'; setTimeout(()=>{const f=$('#modalBody input:not([type=hidden]),#modalBody select,#modalBody textarea, #modalBody button');if(f)f.focus();},40);
}
function closeModal(){ $('#modalBackdrop').hidden=true;document.body.style.overflow='';$('#modalBody').innerHTML='';currentPhotoData='';if(modalFocusReturn?.focus)modalFocusReturn.focus(); }
function reportForm(type='lost') {
 const isFound=type==='found'; currentPhotoData='';
 openModal(isFound?'Report a found item':'Report a lost item','LET’S GET IT BACK',`<form id="reportForm" data-type="${type}"><div class="form-note">${isFound?'Found something? Share enough details to help the owner recognise it.':'Describe the item clearly to help the matching system surface relevant found reports.'} <strong>Keep one distinctive detail private</strong> for claim verification.</div><div class="field-grid"><div class="field"><label for="itemTitle">Item name *</label><input id="itemTitle" name="title" placeholder="e.g. Black laptop sleeve" required maxlength="90"></div><div class="field"><label for="itemCategory">Category *</label><select id="itemCategory" name="category" required><option value="">Choose a category</option>${['Electronics','Accessories','Drinkware','Personal items','Clothing','Books','Other'].map(c=>`<option>${c}</option>`).join('')}</select></div><div class="field"><label for="itemColour">Colour *</label><input id="itemColour" name="colour" placeholder="e.g. Black" required maxlength="35"></div><div class="field"><label for="itemBrand">Brand (if known)</label><input id="itemBrand" name="brand" placeholder="e.g. Lenovo" maxlength="45"></div><div class="field"><label for="itemPlace">${isFound?'Where was it found?':'Where was it lost?'} *</label><input id="itemPlace" name="location" placeholder="e.g. Library, Main Campus" required maxlength="100"></div><div class="field"><label for="itemDate">${isFound?'Date found':'Date lost'} *</label><input id="itemDate" name="date" type="date" max="2026-12-31" required value="${new Date().toISOString().slice(0,10)}"></div><div class="field full"><label for="itemDescription">Description *</label><textarea id="itemDescription" name="description" placeholder="Add useful details such as shape, material or visible features. Keep one private identifying detail out of the public description." required maxlength="700"></textarea><small>Do not include passwords, private documents or other sensitive information.</small></div><div class="field full"><label>Item photograph (optional)</label><label class="upload-zone" for="itemImage"><div class="upload-icon">⇧</div><strong id="uploadLabel">Choose a photo or use your camera</strong><span>JPG, PNG or WEBP · Max 3 MB for this demo</span><input id="itemImage" type="file" accept="image/*" capture="environment"><div class="camera-hint" id="imagePreview"></div></label></div></div><div class="form-actions"><button type="button" class="btn btn-light" data-action="close-modal">Cancel</button><button type="submit" class="btn btn-primary">Submit report <span>↗</span></button></div></form>`);
 const dateInput=$('#itemDate');dateInput.max=new Date().toISOString().slice(0,10);
}
function detailsModal(id) {
 const item=itemById(id); if(!item){toast('Item unavailable','This report may have been removed.');return;}
 const matches=getMatches().filter(m=>m.lost.id===id||m.found.id===id);
 const matchText=matches.length?`<div class="form-note"><strong>${matches[0].score}% potential match</strong><br>A similar report exists. This score is only a recommendation and is not proof of ownership.</div>`:'';
 const own=item.owner===userName();
 openModal(item.title.toUpperCase(),'REPORT DETAILS',`<div style="display:flex;gap:15px;align-items:center;margin-bottom:18px">${itemVisual(item)}<div style="min-width:0"><span class="type-label ${item.type==='found'?'found':''}">${item.type==='found'?'FOUND ITEM':'LOST ITEM'}</span><h3 style="font:800 17px Manrope;margin:9px 0 5px">${esc(item.title)}</h3><span style="font-size:10px;color:#9da1b4">${esc(item.id)} · Reported by ${esc(item.owner||'Community')}</span></div></div>${item.imageData?`<img src="${item.imageData}" alt="Uploaded item" style="width:100%;max-height:210px;object-fit:contain;background:#fafaff;border-radius:12px;margin-bottom:15px">`:''}<div class="field-grid"><div class="field"><label>Category</label><div style="font-size:11px;color:#343955">${esc(item.category)}</div></div><div class="field"><label>Colour</label><div style="font-size:11px;color:#343955">${esc(item.colour||'Not supplied')}</div></div><div class="field"><label>Brand</label><div style="font-size:11px;color:#343955">${esc(item.brand||'Not supplied')}</div></div><div class="field"><label>${item.type==='found'?'Date found':'Date lost'}</label><div style="font-size:11px;color:#343955">${fmtDate(item.date)}</div></div><div class="field full"><label>Location</label><div style="font-size:11px;color:#343955">⌖ ${esc(item.location)}</div></div><div class="field full"><label>Description</label><div style="font-size:11px;line-height:1.7;color:#6f7490">${esc(item.description)}</div></div></div>${matchText}<div class="form-actions">${own?`<button class="btn btn-light" data-action="change-status" data-id="${esc(item.id)}">${item.status==='Returned'?'Mark open':'Mark returned'}</button>`:''}${item.type==='found'&&item.status!=='Returned'?`<button class="btn btn-primary" data-action="claim" data-id="${esc(item.id)}">Claim this item ↗</button>`:`<button class="btn btn-primary" data-action="close-modal">Done</button>`}</div>`);
}
function claimForm(itemId) {
 const item=itemById(itemId); if(!item){toast('Choose an item','Open a found item to start a claim.');return;}
 openModal('Claim this item','PRIVATE VERIFICATION',`<form id="claimForm" data-item-id="${esc(item.id)}"><div class="form-note">You're requesting a review for <strong>${esc(item.title)}</strong>. Your answer is for verification and should not be shared publicly. A human review is still needed before an item is returned.</div><div class="field"><label for="claimName">Your full name *</label><input id="claimName" name="claimant" placeholder="Enter your name" value="${esc(userName())}" required maxlength="90"></div><div class="field"><label for="claimEmail">Contact email (optional)</label><input id="claimEmail" name="email" type="email" placeholder="you@example.com" value="${esc(currentUser?.email||'')}"></div><div class="field"><label for="claimEvidence">Private identifying detail *</label><textarea id="claimEvidence" name="evidence" required maxlength="800" placeholder="Describe a distinctive mark, contents, serial detail or another feature that only the owner is likely to know."></textarea><small>Do not include passwords, bank details or unnecessary sensitive information.</small></div><div class="field"><label class="checkbox-line" style="display:flex;align-items:flex-start;gap:9px;font-size:10px;color:#707591"><input name="confirm" type="checkbox" required style="width:auto;margin-top:1px"> I confirm these details are accurate and understand this request does not automatically prove ownership.</label></div><div class="form-actions"><button type="button" class="btn btn-light" data-action="close-modal">Cancel</button><button type="submit" class="btn btn-primary">Submit for review</button></div></form>`);
}
function claimDetails(id) {
 const c=claims.find(x=>x.id===id); if(!c)return; const it=itemById(c.itemId);
 const canReview=c.status==='Pending';
 openModal('Claim review','CLAIM DETAILS',`<div class="form-note">Claim details contain private information. Use them only to review this request and do not display them on a public item page.</div><div class="field-grid"><div class="field"><label>Item</label><div style="font-size:11px">${esc(it?.title||'Removed item')}</div></div><div class="field"><label>Claimant</label><div style="font-size:11px">${esc(c.claimant||'Not supplied')}</div></div><div class="field"><label>Submitted</label><div style="font-size:11px">${fmtDate(c.createdAt?.slice(0,10))}</div></div><div class="field"><label>Status</label><div><span class="status-pill pending">${esc(c.status)}</span></div></div><div class="field full"><label>Private identifying detail</label><div style="background:#fafaff;border-radius:10px;padding:13px;font-size:11px;line-height:1.7">${esc(c.evidence)}</div></div></div><div class="form-note">This is a local prototype. In a real deployment, only authorised reviewers should be able to read this information.</div><div class="form-actions">${canReview?`<button class="btn btn-light" data-action="set-claim-status" data-id="${esc(c.id)}" data-status="Rejected">Reject claim</button><button class="btn btn-primary" data-action="set-claim-status" data-id="${esc(c.id)}" data-status="Approved">Approve for handover</button>`:`<button class="btn btn-primary" data-action="close-modal">Close</button>`}</div>`);
}
function newItemId(){return `LF-${String(Math.max(1000,...items.map(i=>Number(String(i.id).replace(/\D/g,''))||0)+1))}`;}
function handleReportSubmit(form) {
 const fd=new FormData(form); const type=form.dataset.type;
 const item={id:newItemId(),type,title:fd.get('title').trim(),category:fd.get('category'),colour:fd.get('colour').trim(),brand:fd.get('brand').trim(),location:fd.get('location').trim(),date:fd.get('date'),description:fd.get('description').trim(),emoji:categoryEmoji[fd.get('category')]||'📦',visual:visualFor(fd.get('category'),fd.get('title')),owner:userName(),createdAt:new Date().toISOString(),status:'Open'};
 if(currentPhotoData)item.imageData=currentPhotoData;
 items.unshift(item);
 const candidates=getMatches().filter(m=>m.lost.id===item.id||m.found.id===item.id).sort((a,b)=>b.score-a.score);
 addNotification({type:'report',title:'Your report is live',body:`${item.title} was added to the campus directory.`,itemId:item.id});
 if(candidates.length&&candidates[0].score>=40)addNotification({type:'match',title:'A potential match was detected',body:`A report may match “${item.title}” (${candidates[0].score}% similarity). Review the details carefully.`,itemId:item.id});
 saveAll(); closeModal(); currentView='my-reports';render();toast('Report submitted',candidates.length&&candidates[0].score>=40?'A potential match was detected.':'Your report is now in the directory.');
}
function visualFor(category,title='') { const t=title.toLowerCase(); if(t.includes('key'))return 'keys';if(t.includes('bottle'))return 'bottle';if(t.includes('headphone')||t.includes('earbud'))return 'headphones';if(t.includes('phone')||t.includes('usb'))return 'phone';if(t.includes('wallet'))return 'wallet';if(t.includes('id'))return 'id';if(t.includes('laptop')||t.includes('computer'))return 'laptop';if(t.includes('bag')||t.includes('case'))return 'bag';return ({Electronics:'phone',Accessories:'keys',Drinkware:'bottle','Personal items':'wallet',Clothing:'bag',Books:'bag',Other:'bag'})[category]||'bag';}
function handleClaimSubmit(form) {
 const fd=new FormData(form); const itemId=form.dataset.itemId; const existing=claims.find(c=>c.itemId===itemId&&c.claimant===fd.get('claimant').trim()&&c.status==='Pending');
 if(existing){toast('Claim already submitted','There is already a pending request for this item.');return;}
 const claim={id:`CL-${Date.now().toString().slice(-7)}`,itemId,claimant:fd.get('claimant').trim(),email:fd.get('email').trim(),evidence:fd.get('evidence').trim(),status:'Pending',createdAt:new Date().toISOString(),owner:userName()};
 claims.unshift(claim);addNotification({type:'claim',title:'Claim request submitted',body:`Your claim for “${itemById(itemId)?.title||'an item'}” is waiting for review.`,itemId});saveAll();closeModal();navigate('claims');toast('Claim submitted','Your verification details have been saved for review in this demo.');
}
function handleProfileSubmit(form){
 const data=new FormData(form);
 if(!currentUser)return;
 const name=String(data.get('name')||'').trim();
 const email=normalizeEmail(data.get('email'));
 const campus=String(data.get('campus')||'').trim()||'Main Campus';
 if(!name||!email){toast('Missing details','Name and email are required.');return;}
 const idx=users.findIndex(u=>u.id===currentUser.id);
 if(idx>=0){
  if(users.some((u,i)=>i!==idx&&normalizeEmail(u.email)===email)){toast('Email in use','Another account already uses that email.');return;}
  users[idx]={...users[idx],name,email,campus}; saveUsers();
 }
 currentUser={...currentUser,name,email,campus};
 localStorage.setItem(STORAGE.session,JSON.stringify({userId:currentUser.id}));
 updateAccountChrome(); render();
 toast('Preferences saved',`Settings for ${name} were updated in this demo.`);
}
function handleClick(e) {
 const authTab=e.target.closest('[data-auth-tab]'); if(authTab){showAuthTab(authTab.dataset.authTab);return;}
 const viewBtn=e.target.closest('[data-view]'); if(viewBtn){if(!currentUser)return; navigate(viewBtn.dataset.view);return;}
 const btn=e.target.closest('[data-action]');if(!btn)return;
 const {action,id,type,status}=btn.dataset;
 switch(action){
  case 'report':reportForm(type||'lost');break;
  case 'details':detailsModal(id);break;
  case 'claim':claimForm(id);break;
  case 'close-modal':closeModal();break;
  case 'filter-type':exploreFilter=type;render();break;
  case 'save': saved.includes(id)?saved=saved.filter(x=>x!==id):saved.push(id);saveAll();render();toast(saved.includes(id)?'Item saved':'Removed from saved items');break;
  case 'read-notice':notifications=notifications.map(n=>n.id===id?{...n,read:true}:n);saveAll();render();break;
  case 'read-all':notifications=notifications.map(n=>({...n,read:true}));saveAll();render();toast('All caught up','All notifications are marked as read.');break;
  case 'change-status':{const item=itemById(id);if(item){item.status=item.status==='Returned'?'Open':'Returned';saveAll();closeModal();render();toast('Item status updated',`${item.title} is now ${item.status.toLowerCase()}.`);}break;}
  case 'claim-details':claimDetails(id);break;
  case 'set-claim-status':{const c=claims.find(x=>x.id===id);if(c){c.status=status;const it=itemById(c.itemId);if(status==='Approved'&&it){it.status='Returned';}addNotification({type:'claim',title:`Claim ${status.toLowerCase()}`,body:`The claim request for “${it?.title||'an item'}” was ${status.toLowerCase()}.`,itemId:c.itemId});saveAll();closeModal();render();toast(`Claim ${status.toLowerCase()}`,'The local demo status has been updated.');}break;}
  case 'claim-from-list':{const f=items.find(i=>i.type==='found'&&i.status!=='Returned');if(f)claimForm(f.id);else toast('No found items available','Browse items and open a found report first.');break;}
  case 'logout':showAuthScreen('login');toast('Signed out','Come back anytime.');break;
  case 'reset-demo':if(confirm('Reset all Findly demo data in this browser? Your local reports, claims and saved items will be cleared.')){items=[...seedItems];notifications=[...seedNotifications];claims=[];saved=[];saveAll();navigate('explore');toast('Demo data reset','The sample dataset has been restored.');}break;
 }
}

document.addEventListener('click',handleClick);
document.addEventListener('submit',e=>{
 if(e.target.id==='loginForm'){e.preventDefault();handleLoginSubmit(e.target);}
 else if(e.target.id==='signupForm'){e.preventDefault();handleSignupSubmit(e.target);}
 else if(e.target.id==='reportForm'){e.preventDefault();handleReportSubmit(e.target);}
 else if(e.target.id==='claimForm'){e.preventDefault();handleClaimSubmit(e.target);}
 else if(e.target.id==='profileForm'){e.preventDefault();handleProfileSubmit(e.target);}
});
document.addEventListener('input',e=>{
 if(e.target.id==='exploreSearch'){searchQuery=e.target.value;const start=e.target.selectionStart;const end=e.target.selectionEnd;render();const s=$('#exploreSearch');if(s){s.focus();s.setSelectionRange(start,end);}}
});
document.addEventListener('change',e=>{
 if(e.target.id==='exploreSearch'){searchQuery=e.target.value;render();const s=$('#exploreSearch');s?.focus();if(s)s.setSelectionRange(searchQuery.length,searchQuery.length);}
 if(e.target.id==='categoryFilter'){selectedCategory=e.target.value;render();}
 if(e.target.id==='itemImage'){const file=e.target.files?.[0];if(!file)return;if(!file.type.startsWith('image/')){toast('Choose an image','Please select an image file.');e.target.value='';return;}if(file.size>3*1024*1024){toast('Image is too large','Choose an image smaller than 3 MB for this demo.');e.target.value='';return;}const reader=new FileReader();reader.onload=()=>{currentPhotoData=reader.result;const label=$('#uploadLabel');const preview=$('#imagePreview');if(label)label.textContent=file.name;if(preview)preview.textContent='Photo ready to include in report.';};reader.readAsDataURL(file);}
});
$('#globalSearch').addEventListener('input',e=>{if(!currentUser)return;searchQuery=e.target.value;if(currentView!=='explore'){currentView='explore';render();const inp=$('#exploreSearch');if(inp){inp.focus();inp.setSelectionRange(searchQuery.length,searchQuery.length);}}else{const start=e.target.selectionStart;const end=e.target.selectionEnd;render();$('#globalSearch').focus();$('#globalSearch').setSelectionRange(start,end);}});
$('#topNotifications').addEventListener('click',()=>{if(currentUser)navigate('notifications');});
$('#mobileMenu').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
$('#closeModal').addEventListener('click',closeModal);
$('#modalBackdrop').addEventListener('click',e=>{if(e.target===$('#modalBackdrop'))closeModal();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#modalBackdrop').hidden)closeModal();if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(currentUser)$('#globalSearch').focus();}});
// Handle keyboard activation for report rows styled as interactive surfaces.
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('.match-row[role="button"]')&&!e.target.closest('button')){e.preventDefault();detailsModal(e.target.dataset.id);}});
if(!restoreSession()) showAuthScreen('login');
