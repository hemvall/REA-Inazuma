const STORAGE = 'inazuma-fc:v1';
const STARTING_CREDITS = 3800;
const slots = ['AT', 'AT', 'MIL', 'MIL', 'MIL', 'MIL', 'DEF', 'DEF', 'DEF', 'DEF', 'GB',
  'Banc', 'Banc', 'Banc', 'Banc', 'Banc'];
const scouts = [
  ["Monty Hillary", 'AT', "https://dxi4wb638ujep.cloudfront.net/1/k/o/c/ocbppldxgwu.png"],
  ["Penfold Pulper", 'AT', "https://dxi4wb638ujep.cloudfront.net/1/k/g/q/gqakvkk4b60.png"],
  ["Trey Spotter", 'MIL', "https://dxi4wb638ujep.cloudfront.net/1/k/h/j/hjhhthewqj8.png"],
  ["Ryder Waverly", 'MIL', "https://dxi4wb638ujep.cloudfront.net/1/k/p/o/por5utbna8k.png"],
  ["Ted Larkin", 'MIL', "https://dxi4wb638ujep.cloudfront.net/1/k/k/k/kk-nogtcxce.png"],
  ["Odo Cologne", 'MIL', "https://dxi4wb638ujep.cloudfront.net/1/k/1/j/1jszwc-uppc.png"],
  ["Onslow Ball", 'DEF', "https://dxi4wb638ujep.cloudfront.net/1/k/v/h/vhim9o0fvcu.png"],
  ["Horace Coop", 'DEF', "https://dxi4wb638ujep.cloudfront.net/1/k/8/h/8hdet11byjm.png"],
  ["Ness Lockley", 'DEF', "https://dxi4wb638ujep.cloudfront.net/1/k/c/o/co-x-oathp8.png"],
  ["Olef Tennant", 'DEF', "https://dxi4wb638ujep.cloudfront.net/1/k/t/a/tapqtxmpqau.png"],
  ["Len Scapp", 'GB', "https://dxi4wb638ujep.cloudfront.net/1/k/z/q/zqwiiallnl8.png"],
  ["Leaf Scarlett", 'AT', "https://dxi4wb638ujep.cloudfront.net/1/k/n/v/nvslakthf6k.png"],
  ["Spike Thorne", 'DEF', "https://dxi4wb638ujep.cloudfront.net/1/k/x/t/xtiwrgzkzps.png"],
  ["Rob Ottley", 'MIL', "https://dxi4wb638ujep.cloudfront.net/1/k/9/3/93fqekogpje.png"],
  ["Thomas Cott", 'GB', "https://dxi4wb638ujep.cloudfront.net/1/k/3/c/3crf4bscsjc.png"],
  ["Lincoln Hawking", 'AT', "https://dxi4wb638ujep.cloudfront.net/1/k/m/f/mf5rg5_w0ae.png"],
].map(([name, position, image], index) => ({
  id: `scout-${index + 1}`, name, position, image, rarity: 'Scout', price: 0,
}));
const recruits = [
  {id: 'willy', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/u/y/uy2tfhpjks0.png', name: 'Willy Glasses', position: 'AT', rarity: 'Bronze', price: 180},
  {id: 'steve', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/f/3/f3asqpwqusk.png', name: 'Steve Grim', position: 'MIL', rarity: 'Bronze', price: 220},
  {id: 'tod', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/_/y/_yjndsfyhyu.png', name: 'Tod Ironside', position: 'DEF', rarity: 'Bronze', price: 170},
  {id: 'max', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/r/d/rd_khczyztm.png', name: 'Maxwell Carson', position: 'MIL', rarity: 'Bronze', price: 190},
  {id: 'darren', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/o/y/oy1sibyz7wc.png', name: 'Darren LaChance', position: 'GB', rarity: 'Bronze', price: 200},
  {id: 'jim', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/o/w/owsgutjimb8.png', name: 'Jim Wraith', position: 'DEF', rarity: 'Bronze', price: 210},
  {id: 'erik', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/e/4/e4qtt3lwf_m.png', name: 'Erik Eagle', position: 'MIL', rarity: 'Argent', price: 390},
  {id: 'kevin', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/0/d/0dvmw8cb_ye.png', name: 'Kevin Dragonfly', position: 'AT', rarity: 'Argent', price: 430},
  {id: 'jack', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/m/r/mrvaa0xojh8.png', name: 'Jack Wallside', position: 'DEF', rarity: 'Argent', price: 420},
  {id: 'celia', image: '/assets/celia.png', name: 'Celia Hills', position: 'MIL', rarity: 'Argent', price: 460},
  {id: 'mark', image: '/assets/captain-mark.png', name: 'Mark Evans', position: 'GB', rarity: 'Or', price: 800},
  {id: 'axel', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/f/1/f1kh7d67sbs.png', name: 'Axel Blaze', position: 'AT', rarity: 'Or', price: 850},
  {id: 'nathan', image: '/assets/captain-nathan-dark.png', name: 'Nathan Swift', detail: 'Empereurs noirs', position: 'AT', rarity: 'Légendaire', price: 1500},
  {id: 'xene', image: '/assets/captain-xene.png', name: 'Xene', detail: 'Genesis', position: 'AT', rarity: 'Légendaire', price: 1600},
];
const scoutIds = scouts.map(player => player.id);
const players = new Map([...scouts, ...recruits].map(player => [player.id, player]));
const $ = id => document.getElementById(id);
const picker = $('picker');
const club = $('club-window');
const catalogue = $('recruitment-catalogue');
const formatter = new Intl.NumberFormat('fr-FR');
let activeSlot = null;

function balance(state) {
  return STARTING_CREDITS - state.recruits.reduce((sum, id) => sum + players.get(id).price, 0);
}

function load() {
  const value = JSON.parse(localStorage.getItem(STORAGE) ?? 'null');
  if (value === null) return {recruits: [], lineup: [...scoutIds]};
  if (!Array.isArray(value.recruits) || !Array.isArray(value.lineup)
      || value.recruits.some(id => !recruits.some(player => player.id === id))
      || new Set(value.recruits).size !== value.recruits.length
      || value.lineup.length !== slots.length || new Set(value.lineup).size !== slots.length
      || value.lineup.some(id => !scoutIds.includes(id) && !value.recruits.includes(id))
      || balance(value) < 0) throw new Error('Sauvegarde du club illisible.');
  return value;
}

function feedback(text, error = false) {
  const message = error && picker.open ? $('picker-error')
    : catalogue.open ? $('catalogue-feedback') : $('feedback');
  message.textContent = text;
  message.hidden = false;
  message.classList.toggle('error', error);
}

function update(operation) {
  const apply = () => {
    try {
      const copy = load();
      const message = operation(copy);
      localStorage.setItem(STORAGE, JSON.stringify(copy));
      state = copy;
      render();
      feedback(message);
      return true;
    } catch (error) {
      feedback(error.message || 'La sauvegarde a échoué.', true);
      return false;
    }
  };
  return navigator.locks ? navigator.locks.request(STORAGE, apply) : Promise.resolve(apply());
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

function playerName(player) {
  return player.detail ? `${player.name} · ${player.detail}` : player.name;
}

function portrait(player) {
  const image = node('img', 'club-portrait');
  image.src = player.image;
  image.alt = '';
  image.decoding = 'async';
  image.referrerPolicy = 'no-referrer';
  return image;
}

function slotName(index) {
  return index < 11 ? `Poste ${slots[index]} ${index + 1}` : `Banc ${index - 10}`;
}

function squadSlot(id, index) {
  const player = players.get(id);
  const button = node('button', 'slot');
  button.type = 'button';
  button.dataset.slot = index;
  button.setAttribute('aria-label', `${slotName(index)} — ${playerName(player)}. Changer de joueur`);
  button.title = playerName(player);
  button.dataset.rarity = player.rarity;
  button.append(portrait(player), node('span', 'slot-name', player.name));
  button.onclick = () => {
    activeSlot = index;
    $('picker-error').hidden = true;
    $('picker-title').textContent = slotName(index);
    renderPicker();
    picker.showModal();
  };
  return button;
}

function playerRow(player, info, action) {
  const row = node('li', 'player-row');
  const identity = node('div', 'player-identity');
  const details = node('div', 'player-details');
  details.append(node('strong', '', playerName(player)), node('span', '', info));
  identity.append(portrait(player), details);
  const rarity = node('span', 'rarity', player.rarity);
  rarity.dataset.rarity = player.rarity;
  row.append(identity, rarity);
  if (action) row.append(action);
  return row;
}

function renderShop() {
  if (!catalogue.open) return;
  const filter = $('rarity').value;
  $('shop-list').replaceChildren(...recruits.filter(player => !filter || player.rarity === filter).map(player => {
    const owned = state.recruits.includes(player.id);
    const afford = balance(state) >= player.price;
    const button = node('button', 'purchase', owned ? 'Recruté' : afford ? 'Acheter' : 'Budget insuffisant');
    button.type = 'button';
    button.disabled = owned || !afford;
    button.setAttribute('aria-label', `${button.textContent} — ${playerName(player)}`);
    button.onclick = async () => {
      const focused = document.activeElement === button;
      const saved = await update(copy => {
        if (copy.recruits.includes(player.id)) throw new Error('Ce joueur appartient déjà au club.');
        if (balance(copy) < player.price) throw new Error('Crédits insuffisants.');
        copy.recruits.push(player.id);
        return `Célia confirme le recrutement de ${playerName(player)}. Tu peux retrouver le joueur dans ton inventaire.`;
      });
      if (saved && focused) ($('shop-list').querySelector('button:enabled') ?? $('rarity')).focus();
    };
    return playerRow(player, `${player.position} · ${formatter.format(player.price)} crédits`, button);
  }));
}

function renderPicker() {
  const selecting = activeSlot;
  $('picker-list').replaceChildren(...[...state.recruits, ...scoutIds].map(id => {
    const player = players.get(id);
    const position = state.lineup.indexOf(id);
    const button = node('button', 'choose', position === selecting ? 'Actuel' : 'Choisir');
    button.type = 'button';
    button.disabled = position === selecting;
    button.setAttribute('aria-label', `${button.textContent} — ${playerName(player)}`);
    button.onclick = async () => {
      const saved = await update(copy => {
        const source = copy.lineup.indexOf(id);
        if (source >= 0) copy.lineup[source] = copy.lineup[selecting];
        copy.lineup[selecting] = id;
        return `${player.name} occupe le poste sélectionné.`;
      });
      if (saved) picker.close();
    };
    return playerRow(player, position >= 0 ? slotName(position) : 'En réserve', button);
  }));
}

function render() {
  $('balance').textContent = formatter.format(balance(state));
  $('pitch').replaceChildren(...state.lineup.slice(0, 11).map(squadSlot));
  $('bench').replaceChildren(...state.lineup.slice(11).map((id, index) => squadSlot(id, index + 11)));
  const owned = [...state.recruits, ...scoutIds];
  $('inventory-count').textContent = `${owned.length} joueurs`;
  $('inventory-list').replaceChildren(...owned.map(id => {
    const index = state.lineup.indexOf(id);
    return playerRow(players.get(id), index >= 0 ? slotName(index) : 'En réserve');
  }));
  renderShop();
  if (picker.open) renderPicker();
}

let state;
try {
  state = load();
  render();
} catch (error) {
  feedback(error.message, true);
}

for (const button of document.querySelectorAll('[data-view]')) {
  button.onclick = () => {
    for (const item of document.querySelectorAll('[data-view]')) {
      const active = item === button;
      $(item.dataset.view).hidden = !active;
      item.setAttribute('aria-pressed', active);
    }
  };
}
const openClub = $('open-club');
openClub.onclick = () => club.showModal();
club.addEventListener('close', () => openClub.focus());
$('open-recruitment').onclick = () => {
  $('catalogue-feedback').hidden = true;
  catalogue.showModal();
  if (state) renderShop();
};
if (location.hash === '#inazuma-fc') {
  history.replaceState(history.state, '', location.pathname + location.search);
  club.showModal();
}
$('rarity').onchange = () => { if (state) renderShop(); };
picker.addEventListener('close', () => {
  document.querySelector(`[data-slot="${activeSlot}"]`)?.focus();
  activeSlot = null;
});
window.addEventListener('storage', event => {
  if (event.key !== STORAGE && event.key !== null) return;
  try {
    state = load();
    render();
  } catch (error) {
    feedback(error.message, true);
  }
});
