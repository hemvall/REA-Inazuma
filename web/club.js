const STORAGE = 'inazuma-fc:v1';
const STARTING_CREDITS = 3800;
const SCOUT_RESALE_CREDITS = 50;
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
  {id: 'tim', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/u/f/ufxz9wwq5hm.png', name: 'Tim Saunders', position: 'MIL', rarity: 'Bronze', price: 180},
  {id: 'sam-kincaid', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/a/1/a1orm9vieek.png', name: 'Sam Kincaid', position: 'MIL', rarity: 'Bronze', price: 210},
  {id: 'peter-drent', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/d/5/d5w9zd0i6nc.png', name: 'Peter Drent', position: 'DEF', rarity: 'Bronze', price: 230},
  {id: 'nathan-jones', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/v/a/vaeuza7dvs8.png', name: 'Nathan Jones', position: 'GB', rarity: 'Bronze', price: 240},
  {id: 'chuck-dollman', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/x/m/xmeolswmzne.png', name: 'Chuck Dollman', position: 'AT', rarity: 'Bronze', price: 250},
  {id: 'hekyll', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/p/5/p54_qlu6ghc.png', name: 'Hekyll Jyde', position: 'DEF', rarity: 'Bronze', price: 260},
  {id: 'erik', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/e/4/e4qtt3lwf_m.png', name: 'Erik Eagle', position: 'MIL', rarity: 'Argent', price: 390},
  {id: 'kevin', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/0/d/0dvmw8cb_ye.png', name: 'Kevin Dragonfly', position: 'AT', rarity: 'Argent', price: 430},
  {id: 'jack', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/m/r/mrvaa0xojh8.png', name: 'Jack Wallside', position: 'DEF', rarity: 'Argent', price: 420},
  {id: 'celia', image: '/assets/celia.png', name: 'Celia Hills', position: 'MIL', rarity: 'Argent', price: 460},
  {id: 'bobby', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/-/x/-xzmaq-eqf8.png', name: 'Bobby Shearer', position: 'DEF', rarity: 'Argent', price: 390},
  {id: 'daniel-hatch', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/l/d/ldrmvkqotue.png', name: 'Daniel Hatch', position: 'AT', rarity: 'Argent', price: 410},
  {id: 'rob-crombie', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/m/k/mkvjitw20us.png', name: 'Rob Crombie', position: 'GB', rarity: 'Argent', price: 420},
  {id: 'bruce-monkey', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/i/j/ijd315vl-h0.png', name: 'Bruce Monkey', position: 'MIL', rarity: 'Argent', price: 440},
  {id: 'neil-turner', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/i/n/inwfp5x5ak8.png', name: 'Neil Turner', position: 'AT', rarity: 'Argent', price: 450},
  {id: 'archer', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/p/7/p7cdsgjrbs0.png', name: 'Archer Hawkins', position: 'DEF', rarity: 'Argent', price: 480},
  {id: 'mark', image: '/assets/captain-mark.png', name: 'Mark Evans', position: 'GB', rarity: 'Or', price: 800},
  {id: 'axel', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/f/1/f1kh7d67sbs.png', name: 'Axel Blaze', position: 'AT', rarity: 'Or', price: 850},
  {id: 'joseph-king', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/9/w/9wtikebapts.png', name: 'Joseph King', position: 'GB', rarity: 'Or', price: 720},
  {id: 'david-samford', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/u/d/udbgi0_9hlm.png', name: 'David Samford', position: 'AT', rarity: 'Or', price: 740},
  {id: 'hurley', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/i/0/i0spbukph8c.png', name: 'Hurley Kane', position: 'DEF', rarity: 'Or', price: 760},
  {id: 'austin', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/v/u/vu_2_98zume.png', name: 'Austin Hobbes', position: 'AT', rarity: 'Or', price: 790},
  {id: 'caleb', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/s/x/sxyalpxpni8.png', name: 'Caleb Stonewall', position: 'MIL', rarity: 'Or', price: 810},
  {id: 'shawn', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/o/p/opancch54ie.png', name: 'Shawn Froste', position: 'DEF', rarity: 'Or', price: 880},
  {id: 'nathan', image: '/assets/captain-nathan-dark.png', name: 'Nathan Swift', detail: 'Empereurs noirs', position: 'AT', rarity: 'Légendaire', price: 1500},
  {id: 'xene', image: '/assets/captain-xene.png', name: 'Xene', detail: 'Genesis', position: 'AT', rarity: 'Légendaire', price: 1600},
  {id: 'jude', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/l/1/l1wbplzhm4k.png', name: 'Jude Sharp', position: 'MIL', rarity: 'Légendaire', price: 1300},
  {id: 'byron', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/d/y/dykb3jbxeis.png', name: 'Byron Love', position: 'MIL', rarity: 'Légendaire', price: 1400},
  {id: 'torch', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/m/d/mdglyf7jc3c.png', name: 'Torch', position: 'AT', rarity: 'Légendaire', price: 1450},
  {id: 'gazelle', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/i/r/ir7gceyqjb8.png', name: 'Gazelle', position: 'AT', rarity: 'Légendaire', price: 1475},
  {id: 'xavier-foster', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/8/y/8yq-vg9hzzc.png', name: 'Xavier Foster', position: 'AT', rarity: 'Légendaire', price: 1550},
  {id: 'xavier-schiller', image: 'https://dxi4wb638ujep.cloudfront.net/1/k/j/b/jbof1s5dybs.png', name: 'Xavier Schiller', position: 'AT', rarity: 'Légendaire', price: 1750},
];
const scoutIds = scouts.map(player => player.id);
const players = new Map([...scouts, ...recruits].map(player => [player.id, player]));
const $ = id => document.getElementById(id);
const picker = $('picker');
const club = $('club-window');
const catalogue = $('recruitment-catalogue');
const sale = $('club-sale');
const formatter = new Intl.NumberFormat('fr-FR');
let activeSlot = null;
let sellingId = null;

function ownedPlayers(state) {
  return [...state.recruits, ...scoutIds.filter(id => !state.soldScouts.includes(id))];
}

function resalePrice(player) {
  return player.price ? Math.floor(player.price / 2) : SCOUT_RESALE_CREDITS;
}

function load() {
  const value = JSON.parse(localStorage.getItem(STORAGE) ?? 'null');
  if (value === null) return {recruits: [], soldScouts: [], credits: STARTING_CREDITS, lineup: [...scoutIds]};
  if (!Array.isArray(value.recruits) || !Array.isArray(value.lineup)
      || value.recruits.some(id => !recruits.some(player => player.id === id))
      || new Set(value.recruits).size !== value.recruits.length) throw new Error('Sauvegarde du club illisible.');
  value.soldScouts ??= [];
  value.credits ??= STARTING_CREDITS - value.recruits.reduce((total, id) => total + players.get(id).price, 0);
  const assigned = value.lineup.filter(id => id !== null);
  if (!Array.isArray(value.soldScouts) || value.soldScouts.some(id => !scoutIds.includes(id))
      || new Set(value.soldScouts).size !== value.soldScouts.length
      || !Number.isSafeInteger(value.credits) || value.credits < 0
      || value.lineup.length !== slots.length || new Set(assigned).size !== assigned.length
      || assigned.some(id => !ownedPlayers(value).includes(id))) throw new Error('Sauvegarde du club illisible.');
  return value;
}

function feedback(text, error = false) {
  const message = error && picker.open ? $('picker-error')
    : error && sale.open ? $('sale-error')
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
  const label = player ? playerName(player) : 'Place libre';
  button.setAttribute('aria-label', `${slotName(index)} — ${label}. Choisir un joueur`);
  button.title = label;
  const visual = player ? portrait(player) : node('span', 'club-portrait empty-slot', '+');
  button.append(visual, node('span', 'slot-name', player?.name ?? label));
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
    const afford = state.credits >= player.price;
    const button = node('button', 'purchase', owned ? 'Recruté' : afford ? 'Acheter' : 'Budget insuffisant');
    button.type = 'button';
    button.disabled = owned || !afford;
    button.setAttribute('aria-label', `${button.textContent} — ${playerName(player)}`);
    button.onclick = async () => {
      const focused = document.activeElement === button;
      const saved = await update(copy => {
        if (copy.recruits.includes(player.id)) throw new Error('Ce joueur appartient déjà au club.');
        if (copy.credits < player.price) throw new Error('Crédits insuffisants.');
        copy.credits -= player.price;
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
  const owned = ownedPlayers(state);
  $('picker-empty').hidden = owned.length > 0;
  $('picker-list').replaceChildren(...owned.map(id => {
    const player = players.get(id);
    const position = state.lineup.indexOf(id);
    const button = node('button', 'choose', position === selecting ? 'Actuel' : 'Choisir');
    button.type = 'button';
    button.disabled = position === selecting;
    button.setAttribute('aria-label', `${button.textContent} — ${playerName(player)}`);
    button.onclick = async () => {
      const saved = await update(copy => {
        if (!ownedPlayers(copy).includes(id)) throw new Error('Ce joueur ne fait plus partie du club.');
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

function confirmSale(player) {
  sellingId = player.id;
  $('sale-error').hidden = true;
  const credits = formatter.format(resalePrice(player));
  $('sale-details').textContent = `Revendre ${playerName(player)} pour ${credits} crédits ? Le joueur quittera ton effectif.`;
  sale.showModal();
}

function render() {
  $('balance').textContent = formatter.format(state.credits);
  $('pitch').replaceChildren(...state.lineup.slice(0, 11).map(squadSlot));
  $('bench').replaceChildren(...state.lineup.slice(11).map((id, index) => squadSlot(id, index + 11)));
  const owned = ownedPlayers(state);
  $('inventory-count').textContent = `${owned.length} joueurs`;
  $('inventory-empty').hidden = owned.length > 0;
  $('inventory-list').replaceChildren(...owned.map(id => {
    const player = players.get(id);
    const index = state.lineup.indexOf(id);
    const price = formatter.format(resalePrice(player));
    const button = node('button', 'resell', `Revendre · ${price} cr.`);
    button.type = 'button';
    button.setAttribute('aria-label', `Revendre ${playerName(player)} pour ${price} crédits`);
    button.onclick = () => confirmSale(player);
    return playerRow(player, index >= 0 ? slotName(index) : 'En réserve', button);
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
$('sale-confirm').onclick = async () => {
  const id = sellingId;
  const saved = await update(copy => {
    if (!ownedPlayers(copy).includes(id)) throw new Error('Ce joueur ne fait plus partie du club.');
    const player = players.get(id);
    const price = resalePrice(player);
    if (player.price) copy.recruits = copy.recruits.filter(recruit => recruit !== id);
    else copy.soldScouts.push(id);
    copy.lineup = copy.lineup.map(assigned => assigned === id ? null : assigned);
    copy.credits += price;
    return `${playerName(player)} a été revendu. +${formatter.format(price)} crédits.`;
  });
  if (saved && sale.open && sellingId === id) {
    sale.close();
    $('inventory-title').focus();
  }
};
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
