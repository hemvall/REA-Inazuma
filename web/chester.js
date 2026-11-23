const VOICE_DELIVERY = {
  goal: {rate: 1.20, pitch: 1.36},
  shot: {rate: 1.17, pitch: 1.29},
  attack_duel: {rate: 1.13, pitch: 1.24},
  defence_duel: {rate: 1.13, pitch: 1.24},
  halftime: {rate: 1.03, pitch: 1.15},
  result: {rate: 1.01, pitch: 1.12},
};

const NEUILLE_LINES = {
  kickoff: ['Azy frer, le Five est en classé !', 'Oh na, lobby de zinzins !'],
  handoff: ['Bien, le ballon fait sa tournée !', 'Azy frer, passe en Colissimo !'],
  turnover: ['Oh na, ballon direct sur Leboncoin !', 'Fils dé… le pressing fait les poches !'],
  attack_duel: ['Oh na, duel de scooters !', 'Azy frer, le vigile du Franprix !'],
  defence_duel: ['Bien, le Franprix est fermé !', 'Oh na, videur de mariage !'],
  shot: ['Fils dé… le ballon lui doit des thunes !', 'Azy frer, colis express pour les cages !'],
  goal: ['Oh na, défense en mode avion !', 'Bien, filet livré sans signature !', 'Fils dé… Windows Vista en défense !'],
  halftime: ['Bien, rechargez les manettes !', 'Azy frer, pause merguez !'],
  resume: ['Oh na, le serveur a redémarré !', 'Azy frer, deuxième fournée !'],
  result: ['Bien, les avocats WhatsApp débarquent !', 'Oh na, le débrief va piquer !'],
};

