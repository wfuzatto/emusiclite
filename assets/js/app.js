const searchInput = document.getElementById('searchInput');
const grid = document.getElementById('trackGrid');
const nowCover = document.getElementById('nowCover');
const nowTitle = document.getElementById('nowTitle');
const nowArtist = document.getElementById('nowArtist');
const nowTime = document.getElementById('nowTime');
const nowDuration = document.getElementById('nowDuration');
const nowFill = document.getElementById('nowFill');
const progressBar = document.getElementById('progressBar');
const audio = document.getElementById('audio');
const playBtn = document.getElementById('playBtn');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');

let currentIndex = -1;
let isPlaying = false;

function filterTracks() {
  const q = (searchInput?.value || '').toLowerCase().trim();
  document.querySelectorAll('.track-card').forEach((card) => {
    const hay = [
      card.dataset.title,
      card.dataset.artist,
      card.dataset.genre,
      card.dataset.mood,
    ].join(' ');
    card.style.display = !q || hay.includes(q) ? '' : 'none';
  });
}

function formatTime(seconds) {
  if (!isFinite(seconds)) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function setTrackFromCard(card) {
  const title = card.querySelector('h3')?.textContent || '';
  const artist = card.querySelector('p')?.textContent || '';
  const duration = card.dataset.duration || '0:00';
  const cover = card.dataset.cover || '';
  const stream = card.dataset.stream || '';

  nowTitle.textContent = title;
  nowArtist.textContent = artist;
  nowDuration.textContent = duration;
  nowTime.textContent = '0:00';
  nowFill.style.width = '0%';
  nowCover.style.backgroundImage = `url('${cover}')`;

  if (stream) {
    audio.src = stream;
  } else {
    audio.removeAttribute('src');
  }
}

function setCurrentByIndex(idx) {
  const cards = Array.from(document.querySelectorAll('.track-card')).filter(c => c.style.display !== 'none');
  if (cards.length === 0) return;
  currentIndex = (idx + cards.length) % cards.length;
  setTrackFromCard(cards[currentIndex]);
  if (isPlaying) audio.play().catch(() => {});
}

const playIcon = '<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M8 5v14l11-7L8 5z\"/></svg>';
const pauseIcon = '<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M7 5h3.5v14H7V5zm6.5 0H17v14h-3.5V5z\"/></svg>';

function togglePlay() {
  if (!audio.src) return;
  if (audio.paused) {
    audio.play().then(() => {
      isPlaying = true;
      playBtn.innerHTML = pauseIcon;
    }).catch(() => {});
  } else {
    audio.pause();
    isPlaying = false;
    playBtn.innerHTML = playIcon;
  }
}

if (searchInput) searchInput.addEventListener('input', filterTracks);
if (grid) {
  grid.addEventListener('click', (e) => {
    const card = e.target.closest('.track-card');
    if (!card) return;
    const cards = Array.from(document.querySelectorAll('.track-card')).filter(c => c.style.display !== 'none');
    currentIndex = cards.indexOf(card);
    setTrackFromCard(card);
    if (audio.src) {
      audio.play().then(() => {
        isPlaying = true;
        playBtn.innerHTML = pauseIcon;
      }).catch(() => {});
    }
  });
}

if (playBtn) playBtn.addEventListener('click', togglePlay);
if (prevBtn) prevBtn.addEventListener('click', () => setCurrentByIndex(currentIndex - 1));
if (nextBtn) nextBtn.addEventListener('click', () => setCurrentByIndex(currentIndex + 1));

if (audio) {
  audio.addEventListener('timeupdate', () => {
    nowTime.textContent = formatTime(audio.currentTime);
    if (audio.duration) {
      nowFill.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
      nowDuration.textContent = formatTime(audio.duration);
    }
  });

  audio.addEventListener('ended', () => {
    setCurrentByIndex(currentIndex + 1);
  });
}

if (playBtn) {
  playBtn.innerHTML = playIcon;
}

if (progressBar) {
  progressBar.addEventListener('click', (e) => {
    if (!audio.duration) return;
    const rect = progressBar.getBoundingClientRect();
    const percent = Math.min(Math.max(0, (e.clientX - rect.left) / rect.width), 1);
    audio.currentTime = percent * audio.duration;
  });
}
