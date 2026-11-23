import {createChester} from './chester.js';

const $ = id => document.getElementById(id);
const isClubRoute = value => value === 'club_web' || value === 'club_native';
const pilotMode = $('pilotMode');
const arena = $('matchArena');
const fullscreenButton = $('arenaFullscreen');

if (document.fullscreenEnabled && arena.requestFullscreen) {
  fullscreenButton.hidden = false;
  fullscreenButton.onclick = async () => {
    try {
      if (document.fullscreenElement === arena) {
        await document.exitFullscreen();
      } else {
        await arena.requestFullscreen();
      }
    } catch {
      $('error').textContent = 'Impossible de basculer en plein écran.';
    }
  };
  document.addEventListener('fullscreenchange', () => {
    const label = document.fullscreenElement === arena ? 'Quitter le plein écran' : 'Plein écran';
    fullscreenButton.setAttribute('aria-label', label);
    fullscreenButton.title = label;
  });
}

let session=null,revision=0,running=false,busy=false,owner='human',jobRunning=false,fixture=null,lastJob='',lastImage='',polling=false;
let videoSession=null;
function attachVideo(){
  if(!session||videoSession===session)return;
  videoSession=session;
  $('frame').src=$('topFrame').src='/video?session='+encodeURIComponent(session);
  $('frame').hidden=false;$('empty').hidden=true;setScreenVisible(true);
}
let profile=null;
let recruitment=null;
const keyboardDirections=new Set(),pendingKeys=new Set(),pointerDirections=new Map();
let walkingTouch=null;
let stylusPointer=null,path=[];
function releaseInputs(){keyboardDirections.clear();pendingKeys.clear();pointerDirections.clear();clearStylus();for(const b of $('keys').querySelectorAll('[data-key]'))b.removeAttribute('data-held');}
window.addEventListener('blur',releaseInputs);
document.addEventListener('visibilitychange',()=>{if(document.hidden)releaseInputs();});
const teams={
  1:{name:'Raimon',captain:'Mark',portrait:'mark',code:'RAI',emblem:'raimon'},
  2:{name:'Royal Academy',captain:'Joseph King',portrait:'king',code:'ROY',emblem:'royal'},
  3:{name:'Occulte',captain:'Talisman',portrait:'talisman',code:'OCC',emblem:'occult'},
  10:{name:'Zeus',captain:'Aphrodite',portrait:'aphrodite',code:'ZEU',emblem:'zeus'},
  33:{name:'Genesis',captain:'Xene',portrait:'xene',code:'GEN',emblem:'genesis'},
  41:{name:'Empereurs noirs',captain:'Nathan Swift',portrait:'nathan-dark',code:'EMP',emblem:'dark-emperors'},
};
const chester = createChester({
  api, mode: $('chesterMode'), enabled: $('chesterEnabled'), captions: $('chesterCaptions'),
  volume: $('chesterVolume'), line: $('chesterLine'), hint: $('chesterHint'),
  status: $('chesterStatus'), tool: $('chesterTool'),
});
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
    $(side+'Portrait').src='/assets/captain-'+team.portrait+'.png';
    $(side+'Code').textContent=team.code;
    $(side+'Emblem').src='/assets/team-'+team.emblem+'.png';
    $(side).closest('.team-tile').dataset.team=String(id);
  }
}
function setScreenVisible(visible){
  $('gameScreen').classList.toggle('is-live',visible);
  $('stadiumStage').classList.toggle('is-live',visible);
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
  chester.observe(session, result?.commentary);
  if(!result)return;
  if(isClubRoute(profile)&&['club','route'].includes(result.match?.phase)&&
     !['club','route'].includes(window.currentPhase)){
    running=true;
    $('play').textContent='Pause';
  }
  if(isClubRoute(profile)&&result.match?.phase==='route'){
    $('job').textContent='Choisis un écusson sur l’écran tactile de la DS.';
  }
  if(Number.isInteger(result.revision))revision=result.revision;
  attachVideo();
}
function controls(){
  const clubRoute=!!session&&isClubRoute(profile);
  const routeBoard=clubRoute&&!fixture;
  arena.parentElement.classList.toggle('is-club-route',clubRoute);
  $('manual').hidden=clubRoute;
  $('matchSetup').hidden=clubRoute;
  $('recruitmentColumn').hidden=clubRoute;
  arena.querySelector('.chester-dialogue').hidden=routeBoard;
  arena.querySelector('.chester-controls').hidden=routeBoard;
  for(const id of ['home','away','swapTeams'])$(id).disabled=jobRunning||clubRoute||profile==='club';
  $('enterClub').disabled=jobRunning||!!session;
  $('reset').textContent=clubRoute?'Retour à la route':profile==='club'?'Retour au local':'Nouvelle rencontre';
  $('reset').hidden=routeBoard;
  $('stadiumStage').classList.toggle('is-preparing',jobRunning&&!session);
  const manual=!!session&&owner==='human'&&!jobRunning;
  if(!manual||window.currentPhase==='result')releaseInputs();
  const finished=window.currentPhase==='result';
  const canStart=manual&&!!fixture&&window.currentPhase==='idle';
  $('start').hidden=!canStart;
  $('play').hidden=!manual||canStart||finished||routeBoard;
  $('stop').hidden=!jobRunning&&owner!=='agent';
  $('pilotControls').hidden=!manual||!fixture||finished;
  $('arenaOptions').hidden=!manual;
  if(!manual)$('arenaOptions').open=false;
  if(finished){running=false;$('play').textContent='Continuer';}
  $('stop').textContent=jobRunning&&owner==='human'?'Annuler':'Reprendre la main';
  $('send').disabled=$('manualPrepare').disabled=jobRunning||clubRoute||profile==='club';
  for(const button of $('recruitmentPanel').querySelectorAll('button')){
    button.disabled=busy||jobRunning||!recruitmentAvailable();
  }
  for(const b of $('keys').querySelectorAll('button'))b.disabled=!manual;
}
function recruitmentAvailable() {
  if(!session)return true;
  if(owner!=='human')return false;
  return profile==='club' ? window.currentPhase==='club'
    : profile==='arena'&&['idle','result'].includes(window.currentPhase);
}
function renderRecruitment(state) {
  recruitment=state.recruitment;
  const confirmed=state.recruited_players||[];
  const capacity=$('recruitmentCapacity');
  capacity.textContent=confirmed.length
    ? confirmed.map(player=>`${teams[player.team_id].name} a recruté ${player.name} · Niveau ${player.level}`).join('\n')
    : recruitmentAvailable() ? 'Aucune recrue inscrite'
    : 'Recrutement disponible hors match';
  const draft=recruitment?.result ? null : recruitment?.draft;
  $('recruitmentHint').textContent='Disponible au prochain match préparé en arène.';
  $('recruitmentCancel').hidden=!recruitment||!!recruitment.result;
  $('recruitmentPreview').hidden=!draft;
  if(draft){
    $('recruitmentSheet').textContent=`${teams[draft.team_id].name} peut recruter ${draft.name} · Niveau ${draft.level}`;
  }
  const history=$('recruitmentHistory');
  if(history.dataset.version!==(recruitment?.version||'')){
    history.dataset.version=recruitment?.version||'';
    history.replaceChildren(...(recruitment?.history||[]).map(entry=>{
      const line=document.createElement('p');
      const speaker=entry.role==='joueur'?'Toi':'Celia';
      line.textContent=`${speaker} · ${entry.message}`;
      return line;
    }));
  }
}
async function recruitmentAction(operation, data={}) {
  if(busy||jobRunning||!recruitmentAvailable())return;
  $('recruitmentError').textContent='';
  releaseInputs();
  busy=true;
  controls();
  try {
    const result=await api(operation,{session_id:session,...data});
    if(result.job)jobRunning=true;
    if(result.observation)show(result.observation);
    return result;
  } catch(error) {
    $('recruitmentError').textContent=error.message;
  } finally {
    busy=false;
    controls();
    await poll();
  }
}
$('recruitmentChat').onsubmit=async event=>{
  event.preventDefault();
  const field=$('recruitmentPrompt');
  if(await recruitmentAction('recruitment_turn',{message:field.value}))field.value='';
};
$('recruitmentCancel').onclick=()=>recruitmentAction('recruitment_cancel');
$('recruitmentConfirm').onclick=()=>{
  if(recruitment)recruitmentAction('recruitment_confirm',{version:recruitment.version,revision});
};
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
    if(!session)setScreenVisible(false);
    $('job').textContent=state.job.message;
    if(state.fixture&&JSON.stringify(state.fixture)!==JSON.stringify(fixture))renderFixture(state.fixture);
    if(!state.fixture&&fixture)renderFixture(null);
    show(state.observation);window.currentPhase=state.observation?.match?.phase;
    renderRecruitment(state);
    if(state.job.id&&lastJob!==state.job.id+state.job.state&&state.job.state!=='running'){
      lastJob=state.job.id+state.job.state;message(state.job.message);if(state.job.state==='error')$('error').textContent=state.job.message;
    }
    controls();
  }catch(error){$('error').textContent='Connexion au serveur interrompue : '+error.message;running=false;chester.observe(null);}
  finally{polling=false;}
}
setInterval(poll,650);poll();
// The worker runs the DS clock. HTTP commands only change playback or input;
// the persistent MJPEG connection delivers the latest frames independently.
async function playback(value){
  if(!value)chester.pause(true);
  const result=await mutate('playback',{running:value,include_image:false});
  if(result){chester.pause(!value);running=value;$('play').textContent=running?'Pause':'Continuer';}
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
  try{await api('open_club_route');jobRunning=true;controls();await poll();}
  catch(error){$('error').textContent=error.message;}
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
$('arenaOptions').addEventListener('click',event=>{
  if(!event.target.closest('button'))return;
  $('arenaOptions').open=false;
  $('arenaOptions').querySelector('summary').focus();
});
$('delegate').onclick=async()=>{running=false;$('play').textContent='Continuer';try{await api('delegate_player',{session_id:session,mode:pilotMode.value});chester.pause(false);jobRunning=true;controls();}catch(error){$('error').textContent=error.message;}};
$('stop').onclick=async()=>{running=false;$('play').textContent='Continuer';try{await api('stop_agent',session?{session_id:session}:{});chester.pause(true);await poll();}catch(error){$('error').textContent=error.message;}};
$('reset').onclick=async()=>{await playback(false);await mutate('reset_match');chester.pause(false);renderFixture(null);await poll();};
$('close').onclick=async()=>{running=false;const result=await mutate('session_close');if(result){session=null;chester.observe(null);renderFixture(null);setScreenVisible(false);}await poll();};
const directionKeys={ArrowUp:'UP',ArrowDown:'DOWN',ArrowLeft:'LEFT',ArrowRight:'RIGHT',z:'UP',q:'LEFT',s:'DOWN',d:'RIGHT'};
const actionKeys={a:'A',b:'B',x:'X',y:'Y',Enter:'START'};
document.addEventListener('keydown',event=>{
  if(document.getElementById('club-window').open)return;
  if(['INPUT','SELECT','TEXTAREA'].includes(event.target.tagName)||event.ctrlKey||event.metaKey||event.altKey)return;
  if(event.key==='Enter'&&event.target.tagName==='BUTTON')return;
  const key=directionKeys[event.key]||actionKeys[event.key];
  if(key&&session&&owner==='human'&&!jobRunning){event.preventDefault();if(directionKeys[event.key])keyboardDirections.add(key);else if(!event.repeat)pendingKeys.add(key);}
});
document.addEventListener('keyup',event=>{const key=directionKeys[event.key];if(key)keyboardDirections.delete(key);});
$('keys').onpointerdown=event=>{
  const button=event.target.closest('[data-key]');if(!button||button.disabled||event.button!==0)return;
  event.preventDefault();button.focus({preventScroll:true});const key=button.dataset.key;
  pendingKeys.add(key);
  if(button.closest('.ds-cross')){
    pointerDirections.set(event.pointerId,key);
    button.setPointerCapture(event.pointerId);
    button.setAttribute('data-held','');
  }
};
function releasePointer(event){
  const key=pointerDirections.get(event.pointerId);
  pointerDirections.delete(event.pointerId);
  if(key&&![...pointerDirections.values()].includes(key)){
    $('keys').querySelector('[data-key="'+key+'"]').removeAttribute('data-held');
  }
}
$('keys').onpointerup=$('keys').onpointercancel=$('keys').onlostpointercapture=releasePointer;
$('keys').onclick=event=>{
  const button=event.target.closest('[data-key]');
  if(event.detail===0&&button&&!button.disabled)pendingKeys.add(button.dataset.key);
};
function point(event){const r=$('frame').getBoundingClientRect();const x=Math.floor((event.clientX-r.left)*256/r.width),y=Math.floor((event.clientY-r.top)*384/r.height)-192;return x>=0&&x<256&&y>=0&&y<192?{x,y,frames:2}:null;}
function clearStylus(){
  stylusPointer=null;
  walkingTouch=null;
  path=[];
}
$('frame').onpointerdown=event=>{
  if(!session||owner!=='human'||jobRunning||stylusPointer!==null||event.button!==0)return;
  const p=point(event);
  if(!p)return;
  event.preventDefault();
  stylusPointer=event.pointerId;
  $('frame').setPointerCapture(event.pointerId);
  if(window.currentPhase==='club')walkingTouch=[p.x,p.y];
  else path=[p];
};
$('frame').onpointermove=event=>{
  if(event.pointerId!==stylusPointer)return;
  const p=point(event);
  if(!p)return;
  if(walkingTouch)walkingTouch=[p.x,p.y];
  else if(path.length<50&&(p.x!==path.at(-1).x||p.y!==path.at(-1).y))path.push(p);
};
$('frame').onpointerup=async event=>{
  if(event.pointerId!==stylusPointer)return;
  const points=path;
  const inputSession=session;
  clearStylus();
  if(!points.length)return;
  while(busy||polling)await new Promise(resolve=>setTimeout(resolve,5));
  if(!session||session!==inputSession||owner!=='human'||jobRunning)return;
  if(points.length===1)await step([],[points[0].x,points[0].y],6);
  else await mutate('touch_path',{points});
};
$('frame').onpointercancel=$('frame').onlostpointercapture=event=>{
  if(event.pointerId===stylusPointer)clearStylus();
};
