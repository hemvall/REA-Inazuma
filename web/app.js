const $ = id => document.getElementById(id);
let session=null,revision=0,running=false,busy=false,owner='human',jobRunning=false,fixture=null,lastJob='',lastImage='',polling=false;
const teams={3:{name:'Occulte',captain:'Talisman'},10:{name:'Zeus',captain:'Aphrodite'}};
async function api(op,data={}) {
  const response=await fetch('/api/'+op,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await response.json();
  if(!response.ok||result.error)throw new Error(result.reason||result.error);
  return result;
}
function message(text,kind='answer'){const p=document.createElement('p');p.className=kind;p.textContent=text;$('messages').append(p);p.scrollIntoView({block:'nearest'});}
function show(result){
  if(!result)return;
  if(Number.isInteger(result.revision))revision=result.revision;
  if(result.image&&result.image!==lastImage){lastImage=result.image;$('frame').src='data:image/png;base64,'+result.image;$('frame').hidden=false;$('empty').hidden=true;}
  const phase=result.match?.phase;
  const names={idle:'Au salon',starting:'Démarrage',dialogue:'Dialogue des capitaines',playing:'Rencontre en cours',result:'Résultat',loading:'Chargement'};
  $('status').textContent=owner==='agent'?'Contrôle agent':(names[phase]||'En pause')+(running?'':' · pause');
}
function controls(){
  const manual=!!session&&owner==='human'&&!jobRunning;
  $('start').disabled=!manual||!fixture||!['idle'].includes(window.currentPhase);
  $('delegate').disabled=!manual||!fixture;
  $('play').disabled=!manual;
  $('reset').disabled=!manual;
  $('close').disabled=!manual;
  $('external').disabled=!manual;
  $('stop').disabled=!jobRunning&&owner!=='agent';
  $('stop').textContent=jobRunning&&owner==='human'?'Annuler':'Reprendre la main';
  $('send').disabled=$('manualPrepare').disabled=jobRunning;
  for(const b of $('keys').querySelectorAll('button'))b.disabled=!manual;
}
async function mutate(op,data={}){
  if(busy)return;
  busy=true;$('error').textContent='';
  try{const result=await api(op,{session_id:session,revision,...data});show(result);if(result.match)window.currentPhase=result.match.phase;return result;}
  catch(error){running=false;$('play').textContent='Continuer';$('error').textContent=error.message;}
  finally{busy=false;controls();}
}
async function step(keys=[],touch=null,frames=30){if(!session||owner!=='human'||jobRunning)return;return mutate('step',{frames,keys,touch});}
function renderFixture(value){
  fixture=value;$('fixture').hidden=!value;if(!value)return;
  $('fixtureTitle').textContent=teams[value.home].name+' contre '+teams[value.away].name;
  $('captains').textContent=teams[value.home].captain+' · '+teams[value.away].captain;
  $('dialogues').replaceChildren();value.lines.forEach((line,index)=>{const li=document.createElement('li');li.textContent=teams[index%2?value.away:value.home].captain+' : '+line;$('dialogues').append(li);});
}
async function poll(){
  if(polling||busy)return;polling=true;
  try{
    const state=await api('status');session=state.session_id;owner=state.owner;jobRunning=state.job.state==='running';
    $('job').textContent=state.job.message;
    if(state.fixture&&JSON.stringify(state.fixture)!==JSON.stringify(fixture))renderFixture(state.fixture);
    if(!state.fixture&&fixture)renderFixture(null);
    show(state.observation);window.currentPhase=state.observation?.match?.phase;
    if(state.job.id&&lastJob!==state.job.id+state.job.state&&state.job.state!=='running'){
      lastJob=state.job.id+state.job.state;message(state.job.message);if(state.job.state==='error')$('error').textContent=state.job.message;
    }
    controls();
  }catch(error){$('error').textContent='Connexion au serveur interrompue : '+error.message;running=false;}
  finally{polling=false;}
}
setInterval(poll,650);poll();
setInterval(()=>{if(running&&!busy&&!polling)step();},100);
$('chat').onsubmit=async event=>{
  event.preventDefault();running=false;const text=$('prompt').value.trim();if(!text)return;
  message(text,'question');$('prompt').value='';$('error').textContent='';
  try{await api('chat',{message:text});jobRunning=true;controls();await poll();}catch(error){$('error').textContent=error.message;}
};
$('manual').onsubmit=async event=>{
  event.preventDefault();running=false;const home=Number($('home').value),away=Number($('away').value);
  if(home===away){$('error').textContent='Choisissez deux équipes différentes.';return;}
  const lines=[`Bienvenue. ${teams[home].name} est pret pour ce match.`,`Face a ${teams[away].name}, chaque passe va compter.`,
    'Notre capitaine compte sur toute son equipe.','Alors montrez-nous votre meilleur football.',
    'Le ballon et le terrain vont nous departager.','En place. Que le meilleur gagne !'];
  try{await api('prepare_match',{home,away,lines});jobRunning=true;controls();await poll();}catch(error){$('error').textContent=error.message;}
};
$('start').onclick=async()=>{if(await mutate('start_match')){running=true;$('play').textContent='Pause';}};
$('play').onclick=()=>{running=!running;$('play').textContent=running?'Pause':'Continuer';};
$('delegate').onclick=async()=>{running=false;$('play').textContent='Continuer';try{await api('delegate_player',{session_id:session});jobRunning=true;controls();}catch(error){$('error').textContent=error.message;}};
$('stop').onclick=async()=>{running=false;$('play').textContent='Continuer';try{await api('stop_agent');await poll();}catch(error){$('error').textContent=error.message;}};
$('external').onclick=async()=>{running=false;try{await api('set_control',{session_id:session,owner:'agent'});await poll();}catch(error){$('error').textContent=error.message;}};
$('reset').onclick=async()=>{running=false;$('play').textContent='Continuer';await mutate('reset_match');renderFixture(null);await poll();};
$('close').onclick=async()=>{running=false;const result=await mutate('session_close');if(result){session=null;renderFixture(null);$('frame').hidden=true;$('empty').hidden=false;lastImage='';$('status').textContent='Session fermée';}await poll();};
$('keys').onclick=event=>{if(event.target.dataset.key)step([event.target.dataset.key],null,6);};
document.addEventListener('keydown',event=>{if(['INPUT','SELECT','BUTTON','TEXTAREA'].includes(event.target.tagName))return;
  const key={ArrowUp:'UP',ArrowDown:'DOWN',ArrowLeft:'LEFT',ArrowRight:'RIGHT',a:'A',b:'B',x:'X',y:'Y',Enter:'START'}[event.key];if(key&&session){event.preventDefault();step([key],null,6);}});
let path=[],drawingWasRunning=false;
function point(event){const r=$('frame').getBoundingClientRect();const x=Math.floor((event.clientX-r.left)*256/r.width),y=Math.floor((event.clientY-r.top)*384/r.height)-192;return x>=0&&x<256&&y>=0&&y<192?{x,y,frames:2}:null;}
$('frame').onpointerdown=event=>{if(owner!=='human'||jobRunning||busy)return;const p=point(event);if(!p)return;event.preventDefault();drawingWasRunning=running;running=false;path=[p];$('frame').setPointerCapture(event.pointerId);};
$('frame').onpointermove=event=>{if(!path.length)return;const p=point(event);if(p&&path.length<50&&(p.x!==path.at(-1).x||p.y!==path.at(-1).y))path.push(p);};
$('frame').onpointerup=async()=>{if(!path.length)return;const points=path;path=[];const result=points.length===1?await step([],[points[0].x,points[0].y],6):await mutate('touch_path',{points});running=!!result&&drawingWasRunning;};
$('frame').onpointercancel=()=>{path=[];running=drawingWasRunning;};
