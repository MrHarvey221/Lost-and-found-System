/* Findly v3. Plain JavaScript, real API data, no browser-stored accounts or scores. */
'use strict';
const $=(selector,root=document)=>root.querySelector(selector);
const $$=(selector,root=document)=>[...root.querySelectorAll(selector)];
const esc=(value='')=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state={user:null,items:[],matches:[],claims:[],notifications:[],users:[],history:[],method:null,demo:false,
  view:'home',reportType:'lost',filter:'all',query:'',category:'all',busy:false,savedReport:null};
const categories=['Drinkware','Electronics','Bags','Accessories','Personal items','Clothing','Books','Other'];
const roleNames={student:'Student',staff:'University staff',security:'Security officer',lost_property:'Lost property officer',administrator:'Administrator'};
const statusNames={reported:'Still looking',claim_approved:'Ready for collection',returned:'Recovered',closed:'Closed',submitted:'Pending',more_information:'More information required',approved:'Approved',rejected:'Rejected',completed:'Recovered'};
const icons={
 home:'M3 10 12 3l9 7M5 9v11h5v-6h4v6h5V9',
 search:'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
 report:'M12 5v14M5 12h14M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2',
 reports:'M7 3h10l4 4v14H3V3h4M7 11h10M7 15h10M7 7h5',
 match:'m12 2 2.5 6.5L21 11l-6.5 2.5L12 20l-2.5-6.5L3 11l6.5-2.5L12 2M20 2v4M18 4h4',
 bell:'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4',
 check:'m5 12 4 4L19 6',claim:'M12 3 3 6v6c0 5 9 9 9 9s9-4 9-9V6l-9-3m-4 9 3 3 5-6',
 person:'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0M4 21v-2a8 8 0 0 1 16 0v2',
 arrow:'M5 12h14m-5-5 5 5-5 5',pin:'M19 10c0 6-7 12-7 12S5 16 5 10a7 7 0 0 1 14 0M14 10a2 2 0 1 1-4 0 2 2 0 0 1 4 0',
 bag:'M5 7h14l2 14H3L5 7m3 0V5a4 4 0 0 1 8 0v2',
 bottle:'M9 2h6v4l2 3v12H7V9l2-3V2m0 4h6M7 12h10',
 laptop:'M4 4h16v12H4V4M2 20h20l-2-4H4l-2 4',
 keys:'M10 9a4 4 0 1 1-8 0 4 4 0 0 1 8 0m0 0h12m-4 0v4m-4-4v3',
 book:'M3 3h8l1 2 1-2h8v17h-8l-1 1-1-1H3V3m9 2v16',
 box:'m3 6 9-4 9 4v13l-9 3-9-3V6m0 0 9 4 9-4m-9 4v12',
 info:'M12 11v6m0-10v.1M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 clock:'M12 7v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 users:'M9 9a3 3 0 1 1 0-6 3 3 0 0 1 0 6m6-6a3 3 0 0 1 0 6M2 21v-3a7 7 0 0 1 14 0v3m3-7a5 5 0 0 1 3 4v3',
 logout:'M9 3H3v18h6m5-5 5-4-5-4m-6 4h11',
};
const icon=name=>`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${icons[name]||icons.box}"/></svg>`;
const officer=()=>['security','lost_property','administrator'].includes(state.user?.role);
const admin=()=>state.user?.role==='administrator';
const userId=()=>state.user?.user_id;
const fullName=user=>[user?.name,user?.surname].filter(Boolean).join(' ');
const initials=user=>[user?.name?.[0],user?.surname?.[0]].filter(Boolean).join('').toUpperCase()||'?';
const today=()=>{const d=new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,10);};
const dateLabel=value=>value?new Date(value.slice(0,10)+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'Date not recorded';
function ago(value){if(!value)return 'Earlier';const m=Math.max(0,Math.floor((Date.now()-new Date(value))/60000));return m<1?'Just now':m<60?`${m} min ago`:m<1440?`${Math.floor(m/60)} hr ago`:dateLabel(value);}
const itemById=id=>state.items.find(item=>item.id===id);
const ownReports=()=>state.items.filter(item=>item.reporter_id===userId());
const ownClaims=()=>state.claims.filter(claim=>claim.claimant_id===userId());
const canClaim=item=>item?.type==='found'&&item.status==='reported'&&item.reporter_id!==userId();
const activeClaim=id=>ownClaims().find(c=>c.found_item_id===id&&['submitted','more_information','approved','completed'].includes(c.claim_status));
const itemIcon=item=>({Drinkware:'bottle',Electronics:'laptop',Bags:'bag',Accessories:'keys',Books:'book'})[item?.category]||'box';
let modalReturn=null,previewURLs=[],sessionEpoch=0;

async function api(path,{method='GET',body}={}){
  const headers={'X-Findly-Request':'1'};
  if(body!==undefined&&!(body instanceof FormData)){headers['Content-Type']='application/json';body=JSON.stringify(body);}
  let response;
  try{response=await fetch('/api'+path,{method,headers,body,credentials:'same-origin',cache:'no-store'});}
  catch{throw new Error('We couldn’t reach Findly. Check your connection or the Python server, then try again.');}
  const data=response.status===204?null:await response.json();
  if(!response.ok){
    if(response.status===401&&state.user)showAuth();
    const detail=Array.isArray(data?.detail)?data.detail.map(v=>`${v.loc.slice(1).join(' ')}: ${v.msg}`).join('. '):data?.detail;
    throw new Error(detail||'Something went wrong. Please try again.');
  }
  return data;
}

async function loadData({renderPage=true}={}){
  const epoch=sessionEpoch;
  const me=await api('/auth/me');
  const [items,matches,claims,notifications,method,config]=await Promise.all([
    api('/reports'),api('/matches'),api('/claims'),api('/notifications'),api('/matching/status'),api('/config')]);
  if(epoch!==sessionEpoch)return;
  state.user=me;Object.assign(state,{items,matches,claims,notifications,method,demo:config.demo_mode});
  if(admin())[state.users,state.history]=await Promise.all([api('/admin/users'),api('/admin/history')]);
  else{state.users=[];state.history=[];}
  $('#connectionNotice').hidden=true;updateChrome();if(renderPage)render();
}

function showAuth(mode='login'){
  sessionEpoch++;
  Object.assign(state,{user:null,items:[],matches:[],claims:[],notifications:[],users:[],history:[],view:'home'});
  $('#boot').hidden=true;$('#appShell').hidden=true;$('#authShell').hidden=false;
  closeModal();authTab(mode);
}
function authTab(mode){
  $$('#authShell [role=tab]').forEach(tab=>{const on=tab.dataset.auth===mode;tab.classList.toggle('active',on);tab.setAttribute('aria-selected',String(on));});
  $('#loginPane').hidden=mode!=='login';$('#signupPane').hidden=mode!=='signup';
  for(const id of ['loginError','signupError']){$('#'+id).hidden=true;$('#'+id).textContent='';}
}
async function enterApp(){
  await loadData({renderPage:false});
  if(!state.user)return;
  $('#boot').hidden=true;$('#authShell').hidden=true;$('#appShell').hidden=false;
  const hash=location.hash.slice(1).split('/');
  navigate(['home','report','reports','matches','notifications','claims','profile'].includes(hash[0])?hash[0]:'home',false);
  if(hash[0]==='match'&&hash[1])await viewMatch(Number(hash[1]));
}

function updateChrome(){
  if(!state.user)return;
  $('#avatar').textContent=initials(state.user);$('#accountName').textContent=fullName(state.user);$('#accountRole').textContent=roleNames[state.user.role]||state.user.role;
  $('#campusLabel').textContent=state.user.campus;$('#demoLabel').hidden=!state.demo;$('#bellIcon').innerHTML=icon('bell');
  const unread=state.notifications.filter(n=>!n.read_at).length;
  $('#notificationCount').textContent=unread>99?'99+':unread;$('#notificationCount').hidden=!unread;
  const nav=[['home','home','Home'],['report','report','Report an Item'],['reports','reports','My Reports'],['matches','match','Matches'],['notifications','bell','Notifications'],['claims','claim','My Claims'],['profile','person','Profile']];
  let html=nav.map(([view,symbol,title])=>`<button class="nav-link ${state.view===view?'active':''}" data-view="${view}">${icon(symbol)}<span>${title}</span>${view==='notifications'&&unread?`<span class="nav-count">${unread}</span>`:''}</button>`).join('');
  if(officer())html+=`<div class="nav-caption management-title">CAMPUS MANAGEMENT</div>${[['review','claim','Review Claims'],['manage','box','Manage Items']].map(([view,symbol,title])=>`<button class="nav-link ${state.view===view?'active':''}" data-view="${view}">${icon(symbol)}<span>${title}</span></button>`).join('')}`;
  if(admin())html+=`<button class="nav-link ${state.view==='users'?'active':''}" data-view="users">${icon('users')}<span>Manage Users</span></button><button class="nav-link ${state.view==='audit'?'active':''}" data-view="audit">${icon('clock')}<span>Activity Log</span></button>`;
  $('#mainNav').innerHTML=html;
}

const heading=(title,text,action='')=>`<div class="page-heading"><div><h1>${title}</h1><p>${text}</p></div>${action}</div>`;
const sectionHeading=(title,view,text='View all')=>`<div class="section-heading"><h2>${title}</h2>${view?`<button class="text-button" data-view="${view}">${text} ${icon('arrow')}</button>`:''}</div>`;
function pill(status,type=''){
  const label=status==='reported'?(type==='found'?'Waiting for its owner':'Still looking'):statusNames[status]||status;
  const colour=['returned','completed','approved'].includes(status)?'green':status==='rejected'?'red':status==='closed'?'grey':['submitted','more_information','claim_approved'].includes(status)?'amber':'';
  return `<span class="pill ${colour}">${esc(label)}</span>`;
}
function picture(item,className='item-picture'){
  return `<div class="${className} ${item?.type==='found'?'found':''}">${item?.image_url?`<img src="${esc(item.image_url)}" alt="${esc(item.title)}" loading="lazy">`:icon(itemIcon(item))}</div>`;
}
function empty(title,message,action=''){
  return `<div class="empty-state">${icon('search')}<h3>${title}</h3><p>${message}</p>${action}</div>`;
}
function reportRow(item){return `<div class="report-row">${picture(item)}<div class="row-text"><strong>${esc(item.title)}</strong><small>${esc(item.location)} · ${dateLabel(item.date)}</small></div>${pill(item.status,item.type)}<button class="row-action" data-action="item" data-id="${item.id}" aria-label="View ${esc(item.title)}">${icon('arrow')}</button></div>`;}
function claimRow(claim,review=false){return `<div class="claim-row">${picture(itemById(claim.item_id))}<div class="row-text"><h3>${esc(claim.item_title)}</h3><p>${review?esc(claim.claimant_name)+' · ':''}${dateLabel(claim.created_at)}</p></div>${pill(claim.claim_status)}<button class="text-button" data-action="claim-detail" data-id="${claim.claim_id}">${review?'Review':'View status'} →</button></div>`;}
function noticeRow(note){
  return `<article class="notice-row ${note.read_at?'':'unread'}"><span class="notice-symbol">${icon(note.event_type==='match'?'match':note.event_type==='claim'?'claim':'bell')}</span><div class="notice-copy"><p>${esc(note.message_summary)}</p><time>${ago(note.timestamp)}</time><div>${note.match_id?`<button class="text-button" data-action="notification-match" data-id="${note.match_id}" data-note="${note.notification_id}">View potential match →</button>`:note.event_type==='claim'?`<button class="text-button" data-view="${officer()?'review':'claims'}">${officer()?'Review claims':'View my claims'} →</button>`:''}${!note.read_at?`<button class="text-button" data-action="read-note" data-id="${note.notification_id}">Mark read</button>`:''}</div></div>${note.read_at?'':'<span class="unread-dot" aria-label="Unread"></span>'}</article>`;
}

function actionCards(){return `<div class="action-grid"><button class="action-card" data-action="start-report" data-type="lost"><div><span class="action-symbol">${icon('search')}</span><h2>I lost something</h2><p>Tell us what’s missing.<br>We’ll keep an eye out.</p></div><span class="action-arrow">↗</span></button><button class="action-card found" data-action="start-report" data-type="found"><div><span class="action-symbol">${icon('bag')}</span><h2>I found something</h2><p>Help a belonging<br>find its person.</p></div><span class="action-arrow">↗</span></button></div>`;}

function homeView(){
  const mine=ownReports(),lost=mine.filter(i=>i.type==='lost'),found=mine.filter(i=>i.type==='found');
  const myMatches=state.matches.filter(m=>m.lost.reporter_id===userId()&&m.found.reporter_id!==userId());
  return `<div class="page-heading welcome-heading"><div><span class="eyebrow">GOOD THINGS FIND THEIR WAY BACK</span><h1>Hi ${esc(state.user.name)}<em>.</em> What brings you here?</h1><p>Lost or found, you’re in the right place.</p></div><button class="text-button heading-link" data-view="browse">Browse campus items ${icon('arrow')}</button></div>
    ${actionCards()}
    ${myMatches.length?`<div class="match-callout">${icon('match')}<div><strong>${myMatches.length===1?'There’s a possible match for your item.':`There are ${myMatches.length} possible matches for your items.`}</strong><p>Someone on campus may have found what you’re looking for.</p></div><button class="text-button" data-action="view-match" data-id="${myMatches[0].match_id}">Take a look →</button></div>`:''}
    <div class="home-columns">${[['My lost items',lost,'lost','search'],['My found items',found,'found','bag']].map(([title,rows,type,symbol])=>`<section class="panel"><div class="panel-heading"><h3>${icon(symbol)}${title}</h3><button class="text-button" data-action="start-report" data-type="${type}">+ Add</button></div>${rows.length?rows.slice(0,3).map(reportRow).join(''):`<div class="empty-inline"><strong>${type==='lost'?'Nothing missing? That’s a good day.':'Found something on campus?'}</strong>${type==='lost'?'Your lost reports will stay here while we keep checking.':'A quick report could make someone’s day.'}</div>`}</section>`).join('')}</div>
    ${sectionHeading('Potential matches','matches')}${myMatches.length?`<div class="match-grid">${myMatches.slice(0,2).map(matchCard).join('')}</div>`:`<div class="panel"><div class="empty-inline"><strong>We’re keeping an eye out.</strong>${lost.length?'We’ll notify you when someone reports something similar.':'Report a lost item and we’ll automatically check the found reports for you.'}</div></div>`}
    <div class="home-columns"><section>${sectionHeading('Recent notifications','notifications')}<div class="panel">${state.notifications.length?state.notifications.slice(0,3).map(noticeRow).join(''):'<div class="empty-inline"><strong>You’re all caught up.</strong>Report and claim updates will appear here.</div>'}</div></section><section>${sectionHeading('My ownership claims','claims')}<div class="panel">${ownClaims().length?ownClaims().slice(0,3).map(c=>claimRow(c)).join(''):'<div class="empty-inline"><strong>See something that might be yours?</strong>Open a match and choose “This might be mine”. An officer will help verify it.</div>'}</div></section></div>`;
}

function matchCard(match){
  const found=match.found,existing=activeClaim(found.record_id);
  return `<article class="match-card">${picture(found,'match-photo')}<div class="match-body"><span class="overline">POSSIBLE FOUND ITEM</span><h3>${esc(found.title)}</h3><p class="pair-lost">May match ${match.lost.reporter_id===userId()?'your':'a'} lost ${esc(match.lost.title)}</p><div class="location-line">${icon('pin')}${esc(found.location)}</div><div class="location-line">${icon('clock')}${dateLabel(found.date)} · ${Math.round(match.similarity_score)}% similarity</div><ul class="match-reasons">${match.reasons.slice(0,3).map(reason=>`<li>${esc(reason)}</li>`).join('')}</ul><div class="card-actions"><button class="button" data-action="view-match" data-id="${match.match_id}">View Match</button>${canClaim(found)&&!existing?`<button class="button primary" data-action="claim" data-id="${found.id}" data-lost="${match.lost.reporter_id===userId()?match.lost.record_id:''}">This Might Be Mine</button>`:existing?`<button class="button soft" data-action="claim-detail" data-id="${existing.claim_id}">View My Claim</button>`:''}</div></div></article>`;
}
function matchesView(){
  return `${heading('Could one of these be yours?','We check new reports automatically. You don’t need to keep searching.')}<div class="match-grid">${state.matches.length?state.matches.map(matchCard).join(''):empty('Nothing just yet.','Your report stays active. We’ll notify you when someone reports something similar.','<button class="button soft" data-action="start-report" data-type="lost">Report a lost item</button>')}</div><p class="match-footnote">A similarity score is a suggestion, never proof of ownership. A campus officer checks every ownership claim.</p><details class="method-note"><summary>How does Findly compare items?</summary><p>${esc(state.method?.label||'TF-IDF + contextual synonyms + attributes')}. ${esc(state.method?.detail||'')} We compare the descriptions, item names, colour, brand, location and dates. Photos help people identify items; Findly does not analyse their contents.</p></details>${officer()?'<button class="text-button small" data-action="recheck">Recheck active reports</button>':''}`;
}

function itemCard(item){return `<article class="item-card"><div class="match-photo">${item.image_url?`<img src="${esc(item.image_url)}" alt="${esc(item.title)}" loading="lazy">`:icon(itemIcon(item))}<span class="type-tag ${item.type}">${item.type==='lost'?'LOST':'FOUND'}</span></div><div class="item-card-body">${pill(item.status,item.type)}<h3>${esc(item.title)}</h3><p class="description">${esc(item.description)}</p><div class="location-line">${icon('pin')}${esc(item.location)}</div><div class="location-line">${icon('clock')}${dateLabel(item.date)}</div><button class="button wide" data-action="item" data-id="${item.id}">View item ${icon('arrow')}</button></div></article>`;}
function reportsView(all=false){
  const source=all?state.items:ownReports();
  const rows=source.filter(i=>(state.filter==='all'||i.type===state.filter)&&(state.category==='all'||i.category===state.category)&&`${i.title} ${i.description} ${i.colour||''} ${i.brand||''} ${i.location}`.toLowerCase().includes(state.query.toLowerCase()));
  return `${heading(all?'Around your campus':'My reports',all?'Browse lost and found reports from the campus community.':'Your reports stay active until an item is recovered or you close them.',`<button class="button primary" data-view="report">+ New report</button>`)}<div class="filter-bar"><input id="reportSearch" type="search" placeholder="Search items, places or details…" aria-label="Search reports" value="${esc(state.query)}"><select id="categoryFilter" aria-label="Filter category"><option value="all">All categories</option>${categories.map(c=>`<option ${state.category===c?'selected':''}>${esc(c)}</option>`).join('')}</select><div class="segmented" aria-label="Report type">${[['all','All'],['lost','Lost'],['found','Found']].map(([type,title])=>`<button class="${state.filter===type?'active':''}" data-action="filter" data-type="${type}">${title}</button>`).join('')}</div></div><div class="item-grid">${rows.length?rows.map(itemCard).join(''):empty('No reports here yet.',all?'Try another search, or tell the campus about a lost or found item.':'Start with one of the two reporting buttons. We’ll take it from there.','<button class="button soft" data-view="report">Report an item</button>')}</div>${!all?'<p class="match-footnote"><button class="text-button" data-view="browse">Browse all campus reports →</button></p>':''}`;
}

function reportView(){
  const found=state.reportType==='found';
  return `${heading(found?'Let’s find its person.':'Let’s get it back.',found?'Thank you for helping. A few details can make all the difference.':'Describe it in your own words. We’ll check the found reports for you.')}<div class="segmented" style="margin-bottom:23px"><button class="${!found?'active':''}" data-action="start-report" data-type="lost">I lost something</button><button class="${found?'active':''}" data-action="start-report" data-type="found">I found something</button></div><div class="form-layout"><form id="reportForm" class="form-card" data-type="${state.reportType}">
    <section class="form-section"><h2>First, the item.</h2><p class="section-subtitle">Every detail helps. Keep one unique identifying detail private.</p><div class="form-grid"><div><label for="itemTitle">Item name</label><input id="itemTitle" name="title" placeholder="e.g. Pink water bottle" minlength="2" maxlength="90" required></div><div><label for="itemCategory">Category</label><select id="itemCategory" name="category" required><option value="">Choose a category</option>${categories.map(c=>`<option>${c}</option>`).join('')}</select></div><div class="full"><label for="itemDescription">What does it look like?</label><textarea id="itemDescription" name="description" placeholder="e.g. A large pink drinking bottle, about two litres. It has a handle and a grey lid." minlength="5" maxlength="2000" required></textarea><small class="field-help">Natural descriptions are welcome. You don’t need special keywords.</small></div><div><label for="itemColour">Colour</label><input id="itemColour" name="colour" list="colourList" placeholder="e.g. Pink, rose or light pink" maxlength="50" required><datalist id="colourList">${['Black','White','Blue','Pink','Rose','Green','Grey','Brown','Purple','Red'].map(c=>`<option>${c}</option>`).join('')}</datalist></div><div><label for="itemBrand">Brand <span class="muted">(optional)</span></label><input id="itemBrand" name="brand" placeholder="e.g. Hydro Flask" maxlength="80"></div></div></section>
    <section class="form-section"><h2>Where and when?</h2><div class="form-grid"><div><label for="itemLocation">${found?'Where was it found?':'Last known location'}</label><input id="itemLocation" name="location" placeholder="e.g. Main campus library" minlength="2" maxlength="150" required></div><div><label for="itemDate">${found?'Date found':'Approximate date lost'}</label><input id="itemDate" name="date" type="date" value="${today()}" max="${today()}" required></div>${found?'<div class="full"><label for="itemStorage">Where is it being kept?</label><input id="itemStorage" name="storage_location" placeholder="e.g. With me, or Campus Security front desk" minlength="2" maxlength="150" required><small class="field-help">Only you and authorized campus officers can see this location.</small></div>':''}</div></section>
    <section class="form-section"><h2>${found?'A picture helps its owner.':'Have a picture?'}</h2><p class="section-subtitle">${found?'Add up to four photographs, if you can.':'You can add one photo, or leave this blank.'}</p><label for="itemPhotos">Item ${found?'photographs':'photograph'} <span class="muted">(optional)</span></label><input id="itemPhotos" name="photos" type="file" accept="image/jpeg,image/png,image/webp" ${found?'multiple':''}><small class="field-help">JPG, PNG or WEBP · up to 3 MB per photo. Keep personal documents out of public pictures.</small><div id="photoPreview" class="photo-preview"></div></section>
    <p id="reportError" class="form-error" role="alert" hidden></p><div class="form-actions"><button type="button" class="button" data-view="home">Cancel</button><button class="button primary" type="submit">${found?'Submit found report':'Submit lost report'} ${icon('arrow')}</button></div></form><aside class="form-tip">${icon('info')}<h3>You report. We keep checking.</h3><p>Your report goes into the campus database and is compared with the other item reports automatically.</p><ol><li>Tell us about the item.</li><li>We look for similar lost or found reports.</li><li>You receive a notification when there’s a possible match.</li><li>An officer helps verify ownership before a return.</li></ol></aside></div>`;
}

function successView(){
  const item=state.savedReport,pairs=state.matches.filter(m=>m[item.type].id===item.id);
  return `<section class="success-card"><div class="success-symbol">${icon('check')}</div><h1>Your report is saved.</h1><p>${pairs.length?'Good news — we found a possible match. Take a look below.':"Your report has been saved. We’ll notify you when someone reports something similar."}</p><p class="small muted">${esc(item.title)} · ${item.type==='lost'?'Lost report':'Found report'}</p><div class="form-actions"><button class="button" data-view="reports">View my reports</button><button class="button primary" data-view="home">Back to Home</button></div>${pairs.length?`<div class="success-matches"><h2>Worth a look</h2>${pairs.slice(0,2).map(matchCard).join('')}</div>`:''}</section>`;
}

function claimsView(review=false){
  if(review&&!officer())return empty('This page is for campus officers.','Return Home to continue.');
  const rows=review?state.claims.filter(c=>c.claimant_id!==userId()):ownClaims();
  return `${heading(review?'A careful check. A safe return.':'My ownership claims',review?'Review private evidence, ask for more information, and record a decision.':'Follow your claim from the first check to collecting your item.')}<div class="panel">${rows.length?rows.map(c=>claimRow(c,review)).join(''):`<div class="empty-state">${icon('claim')}<h3>${review?'The review queue is clear.':'No claims yet.'}</h3><p>${review?'New claims will appear here for authorized review.':'See something that might be yours? Open a match and choose “This Might Be Mine”.'}</p>${!review?'<button class="button soft" data-view="matches">See potential matches</button>':''}</div>`}</div>`;
}
function notificationsView(){return `${heading('A little good news.','Your reports, matches and ownership updates, all in one place.','<button class="button" data-action="read-all">Mark all as read</button>')}<section class="panel">${state.notifications.length?state.notifications.map(noticeRow).join(''):'<div class="empty-state">'+icon('bell')+'<h3>You’re all caught up.</h3><p>We’ll let you know when there’s something to see.</p></div>'}</section>`;}
function profileView(){const u=state.user;return `${heading('A little about you.','Keep your campus details up to date.')}<div class="profile-layout"><aside class="panel profile-card"><span class="avatar">${esc(initials(u))}</span><h2>${esc(fullName(u))}</h2><p>${esc(u.email)}</p><span class="pill">${esc(roleNames[u.role])}</span><button class="button wide" data-action="logout">${icon('logout')}Log out</button></aside><form id="profileForm" class="form-card"><h2>Campus profile</h2><div class="form-grid"><div><label for="profileName">First name</label><input id="profileName" name="name" value="${esc(u.name)}" maxlength="90" required></div><div><label for="profileSurname">Surname</label><input id="profileSurname" name="surname" value="${esc(u.surname)}" maxlength="90"></div><div class="full"><label for="profileCampus">Campus</label><input id="profileCampus" name="campus" value="${esc(u.campus)}" maxlength="80" required></div><div class="full"><label for="profileEmail">Email address</label><input id="profileEmail" value="${esc(u.email)}" readonly><small class="field-help">Contact your administrator if your account email needs attention.</small></div></div><p id="profileError" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary">Save profile</button></div></form></div>`;}
function usersView(){if(!admin())return '';return `${heading('Campus accounts','Manage roles and account access. Changes revoke existing sessions.')}<div class="table-wrap"><table class="data-table"><thead><tr><th>Person</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead><tbody>${state.users.map(u=>`<tr><td>${esc(fullName(u))}</td><td>${esc(u.email)}</td><td>${esc(roleNames[u.role])}</td><td>${esc(u.account_status)}</td><td>${u.user_id!==userId()?`<button class="text-button" data-action="edit-user" data-id="${u.user_id}">Manage</button>`:'You'}</td></tr>`).join('')}</tbody></table></div>`;}
function auditView(){if(!admin())return '';return `${heading('Activity log','Report, claim and account actions recorded by Findly.')}<div class="table-wrap"><table class="data-table"><thead><tr><th>Time</th><th>Record</th><th>Previous</th><th>New status</th><th>Actor</th><th>Reason</th></tr></thead><tbody>${state.history.map(h=>`<tr><td>${esc(new Date(h.timestamp).toLocaleString())}</td><td>${esc(h.related_record_type)} #${h.related_record_id}</td><td>${esc(h.previous_status||'—')}</td><td>${esc(h.new_status)}</td><td>#${h.actor_id}</td><td>${esc(h.reason)}</td></tr>`).join('')}</tbody></table></div>`;}

function render(){
  if(!state.user)return;
  const views={home:homeView,report:reportView,reports:reportsView,browse:()=>reportsView(true),manage:()=>officer()?reportsView(true):homeView(),matches:matchesView,notifications:notificationsView,claims:claimsView,review:()=>claimsView(true),profile:profileView,users:usersView,audit:auditView,success:successView};
  const labels={home:'Home',report:'Report an Item',reports:'My Reports',browse:'Around campus',manage:'Manage Items',matches:'Matches',notifications:'Notifications',claims:'My Claims',review:'Review Claims',profile:'Profile',users:'Manage Users',audit:'Activity Log',success:'Report saved'};
  $('#pageContent').innerHTML=(views[state.view]||homeView)();$('#pageLabel').textContent=labels[state.view]||'Home';updateChrome();
}
function navigate(view,changeHash=true){
  if(['users','audit'].includes(view)&&!admin())return;if(['review','manage'].includes(view)&&!officer())return;
  if(view!==state.view){state.filter='all';state.query='';state.category='all';}
  state.view=view;closeNav();closeModal();revokePreviews();if(changeHash)history.replaceState(null,'','#'+view);render();window.scrollTo({top:0,behavior:'instant'});
}
function closeNav(){$('#sidebar').classList.remove('open');$('#navShade').hidden=true;}
function revokePreviews(){previewURLs.forEach(url=>URL.revokeObjectURL(url));previewURLs=[];}
function toast(title,message=''){
  const el=document.createElement('div');el.className='toast';el.setAttribute('role','status');el.innerHTML=`${icon('check')}<div><strong>${esc(title)}</strong>${message?`<p>${esc(message)}</p>`:''}</div>`;$('#toastStack').append(el);setTimeout(()=>el.remove(),6500);
}
function openModal(title,html){modalReturn=document.activeElement;$('#modalTitle').textContent=title;$('#modalBody').innerHTML=html;$('#modalBackdrop').hidden=false;document.body.style.overflow='hidden';const field=$('#modalBody input:not([readonly]),#modalBody textarea,#modalBody select,#modalBody button');(field||$('#closeModal')).focus();}
function closeModal(){$('#modalBackdrop').hidden=true;$('#modalBody').innerHTML='';document.body.style.overflow='';if(modalReturn?.isConnected)modalReturn.focus();}

function gallery(item){return item.image_urls?.length?`<div class="gallery">${item.image_urls.map(url=>`<img src="${esc(url)}" alt="Photograph of ${esc(item.title)}">`).join('')}</div>`:'';}
function facts(item){return `<dl class="detail-grid"><div><dt>Category</dt><dd>${esc(item.category)}</dd></div><div><dt>Colour</dt><dd>${esc(item.colour||'Not supplied')}</dd></div><div><dt>Brand</dt><dd>${esc(item.brand||'Not supplied')}</dd></div><div><dt>${item.type==='lost'?'Date lost':'Date found'}</dt><dd>${dateLabel(item.date)}</dd></div><div class="full"><dt>Location</dt><dd>${esc(item.location)}</dd></div><div class="full"><dt>Description</dt><dd class="private-text">${esc(item.description)}</dd></div></dl>`;}
async function viewItem(id){
  const old=itemById(id);if(!old)return;
  const item=await api(`/reports/${old.type}/${old.record_id}`);state.items=state.items.map(i=>i.id===id?item:i);
  const mine=item.reporter_id===userId(),existing=activeClaim(item.record_id);
  const reportMatches=state.matches.filter(m=>m[item.type].id===item.id);
  let controls='';
  if(mine||officer())controls+=`<button class="button" data-action="photos" data-id="${item.id}">Update ${item.type==='lost'?'photo':'photos'}</button>`;
  if(officer()&&item.status==='claim_approved')controls+=`<button class="button green" data-action="status" data-id="${item.id}" data-status="returned">Confirm recovery</button>`;
  if((officer()||mine&&item.type==='lost')&&item.status==='reported')controls+=`<button class="button" data-action="status" data-id="${item.id}" data-status="closed">Close report</button>`;
  if((officer()||mine&&item.type==='lost')&&item.status==='closed')controls+=`<button class="button" data-action="status" data-id="${item.id}" data-status="reported">Reopen report</button>`;
  if(canClaim(item)&&!existing)controls+=`<button class="button primary" data-action="claim" data-id="${item.id}">This Might Be Mine</button>`;
  if(item.type==='found'&&existing)controls+=`<button class="button primary" data-action="claim-detail" data-id="${existing.claim_id}">View my claim</button>`;
  openModal(item.title,`${pill(item.status,item.type)}${gallery(item)}${facts(item)}${item.storage_location?`<div class="note">Private storage location: ${esc(item.storage_location)}</div>`:''}${officer()&&item.type==='found'?`<p><button class="text-button" data-action="storage" data-id="${item.id}">Update storage location →</button></p>`:''}${reportMatches.length?`<div class="note green">There ${reportMatches.length===1?'is a possible match':'are possible matches'} for this report. <button class="text-button" data-action="view-match" data-id="${reportMatches[0].match_id}">Take a look →</button></div>`:''}<div class="form-actions">${controls||'<button class="button" data-action="close-modal">Done</button>'}</div>`);
}
async function viewMatch(id){
  const match=await api('/matches/'+id),found=match.found,existing=activeClaim(found.record_id);
  const ownLost=match.lost.reporter_id===userId();
  history.replaceState(null,'','#match/'+id);
  openModal('Could this be your item?',`${match.match_status!=='candidate'?'<div class="note">This match is no longer active. The item may already be reserved or recovered.</div>':''}${gallery(found)}<span class="eyebrow muted">${Math.round(match.similarity_score)}% SIMILARITY · A SUGGESTION, NOT PROOF</span><h3 style="margin-top:12px">${esc(found.title)}</h3><p class="muted">May match ${ownLost?'your':'the'} lost <strong>${esc(match.lost.title)}</strong>.</p><ul class="match-reasons">${match.reasons.map(reason=>`<li>${esc(reason)}</li>`).join('')}</ul><dl class="detail-grid"><div><dt>Lost near</dt><dd>${esc(match.lost.location)}<br>${dateLabel(match.lost.date)}</dd></div><div><dt>Found near</dt><dd>${esc(found.location)}<br>${dateLabel(found.date)}</dd></div><div class="full"><dt>Found-item description</dt><dd class="private-text">${esc(found.description)}</dd></div><div class="full"><dt>Lost-item description</dt><dd class="private-text">${esc(match.lost.description)}</dd></div></dl><div class="note">Recognise it? Tell an officer a private detail that only the owner would know. A match score alone can’t establish ownership.</div><div class="form-actions">${canClaim(found)&&!existing?`<button class="button primary" data-action="claim" data-id="${found.id}" data-lost="${ownLost?match.lost.record_id:''}">This Might Be Mine</button>`:existing?`<button class="button primary" data-action="claim-detail" data-id="${existing.claim_id}">View my claim</button>`:'<button class="button" data-action="close-modal">Done</button>'}</div>`);
}
function claimForm(id,lostId=''){
  const item=itemById(id);if(!canClaim(item))return;
  const mine=ownReports().filter(i=>i.type==='lost'&&i.status==='reported');
  openModal('This might be mine.',`<div class="note">You’re claiming <strong>${esc(item.title)}</strong>. Your answers are private to you and authorized campus officers.</div><form id="claimForm" data-item="${item.id}"><label for="claimStatement">Why do you believe this is yours?</label><textarea id="claimStatement" name="claim_statement" placeholder="Tell us when and how you lost it." minlength="8" maxlength="2000" required></textarea><label for="claimDetail">A private identifying detail</label><textarea id="claimDetail" name="private_description" placeholder="A unique scratch, something inside, a receipt detail, or another feature only the owner would know." minlength="8" maxlength="2000" required></textarea><small class="field-help">Do not include passwords, card numbers or unnecessary personal documents.</small>${mine.length?`<label for="claimLost">Link to my lost report <span class="muted">(optional)</span></label><select id="claimLost" name="lost_item_id"><option value="">No lost report to link</option>${mine.map(i=>`<option value="${i.record_id}" ${Number(lostId)===i.record_id?'selected':''}>${esc(i.title)}</option>`).join('')}</select>`:''}<label for="claimProof">Supporting proof <span class="muted">(optional)</span></label><input id="claimProof" name="proof" type="file" accept="image/jpeg,image/png,image/webp,application/pdf"><small class="field-help">A receipt or a photo showing prior possession. JPG, PNG, WEBP or PDF · max 3 MB.</small><label class="check-label"><input name="confirm" type="checkbox" required>I confirm this is my property and understand an officer must verify my claim.</label><p id="claimError" class="form-error" role="alert" hidden></p><div class="form-actions"><button type="button" class="button" data-action="close-modal">Cancel</button><button class="button primary" type="submit">Submit ownership claim</button></div></form>`);
}
async function claimDetail(id){
  const claim=await api('/claims/'+id),canReview=officer()&&claim.claimant_id!==userId()&&['submitted','more_information'].includes(claim.claim_status);
  const canAdd=claim.claimant_id===userId()&&['submitted','more_information'].includes(claim.claim_status);
  openModal('Ownership claim',`${pill(claim.claim_status)}<h3 style="margin:16px 0 7px">${esc(claim.item_title)}</h3><p class="muted small">${officer()?esc(claim.claimant_name)+' · ':''}Submitted ${dateLabel(claim.created_at)}</p><div class="note">These ownership details are private. A campus officer checks them before arranging a safe return.</div><label>Explanation of ownership</label><p class="private-text">${esc(claim.claim_statement)}</p>${(claim.evidence||[]).map((e,index)=>`<div class="evidence-entry"><strong>PRIVATE EVIDENCE ${index+1}</strong><p class="private-text">${esc(e.private_description)}</p>${e.file_url?`<a class="text-button" href="${esc(e.file_url)}" download>Download supporting proof →</a>`:''}</div>`).join('')}${claim.review_notes?`<div class="note"><strong>Officer’s response</strong><br>${esc(claim.review_notes)}</div>`:''}${claim.claim_status==='approved'?'<p class="note green" style="margin-top:16px">Your claim has been approved. Follow your officer’s collection instructions. The officer will record the recovery after the physical handover.</p>':''}
    ${canReview?`<form id="reviewForm" class="review-divider" data-id="${claim.claim_id}"><h3>Record your review</h3><label for="reviewNotes">Review notes or information required</label><textarea id="reviewNotes" name="reviewer_notes" minlength="5" maxlength="2000" placeholder="Explain what was checked or what the claimant should provide." required></textarea><label for="reviewDecision">Decision</label><select id="reviewDecision" name="decision"><option value="more_information">More Information Required</option><option value="approved">Approve for collection</option><option value="rejected">Reject claim</option></select><p id="reviewError" class="form-error" role="alert" hidden></p><div class="form-actions"><button type="submit" class="button primary">Record decision</button></div></form>`:''}
    ${canAdd?`<form id="evidenceForm" class="review-divider" data-id="${claim.claim_id}"><h3>Send more information</h3><label for="extraDetail">Additional private details</label><textarea id="extraDetail" name="private_description" minlength="8" maxlength="2000" required></textarea><label for="extraProof">Supporting file <span class="muted">(optional)</span></label><input id="extraProof" name="file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf"><p id="evidenceError" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary">Send more information</button></div></form>`:''}
    ${officer()&&claim.claim_status==='approved'?`<div class="form-actions"><button class="button green" data-action="status" data-id="${claim.item_id}" data-status="returned">Confirm recovery</button></div>`:''}`);
}
function statusForm(id,status){
  const item=itemById(id);if(!item)return;
  openModal(status==='returned'?'Confirm the recovery.':status==='closed'?'Close this report?':'Reopen this report?',`<form id="statusForm" data-item="${id}" data-status="${status}"><div class="note ${status==='returned'?'green':''}"><strong>${esc(item.title)}</strong><br>${status==='returned'?'Record this only after the verified owner has physically collected the item. The claim and its linked lost report will be completed.':status==='closed'?'The report will stop appearing in active matches.':'The report will be checked for potential matches again.'}</div><label for="statusReason">${status==='returned'?'Collection notes':'Reason'}</label><textarea id="statusReason" name="reason" minlength="5" maxlength="1000" placeholder="${status==='returned'?'e.g. Collected in person at the security desk; ownership evidence verified.':'Tell us why the report is changing.'}" required></textarea><p id="statusError" class="form-error" role="alert" hidden></p><div class="form-actions"><button type="button" class="button" data-action="close-modal">Cancel</button><button class="button ${status==='returned'?'green':'primary'}">${status==='returned'?'Confirm recovered':'Save status'}</button></div></form>`);
}
function storageForm(id){const item=itemById(id);if(!item||!officer())return;openModal('Where is it being kept?',`<form id="storageForm" data-item="${id}"><div class="note">Only the reporter and authorized officers can see this location.</div><label for="storageLocation">Current storage location</label><input id="storageLocation" name="storage_location" value="${esc(item.storage_location||'')}" placeholder="e.g. Security office, shelf B2" minlength="2" maxlength="150" required><label for="storageReason">Custody notes</label><textarea id="storageReason" name="reason" minlength="5" maxlength="1000" required></textarea><p id="storageError" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary">Save storage location</button></div></form>`);}
function photosForm(id){const item=itemById(id);if(!item)return;openModal('Update item photographs',`<form id="photosForm" data-item="${id}"><p class="muted">Choose ${item.type==='lost'?'one photo':'up to four photos'}. These replace the displayed gallery.</p><label for="replacementPhotos">Item photographs</label><input id="replacementPhotos" name="files" type="file" accept="image/jpeg,image/png,image/webp" ${item.type==='found'?'multiple':''} required><small class="field-help">JPG, PNG, WEBP · max 3 MB each.</small><p id="photosError" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary">Save photos</button></div></form>`);}
function userForm(id){const user=state.users.find(u=>u.user_id===Number(id));if(!user||!admin())return;openModal('Manage campus access',`<form id="userForm" data-id="${id}"><p>${esc(fullName(user))}<br><span class="muted">${esc(user.email)}</span></p><label for="userRole">Campus role</label><select id="userRole" name="role">${Object.entries(roleNames).map(([role,name])=>`<option value="${role}" ${user.role===role?'selected':''}>${name}</option>`).join('')}</select><label for="userStatus">Account status</label><select id="userStatus" name="account_status"><option value="active" ${user.account_status==='active'?'selected':''}>Active</option><option value="suspended" ${user.account_status==='suspended'?'selected':''}>Suspended</option></select><label for="userReason">Reason for change</label><textarea id="userReason" name="reason" minlength="5" maxlength="1000" required></textarea><p id="userError" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary">Save account access</button></div></form>`);}

function validatePhotos(files,kind){
  if(files.length>(kind==='lost'?1:4))throw new Error(kind==='lost'?'Choose one lost-item photo.':'Choose up to four found-item photos.');
  for(const file of files){if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>3*1024*1024)throw new Error('Use JPG, PNG or WEBP images no larger than 3 MB each.');}
}
function validateProof(file){if(file?.size>3*1024*1024)throw new Error('Choose proof no larger than 3 MB.');}
async function submitReport(form){
  const fd=new FormData(form),kind=form.dataset.type,files=$('#itemPhotos').files?[...$('#itemPhotos').files]:[];
  validatePhotos(files,kind);
  const body={title:fd.get('title'),category:fd.get('category'),description:fd.get('description'),colour:fd.get('colour')||null,brand:fd.get('brand')||null};
  body['location_'+kind]=fd.get('location');body['date_'+kind]=fd.get('date');if(kind==='found')body.storage_location=fd.get('storage_location');
  const report=await api('/reports/'+kind,{method:'POST',body});
  let warning='';
  if(files.length){const photos=new FormData();files.forEach(file=>photos.append('files',file));try{await api(`/reports/${kind}/${report.record_id}/photos`,{method:'POST',body:photos});}catch(error){warning=error.message;}}
  state.savedReport=report;state.view='success';history.replaceState(null,'','#success');revokePreviews();await loadData();window.scrollTo({top:0,behavior:'instant'});
  if(warning)toast('Your report is saved.','The photos didn’t upload: '+warning+' Open your report to retry.');
}
async function submitClaim(form){
  const fd=new FormData(form),item=itemById(form.dataset.item),proof=fd.get('proof');validateProof(proof);
  const claim=await api('/claims',{method:'POST',body:{found_item_id:item.record_id,lost_item_id:fd.get('lost_item_id')?Number(fd.get('lost_item_id')):null,claim_statement:fd.get('claim_statement'),private_description:fd.get('private_description')}});
  let warning='';
  if(proof?.size){const evidence=new FormData();evidence.append('private_description','Supporting proof of prior ownership.');evidence.append('file',proof);try{await api('/claims/'+claim.claim_id+'/evidence',{method:'POST',body:evidence});}catch(error){warning=error.message;}}
  closeModal();state.view='claims';await loadData();history.replaceState(null,'','#claims');toast('Your claim is with the campus officers.',warning?'Your details are saved, but the file didn’t upload. Open your claim to retry. '+warning:'We’ll notify you when an officer responds.');
}

const submitters={
  async loginForm(form){const fd=new FormData(form);await api('/auth/login',{method:'POST',body:{email:fd.get('email').trim(),password:fd.get('password')}});form.reset();history.replaceState(null,'','#home');await enterApp();},
  async signupForm(form){const fd=new FormData(form);if(fd.get('password')!==fd.get('confirm'))throw new Error('Your passwords don’t match. Please enter them again.');const names=fd.get('name').trim().split(/\s+/);await api('/auth/register',{method:'POST',body:{name:names.shift(),surname:names.join(' '),email:fd.get('email').trim(),password:fd.get('password'),campus:fd.get('campus'),role:fd.get('role')}});form.reset();history.replaceState(null,'','#home');await enterApp();toast('Welcome to Findly.','Start with “I lost something” or “I found something”.');},
  reportForm:submitReport,claimForm:submitClaim,
  async profileForm(form){const fd=new FormData(form);await api('/auth/me',{method:'PATCH',body:Object.fromEntries(fd)});await loadData();toast('Your profile is updated.');},
  async reviewForm(form){const fd=new FormData(form);await api(`/claims/${form.dataset.id}/review`,{method:'PATCH',body:Object.fromEntries(fd)});closeModal();await loadData();toast('Decision recorded.','The claimant has been notified.');},
  async evidenceForm(form){const fd=new FormData(form),file=fd.get('file');validateProof(file);if(!file?.size)fd.delete('file');await api(`/claims/${form.dataset.id}/evidence`,{method:'POST',body:fd});closeModal();await loadData();toast('Your information has been sent.','An officer will take another look.');},
  async statusForm(form){const item=itemById(form.dataset.item),fd=new FormData(form);await api(`/reports/${item.type}/${item.record_id}/status`,{method:'PATCH',body:{status:form.dataset.status,reason:fd.get('reason')}});closeModal();await loadData();toast(form.dataset.status==='returned'?'One more belonging, reunited.':'Report updated.','The change has been recorded.');},
  async storageForm(form){const item=itemById(form.dataset.item);await api(`/reports/found/${item.record_id}/storage`,{method:'PATCH',body:Object.fromEntries(new FormData(form))});closeModal();await loadData();toast('Storage location saved.');},
  async photosForm(form){const item=itemById(form.dataset.item),files=[...$('#replacementPhotos').files];validatePhotos(files,item.type);const fd=new FormData();files.forEach(file=>fd.append('files',file));await api(`/reports/${item.type}/${item.record_id}/photos`,{method:'POST',body:fd});closeModal();await loadData();toast('Photographs updated.');},
  async userForm(form){await api('/admin/users/'+form.dataset.id,{method:'PATCH',body:Object.fromEntries(new FormData(form))});closeModal();await loadData();toast('Campus access updated.');},
};

document.addEventListener('submit',async event=>{
  const form=event.target,submit=submitters[form.id];if(!submit)return;event.preventDefault();if(state.busy||!form.reportValidity())return;
  state.busy=true;const button=form.querySelector('button[type=submit],button:not([type])'),html=button?.innerHTML;
  if(button){button.disabled=true;button.innerHTML='<span class="spinner"></span> One moment…';}
  const error=$('#'+form.id.replace('Form','Error'));if(error)error.hidden=true;
  try{await submit(form);}catch(problem){if(error?.isConnected){error.textContent=problem.message;error.hidden=false;error.scrollIntoView({block:'nearest'});}else toast('We couldn’t save that.',problem.message);}
  finally{state.busy=false;if(button?.isConnected){button.disabled=false;button.innerHTML=html;}}
});

document.addEventListener('click',async event=>{
  const auth=event.target.closest('[data-auth]');if(auth){authTab(auth.dataset.auth);return;}
  const nav=event.target.closest('[data-view]');if(nav){event.preventDefault();if(state.user&&!state.busy)navigate(nav.dataset.view);return;}
  const button=event.target.closest('[data-action]');if(!button||state.busy)return;
  const {action,id,type,status,lost,note}=button.dataset;
  try{
    switch(action){
      case 'start-report':state.reportType=type;navigate('report');break;
      case 'item':await viewItem(id);break;
      case 'view-match':await viewMatch(Number(id));break;
      case 'notification-match':await api(`/notifications/${note}/read`,{method:'PATCH'});await loadData();await viewMatch(Number(id));break;
      case 'claim':claimForm(id,lost);break;
      case 'claim-detail':await claimDetail(id);break;
      case 'close-modal':closeModal();break;
      case 'filter':state.filter=type;render();break;
      case 'status':statusForm(id,status);break;
      case 'storage':storageForm(id);break;
      case 'photos':photosForm(id);break;
      case 'edit-user':userForm(id);break;
      case 'read-note':await api(`/notifications/${id}/read`,{method:'PATCH'});await loadData();break;
      case 'read-all':await api('/notifications/read-all',{method:'PATCH'});await loadData();toast('You’re all caught up.');break;
      case 'recheck':state.busy=true;button.disabled=true;await api('/matches/recheck',{method:'POST'});await loadData();toast('Active reports have been rechecked.');break;
      case 'logout':await api('/auth/logout',{method:'POST'});history.replaceState(null,'','#home');showAuth();$('#loginForm').reset();toast('You’re signed out.');break;
    }
  }catch(error){toast('We couldn’t do that.',error.message);}
  finally{if(action==='recheck'){state.busy=false;button.disabled=false;}}
});
document.addEventListener('input',event=>{
  if(event.target.id==='reportSearch'){state.query=event.target.value;const position=event.target.selectionStart;render();$('#reportSearch').focus();try{$('#reportSearch').setSelectionRange(position,position);}catch{}}
});
document.addEventListener('change',event=>{
  if(event.target.id==='categoryFilter'){state.category=event.target.value;render();}
  if(event.target.id==='itemPhotos'){
    revokePreviews();const files=[...event.target.files];
    try{validatePhotos(files,state.reportType);$('#photoPreview').innerHTML=files.map(file=>{const url=URL.createObjectURL(file);previewURLs.push(url);return `<img src="${url}" alt="Photo preview">`;}).join('');}
    catch(error){event.target.value='';$('#photoPreview').innerHTML='';toast('Choose another photograph.',error.message);}
  }
});
$('#mobileMenu').addEventListener('click',()=>{$('#sidebar').classList.add('open');$('#navShade').hidden=false;});
$('#navShade').addEventListener('click',closeNav);
$('#closeModal').addEventListener('click',()=>{if(!state.busy)closeModal();});
$('#modalBackdrop').addEventListener('click',event=>{if(event.target===$('#modalBackdrop')&&!state.busy)closeModal();});
$('#refreshButton').addEventListener('click',async()=>{if(state.busy)return;try{await loadData({renderPage:!['report','profile'].includes(state.view)});toast('You’re up to date.');}catch(error){toast('Couldn’t refresh.',error.message);}});
document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&!state.busy){closeModal();closeNav();}
  if(event.key==='Tab'&&!$('#modalBackdrop').hidden){const fields=$$('button:not([disabled]),a[href],input,select,textarea',$('#modal'));const first=fields[0],last=fields.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}
});
window.addEventListener('popstate',()=>{if(!state.user)return;const [view,id]=location.hash.slice(1).split('/');if(view==='match'&&id)viewMatch(Number(id)).catch(error=>toast('Match unavailable.',error.message));else navigate(view||'home',false);});
setInterval(()=>{if(state.user&&!state.busy&&!document.hidden&&$('#modalBackdrop').hidden&&!['report','profile'].includes(state.view)&&!document.activeElement?.matches('input,textarea,select'))loadData().catch(error=>{if(state.user){$('#connectionNotice').textContent=error.message;$('#connectionNotice').hidden=false;}});},15000);
(async()=>{try{const config=await api('/config');if(config.demo_mode)$('.auth-foot').textContent='Demonstration mode · Synthetic campus accounts and reports. See DEMO_GUIDE.md for test logins.';await enterApp();}catch(error){showAuth();if(!error.message.toLowerCase().includes('log in')){$('#loginError').textContent=error.message;$('#loginError').hidden=false;}}})();