export function createChester({api, mode, enabled, captions, volume, line, hint, status}) {
  const voice = window.speechSynthesis;
  let session = null;
  let epoch = null;
  let cursor = 0;
  let paused = false;
  let current = null;
  let pending = [];
  let caption = '';
  let captionTimer;
  let voiceFailed = false;
  const previous = {};
  const neuilleTurns = {};

  function renderCaption() {
    const showText = captions.checked || (enabled.checked && (!frenchVoice() || voiceFailed));
    const text = showText ? caption : '';
    if (line.textContent !== text) line.textContent = text;
    hint.hidden = Boolean(text);
    hint.textContent = !enabled.checked && !captions.checked ? 'Active les sous-titres ou le commentaire vocal.'
      : !showText ? 'Les sous-titres sont désactivés.'
      : paused ? 'Commentaire en pause.' : 'En attente d’une action…';
  }

  function showCaption(text) {
    clearTimeout(captionTimer);
    caption = text;
    renderCaption();
    if (text) captionTimer = setTimeout(() => showCaption(''), 8000);
  }

  function stop() {
    const speaking = current?.speaking;
    current = null;
    pending = [];
    if (speaking) voice?.cancel();
    showCaption('');
  }

  function frenchVoice() {
    const options = voice?.getVoices().filter(item => /^fr(?:[-_]|$)/i.test(item.lang)) ?? [];
    const france = options.filter(item => /^fr[-_]FR$/i.test(item.lang));
    return france.find(item => /\b(?:Henri|Paul|Thomas|Rémi|Remi|Alain)\b/i.test(item.name))
      ?? france.find(item => item.localService)
      ?? france[0] ?? options[0];
  }

  function updateStatus() {
    const available = Boolean(frenchVoice()) && !voiceFailed;
    volume.disabled = !enabled.checked || !available;
    status.textContent = enabled.checked && !available
      ? 'Voix française indisponible. Les sous-titres restent disponibles.'
      : '';
    renderCaption();
  }

  async function playNext() {
    if (current || paused || (!enabled.checked && !captions.checked)) return;
    const event = pending.shift();
    if (!event) return;
    if (Date.now() - event.at * 1000 > 4500) return playNext();
    const turn = {kind: event.kind, speaking: false};
    current = turn;
    const style = mode.value;
    const key = style + ':' + event.kind;
    const riffs = style === 'neuille' ? NEUILLE_LINES[event.kind] : null;
    const count = neuilleTurns[event.kind] ?? 0;
    const fallback = riffs ? riffs[count % riffs.length] : '';
    if (riffs) neuilleTurns[event.kind] = count + 1;
    const format = reaction => style === 'neuille' ? reaction
      : event.text + (reaction ? ' ' + reaction : '');
    showCaption(format(fallback));
    let deadline;
    const variation = await Promise.race([
      api('chester_reaction', {session_id: session, epoch, event_id: event.id, mode: style, previous: previous[key]}).catch(() => null),
      new Promise(resolve => { deadline = setTimeout(resolve, 950); }),
    ]);
    clearTimeout(deadline);
    if (current !== turn) return;
    const reaction = variation?.reaction || fallback;
    if (reaction) previous[key] = reaction;
    const text = format(reaction);
    const selectedVoice = frenchVoice();
    showCaption(text);
    const done = () => {
      if (current !== turn) return;
      current = null;
      playNext();
    };
    turn.done = done;
    if (!enabled.checked || !selectedVoice || voiceFailed || Number(volume.value) === 0) {
      // Keep consecutive caption-only announcements readable.
      setTimeout(done, 1800);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = selectedVoice;
    utterance.lang = selectedVoice.lang;
    const delivery = VOICE_DELIVERY[event.kind] ?? {rate: 1.10, pitch: 1.20};
    utterance.rate = delivery.rate;
    utterance.pitch = delivery.pitch;
    utterance.volume = Number(volume.value);
    utterance.onend = done;
    utterance.onerror = () => {
      if (current !== turn || !turn.speaking) return;
      if (Number(volume.value) !== 0) {
        voiceFailed = true;
        updateStatus();
      }
      setTimeout(done, 1800);
    };
    turn.speaking = true;
    voice.speak(utterance);
  }

  function muteCurrent() {
    if (current?.speaking) {
      const turn = current;
      turn.speaking = false;
      voice.cancel();
      setTimeout(turn.done, 1800);
    }
  }

  enabled.addEventListener('change', () => {
    if (!enabled.checked) {
      if (captions.checked) muteCurrent();
      else stop();
    } else {
      voiceFailed = false;
      voice?.resume();
    }
    updateStatus();
  });
  volume.addEventListener('input', () => {
    if (Number(volume.value) === 0) muteCurrent();
  });
  captions.addEventListener('change', renderCaption);
  mode.addEventListener('change', stop);
  voice?.addEventListener('voiceschanged', updateStatus);
  window.addEventListener('pagehide', stop);
  updateStatus();

  return {
    observe(sessionId, journal) {
      if (sessionId !== session) {
        session = sessionId;
        paused = false;
        stop();
        epoch = null;
        cursor = 0;
      }
      if (!journal || journal.session_id !== sessionId || journal.epoch < epoch || journal.cursor < cursor) return;
      if (epoch === null) {
        epoch = journal.epoch;
        cursor = journal.cursor;
        return;
      }
      if (journal.epoch !== epoch) {
        stop();
        epoch = journal.epoch;
      }
      const events = journal.events.filter(event => event.id > cursor && Date.now() - event.at * 1000 <= 4500);
      cursor = journal.cursor;
      if ((!enabled.checked && !captions.checked) || paused || !events.length) return;
      const final = events.find(event => event.kind === 'result');
      const goals = events.filter(event => event.kind === 'goal');
      if (final || (goals.length && current?.kind !== 'goal')) stop();
      if (goals.length) pending = pending.filter(event => event.kind === 'goal');
      pending.push(...(final ? [final] : goals.length ? goals : events));
      playNext();
    },
    pause(value) {
      paused = value;
      if (value) stop();
      else renderCaption();
    },
  };
}
