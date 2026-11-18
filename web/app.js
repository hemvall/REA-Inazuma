const $ = id => document.getElementById(id);
let session=null,revision=0,running=false,busy=false,owner='human',jobRunning=false,fixture=null,lastJob='',lastImage='',polling=false;
let videoSession=null;
function attachVideo(){
  if(!session||videoSession===session)return;
  videoSession=session;
  $('frame').src=$('topFrame').src='/video?session='+encodeURIComponent(session);
  $('frame').hidden=false;$('empty').hidden=true;setScreenVisible(true);
}
let profile=null,enteringClub=false;
const keyboardDirections=new Set(),pendingKeys=new Set(),pointerDirections=new Map();
let walkingTouch=null;
function releaseInputs(){keyboardDirections.clear();pendingKeys.clear();pointerDirections.clear();walkingTouch=null;for(const b of $('keys').querySelectorAll('[data-key]'))b.setAttribute('aria-pressed','false');}
window.addEventListener('blur',releaseInputs);
document.addEventListener('visibilitychange',()=>{if(document.hidden)releaseInputs();});
const teams={1:{name:'Raimon',captain:'Mark',code:'RAI',emblem:'ball'},2:{name:'Royal Academy',captain:'Joseph King',code:'ROY',emblem:'ball'},3:{name:'Occulte',captain:'Talisman',code:'OCC',emblem:'occult'},10:{name:'Zeus',captain:'Aphrodite',code:'ZEU',emblem:'zeus'}};
async function api(op,data={}) {
  const response=await fetch('/api/'+op,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await response.json();
  if(!response.ok||result.error)throw new Error(result.reason||result.error);
  return result;
}
function message(text,kind='answer'){const p=document.createElement('p');p.className=kind;p.textContent=text;$('messages').append(p);$('messages').scrollTop=$('messages').scrollHeight;}
function updateTeamPreview(){
  for(const side of ['home','away']){
    const id=Number($(side).value),team=teams[id];
    $(side+'Captain').textContent='Capitaine · '+team.captain;
    $(side+'Code').textContent=team.code;
    $(side+'Emblem').querySelector('use').setAttribute('href','#icon-'+team.emblem);
    $(side).closest('.team-tile').dataset.team=String(id);
  }
}
function setScreenVisible(visible){
  $('gameScreen').classList.toggle('is-live',visible);
  $('stadiumStage').classList.toggle('is-live',visible);
  $('screenMode').textContent=visible?'ÉCRANS DS · EN DIRECT':'ARÈNE EN ATTENTE';
  $('dsShell').hidden=!visible;
  if(!visible){$('frame').hidden=true;$('empty').hidden=false;lastImage='';videoSession=null;$('frame').removeAttribute('src');$('topFrame').removeAttribute('src');}
}
$('swapTeams').onclick=()=>{const previous=$('home').value;$('home').value=$('away').value;$('away').value=previous;updateTeamPreview();};
for(const side of ['home','away'])$(side).onchange=()=>{
  const other=side==='home'?'away':'home';
  if($(side).value===$(other).value)$(other).value=$(side).value==='3'?'10':'3';
  updateTeamPreview();
};
updateTeamPreview();
function show(result){
  if(!result)return;
  if(Number.isInteger(result.revision))revision=result.revision;
  attachVideo();
  const phase=result.match?.phase;
  const names={club:'Local du club',choosing:'Choix du match',idle:'Au salon',starting:'Démarrage',dialogue:'Dialogue des capitaines',playing:'Rencontre en cours',result:'Résultat',loading:'Chargement'};
  $('status').textContent=owner==='agent'?'Contrôle agent':(names[phase]||'En pause')+(running?'':' · pause');
}
function controls(){
  $('agentBackend').disabled=jobRunning;
  for(const id of ['home','away','swapTeams'])$(id).disabled=jobRunning||profile==='club';
  $('enterClub').disabled=jobRunning||!!session;
  $('reset').textContent=profile==='club'?'Retour au local':'Nouvelle rencontre';
  $('stadiumStage').classList.toggle('is-preparing',jobRunning&&!session);
  const manual=!!session&&owner==='human'&&!jobRunning;
  if(!manual||window.currentPhase==='result')releaseInputs();
  $('start').disabled=!manual||!fixture||!['idle'].includes(window.currentPhase);
  $('delegate').disabled=!manual||!fixture||window.currentPhase==='result';
  $('play').disabled=!manual||window.currentPhase==='result';
  if(window.currentPhase==='result'){running=false;$('play').textContent='Continuer';}
  $('reset').disabled=!manual;
  $('close').disabled=!manual;
  $('external').disabled=!manual;
  $('stop').disabled=!jobRunning&&owner!=='agent';
  $('stop').textContent=jobRunning&&owner==='human'?'Annuler':'Reprendre la main';
  $('send').disabled=$('manualPrepare').disabled=jobRunning||profile==='club';
  for(const b of $('keys').querySelectorAll('button'))b.disabled=!manual;
}
async function mutate(op,data={}){
  if(busy)return;
  busy=true;$('error').textContent='';
  try{const result=await api(op,{session_id:session,revision,...data});show(result);if(result.match){window.currentPhase=result.match.phase;if(JSON.stringify(result.match.fixture)!==JSON.stringify(fixture))renderFixture(result.match.fixture);}return result;}
  catch(error){running=false;$('play').textContent='Continuer';$('error').textContent=error.message;}
  finally{busy=false;controls();}
}
async function step(keys=[],touch=null,frames=2,continuous=false){if(!session||owner!=='human'||jobRunning)return;return mutate('step',{frames,keys,touch,continuous});}
function renderFixture(value){
  fixture=value;$('fixture').hidden=!value;if(!value)return;
  $('home').value=String(value.home);$('away').value=String(value.away);updateTeamPreview();
  $('fixtureTitle').textContent=teams[value.home].name+' contre '+teams[value.away].name;
  $('captains').textContent=teams[value.home].captain+' · '+teams[value.away].captain;
  $('dialogues').replaceChildren();value.lines.forEach((line,index)=>{const li=document.createElement('li');li.textContent=teams[index%2?value.away:value.home].captain+' : '+line;$('dialogues').append(li);});
}
async function poll(){
  if(polling||busy)return;polling=true;
  try{
    const state=await api('status');session=state.session_id;profile=state.profile;owner=state.owner;jobRunning=state.job.state==='running';
    if(!session){setScreenVisible(false);$('status').textContent=jobRunning?'PRÉPARATION…':'EN ATTENTE';}
    $('job').textContent=state.job.message;
    if(state.fixture&&JSON.stringify(state.fixture)!==JSON.stringify(fixture))renderFixture(state.fixture);
    if(!state.fixture&&fixture)renderFixture(null);
    show(state.observation);window.currentPhase=state.observation?.match?.phase;
    if(state.job.id&&lastJob!==state.job.id+state.job.state&&state.job.state!=='running'){
      lastJob=state.job.id+state.job.state;message(state.job.message);if(state.job.state==='error')$('error').textContent=state.job.message;
    }
    controls();
    if(enteringClub&&!jobRunning){enteringClub=false;if(session&&profile==='club'){running=true;$('play').textContent='Pause';}}
  }catch(error){$('error').textContent='Connexion au serveur interrompue : '+error.message;running=false;}
  finally{polling=false;}
}
setInterval(poll,650);poll();
function showBackend(backend){
  $('agentBackend').value=backend;
  $('agentNote').textContent=backend==='local'
    ?'Sur ton PC, avec LM Studio et qwen/qwen3.5-9b. Aucun compte requis. Le jeu attend les décisions.'
    :'Codex CLI : installation et compte connecté requis. Le jeu attend les décisions.';
}
let selectedBackend='local';
api('capabilities').then(value=>{selectedBackend=value.agent_backend;showBackend(selectedBackend);}).catch(error=>{$('error').textContent=error.message;});
$('agentBackend').onchange=async()=>{
  const requested=$('agentBackend').value;
  $('agentBackend').disabled=true;
  try{const value=await api('select_agent',{backend:requested});selectedBackend=value.agent_backend;showBackend(selectedBackend);}
  catch(error){showBackend(selectedBackend);$('error').textContent=error.message;}
  finally{controls();}
};
// The worker runs the DS clock. HTTP commands only change playback or input;
// the persistent MJPEG connection delivers the latest frames independently.
async function playback(value){
  const result=await mutate('playback',{running:value,include_image:false});
  if(result){running=value;$('play').textContent=running?'Pause':'Continuer';}
  return result;
}
async function pumpInputs(){
  const started=performance.now();
  if(!busy&&!polling&&(keyboardDirections.size||pointerDirections.size||pendingKeys.size||walkingTouch)){
    const keys=[...new Set([...keyboardDirections,...pointerDirections.values(),...pendingKeys])];pendingKeys.clear();
    await step(keys,walkingTouch,keys.length||walkingTouch?6:2,keyboardDirections.size>0||pointerDirections.size>0||!!walkingTouch);
  }
  setTimeout(pumpInputs,Math.max(0,1000/30-(performance.now()-started)));
}
pumpInputs();
$('enterClub').onclick=async()=>{
  $('error').textContent='';
  try{await api('open_club');enteringClub=true;jobRunning=true;controls();await poll();}
  catch(error){$('error').textContent=error.message;enteringClub=false;}
};
$('chat').onsubmit=async event=>{
  event.preventDefault();running=false;const text=$('prompt').value.trim();if(!text)return;
  message(text,'question');$('prompt').value='';$('error').textContent='';
  try{await api('chat',{message:text});jobRunning=true;controls();await poll();}catch(error){$('error').textContent=error.message;}
};
$('manual').onsubmit=async event=>{
  event.preventDefault();running=false;const home=Number($('home').value),away=Number($('away').value);
  if(home===away){$('error').textContent='Choisissez deux équipes différentes.';return;}
  const lines=[`${teams[home].name} est pret. Et vous ?`,`${teams[away].name} releve le defi !`,
    'On donnera tout, ensemble.','Alors montrez-nous votre football !',
    'Que le meilleur gagne !','En place. Le match commence !'];
  try{await api('prepare_match',{home,away,lines});jobRunning=true;controls();await poll();}catch(error){$('error').textContent=error.message;}
};
$('start').onclick=async()=>{if(await mutate('start_match'))await playback(true);};
$('play').onclick=()=>playback(!running);
$('delegate').onclick=async()=>{running=false;$('play').textContent='Continuer';try{await api('delegate_player',{session_id:session});jobRunning=true;controls();}catch(error){$('error').textContent=error.message;}};
$('stop').onclick=async()=>{running=false;$('play').textContent='Continuer';try{await api('stop_agent');await poll();}catch(error){$('error').textContent=error.message;}};
$('external').onclick=async()=>{running=false;try{await api('set_control',{session_id:session,owner:'agent'});await poll();}catch(error){$('error').textContent=error.message;}};
$('reset').onclick=async()=>{await playback(false);await mutate('reset_match');renderFixture(null);await poll();};
$('close').onclick=async()=>{running=false;const result=await mutate('session_close');if(result){session=null;renderFixture(null);setScreenVisible(false);$('status').textContent='Session fermée';}await poll();};
const directionKeys={ArrowUp:'UP',ArrowDown:'DOWN',ArrowLeft:'LEFT',ArrowRight:'RIGHT',z:'UP',q:'LEFT',s:'DOWN',d:'RIGHT'};
const actionKeys={a:'A',b:'B',x:'X',y:'Y',Enter:'START'};
document.addEventListener('keydown',event=>{
  if(['INPUT','SELECT','TEXTAREA'].includes(event.target.tagName)||event.ctrlKey||event.metaKey||event.altKey)return;
  if(event.key==='Enter'&&event.target.tagName==='BUTTON')return;
  const key=directionKeys[event.key]||actionKeys[event.key];
  if(key&&session&&owner==='human'&&!jobRunning){event.preventDefault();if(directionKeys[event.key])keyboardDirections.add(key);else if(!event.repeat)pendingKeys.add(key);}
});
document.addEventListener('keyup',event=>{const key=directionKeys[event.key];if(key)keyboardDirections.delete(key);});
$('keys').onpointerdown=event=>{
  const button=event.target.closest('[data-key]');if(!button||button.disabled)return;
  event.preventDefault();button.focus();const key=button.dataset.key;
  if(['UP','DOWN','LEFT','RIGHT'].includes(key)){pointerDirections.set(event.pointerId,key);button.setPointerCapture(event.pointerId);button.setAttribute('aria-pressed','true');}
  else pendingKeys.add(key);
};
function releasePointer(event){const key=pointerDirections.get(event.pointerId);pointerDirections.delete(event.pointerId);if(key)$('keys').querySelector('[data-key="'+key+'"]').setAttribute('aria-pressed','false');}
$('keys').onpointerup=$('keys').onpointercancel=$('keys').onlostpointercapture=releasePointer;
$('keys').onclick=event=>{if(event.detail===0&&event.target.dataset.key)pendingKeys.add(event.target.dataset.key);};
let path=[],drawingWasRunning=false;
function point(event){const r=$('frame').getBoundingClientRect();const x=Math.floor((event.clientX-r.left)*256/r.width),y=Math.floor((event.clientY-r.top)*384/r.height)-192;return x>=0&&x<256&&y>=0&&y<192?{x,y,frames:2}:null;}
$('frame').onpointerdown=event=>{if(owner!=='human'||jobRunning)return;const p=point(event);if(!p)return;event.preventDefault();if(window.currentPhase==='club'){walkingTouch=[p.x,p.y];$('frame').setPointerCapture(event.pointerId);return;}if(busy)return;drawingWasRunning=running;path=[p];$('frame').setPointerCapture(event.pointerId);if(running)playback(false);};
$('frame').onpointermove=event=>{if(walkingTouch){const p=point(event);if(p)walkingTouch=[p.x,p.y];return;}if(!path.length)return;const p=point(event);if(p&&path.length<50&&(p.x!==path.at(-1).x||p.y!==path.at(-1).y))path.push(p);};
$('frame').onpointerup=async()=>{if(walkingTouch){walkingTouch=null;return;}if(!path.length)return;const points=path;path=[];while(busy)await new Promise(resolve=>setTimeout(resolve,5));const result=points.length===1?await step([],[points[0].x,points[0].y],6):await mutate('touch_path',{points});if(result&&drawingWasRunning)await playback(true);};
$('frame').onpointercancel=()=>{if(walkingTouch){walkingTouch=null;return;}path=[];if(drawingWasRunning)playback(true);};
