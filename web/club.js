const STORAGE = 'inazuma-fc:v1';
const STARTING_CREDITS = 3800;
const slots = ['AT', 'AT', 'MIL', 'MIL', 'MIL', 'MIL', 'DEF', 'DEF', 'DEF', 'DEF', 'GB',
  'Banc', 'Banc', 'Banc', 'Banc', 'Banc'];
const scouts = slots.map((position, index) => ({
  id: `scout-${index + 1}`, name: `Scoot ${String(index + 1).padStart(2, '0')}`,
  position, rarity: 'Scoot', price: 0,
}));
const recruits = [
  {id: 'willy', name: 'Willy Glasses', position: 'AT', rarity: 'Bronze', price: 180},
  {id: 'steve', name: 'Steve Grim', position: 'MIL', rarity: 'Bronze', price: 220},
  {id: 'tod', name: 'Tod Ironside', position: 'DEF', rarity: 'Bronze', price: 170},
  {id: 'max', name: 'Maxwell Carson', position: 'MIL', rarity: 'Bronze', price: 190},
  {id: 'darren', name: 'Darren LaChance', position: 'GB', rarity: 'Bronze', price: 200},
  {id: 'jim', name: 'Jim Wraith', position: 'DEF', rarity: 'Bronze', price: 210},
  {id: 'erik', name: 'Erik Eagle', position: 'MIL', rarity: 'Argent', price: 390},
  {id: 'kevin', name: 'Kevin Dragonfly', position: 'AT', rarity: 'Argent', price: 430},
  {id: 'jack', name: 'Jack Wallside', position: 'DEF', rarity: 'Argent', price: 420},
  {id: 'celia', name: 'Celia Hills', position: 'MIL', rarity: 'Argent', price: 460},
  {id: 'mark', name: 'Mark Evans', position: 'GB', rarity: 'Or', price: 800},
  {id: 'axel', name: 'Axel Blaze', position: 'AT', rarity: 'Or', price: 850},
  {id: 'nathan', name: 'Nathan Swift', detail: 'Empereurs noirs', position: 'AT', rarity: 'Légendaire', price: 1500},
  {id: 'xene', name: 'Xene', detail: 'Genesis', position: 'AT', rarity: 'Légendaire', price: 1600},
];
const scoutIds = scouts.map(player => player.id);
const players = new Map([...scouts, ...recruits].map(player => [player.id, player]));
const $ = id => document.getElementById(id);
const picker = $('picker');
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
  const message = error && picker.open ? $('picker-error') : $('feedback');
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
  const shirt = node('span', 'shirt', index < 11 ? String(index + 1).padStart(2, '0') : `R${index - 10}`);
  shirt.setAttribute('aria-hidden', 'true');
  button.append(shirt, node('span', 'slot-name', player.name));
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
  const name = node('div', 'player-identity');
  name.append(node('strong', '', playerName(player)), node('span', '', info));
  const rarity = node('span', 'rarity', player.rarity);
  rarity.dataset.rarity = player.rarity;
  row.append(name, rarity);
  if (action) row.append(action);
  return row;
}

function renderShop() {
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
        return `${player.name} a rejoint ton inventaire.`;
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
    if (state && button.dataset.view === 'shop') renderShop();
  };
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
