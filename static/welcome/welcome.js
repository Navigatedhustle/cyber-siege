import {
  api
} from '/static/common.js';
async function status() {
  try {
    const health = await api('/health', undefined, 'screen');
    const count = health.qualified_models.length;
    document.getElementById('availability').textContent = health.replay ? 'Recorded rehearsal mode' : count ? `${count} ${count===1?'model':'models'} ready on this Fury` : 'Workshop online · Live inference unavailable';
    document.getElementById('availability-detail').textContent = health.replay ? 'The room will see an explicit replay label.' : 'Press Start experience. Your progress is individual.';
    document.getElementById('availability-dot').classList.toggle('ready', count > 0 && !health.replay);
  } catch {
    document.getElementById('availability').textContent = 'Reconnecting to the workshop';
    document.getElementById('availability-detail').textContent = 'Refresh this page if the connection does not return.';
  }
}
await status();
setInterval(status, 15000);
