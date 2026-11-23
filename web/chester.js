export function createChester({api, enabled, captions, volume, line, hint, status}) {
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

  function renderCaption() {
    const showText = captions.checked || !frenchVoice() || voiceFailed;
    const text = enabled.checked && showText ? caption : '';
    if (line.textContent !== text) line.textContent = text;
    hint.hidden = Boolean(text);
    hint.textContent = !enabled.checked ? 'Active le commentaire vocal pour entendre Chester.'
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
    return voice?.getVoices().find(item => /^fr(?:[-_]|$)/i.test(item.lang));
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
    if (current || paused || !enabled.checked) return;
    const event = pending.shift();
    if (!event) return;
    if (Date.now() - event.at * 1000 > 4500) return playNext();
    const turn = {kind: event.kind, speaking: false};
    current = turn;
    let deadline;
    const variation = await Promise.race([
      api('chester_reaction', {session_id: session, epoch, event_id: event.id, previous: previous[event.kind]}).catch(() => null),
      new Promise(resolve => { deadline = setTimeout(resolve, 950); }),
    ]);
    clearTimeout(deadline);
    if (current !== turn) return;
    if (variation?.reaction) previous[event.kind] = variation.reaction;
    const text = event.text + (variation?.reaction ? ' ' + variation.reaction : '');
    const selectedVoice = frenchVoice();
    showCaption(text);
    const done = () => {
      if (current !== turn) return;
      current = null;
      playNext();
    };
    turn.done = done;
    if (!selectedVoice || voiceFailed || Number(volume.value) === 0) {
      // Keep consecutive caption-only announcements readable.
      setTimeout(done, 1800);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = selectedVoice;
    utterance.lang = selectedVoice.lang;
    utterance.rate = 1.08;
    utterance.volume = Number(volume.value);
    utterance.onend = done;
    utterance.onerror = () => {
      if (current !== turn) return;
      if (Number(volume.value) !== 0) {
        voiceFailed = true;
        updateStatus();
      }
      setTimeout(done, 1800);
    };
    turn.speaking = true;
    voice.speak(utterance);
  }

  enabled.addEventListener('change', () => {
    if (!enabled.checked) stop();
    else {
      voiceFailed = false;
      voice?.resume();
    }
    updateStatus();
  });
  volume.addEventListener('input', () => {
    if (Number(volume.value) === 0 && current?.speaking) {
      const turn = current;
      turn.speaking = false;
      voice.cancel();
      setTimeout(turn.done, 1800);
    }
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
      if (!enabled.checked || paused || !events.length) return;
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
