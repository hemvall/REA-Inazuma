const VOICE_DELIVERY = {
  goal: {rate: 1.20, pitch: 1.36},
  shot: {rate: 1.17, pitch: 1.29},
  attack_duel: {rate: 1.13, pitch: 1.24},
  defence_duel: {rate: 1.13, pitch: 1.24},
  halftime: {rate: 1.03, pitch: 1.15},
  result: {rate: 1.01, pitch: 1.12},
};
const CONTEXT_EVENTS = new Set(['kickoff', 'goal', 'halftime', 'result']);

export function createChester({api, enabled, captions, volume, line, hint, status, tool}) {
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
  let lastContextEvent = 0;
  const previous = {};

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

  async function showContext(event) {
    const request = {session_id: session, epoch, event_id: event.id, previous: previous[event.kind]};
    try {
      const result = await api('chester_reaction', request);
      if (session !== request.session_id || epoch !== request.epoch || event.id <= lastContextEvent
          || (!enabled.checked && !captions.checked) || !result.reaction || !result.tool?.context) return;
      lastContextEvent = event.id;
      previous[event.kind] = result.reaction;
      const {score} = result.tool.context;
      const source = score ? `${result.tool.name} · Score ${score.home}–${score.away}` : result.tool.name;
      tool.textContent = `${source} · « ${result.reaction} »`;
      tool.hidden = false;
    } catch {
      // The confirmed announcement has already played.
    }
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

  function playNext() {
    if (current || paused || (!enabled.checked && !captions.checked)) return;
    const event = pending.shift();
    if (!event) return;
    if (Date.now() - event.at * 1000 > 4500) return playNext();
    const turn = {kind: event.kind, speaking: false};
    current = turn;
    if (CONTEXT_EVENTS.has(event.kind)) showContext(event);
    const text = event.text;
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
  voice?.addEventListener('voiceschanged', updateStatus);
  window.addEventListener('pagehide', stop);
  updateStatus();

  return {
    observe(sessionId, journal) {
      if (sessionId !== session) {
        session = sessionId;
        paused = false;
        stop();
        lastContextEvent = 0;
        tool.hidden = true;
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
        lastContextEvent = 0;
        tool.hidden = true;
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
