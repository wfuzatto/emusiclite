const trackList = document.getElementById('trackList');
const trackSearch = document.getElementById('trackSearch');
const prevPage = document.getElementById('prevPage');
const nextPage = document.getElementById('nextPage');
const pageInfo = document.getElementById('pageInfo');
const modal = document.getElementById('trackModal');
const openModalBtn = document.getElementById('openModal');
const closeModalBtn = document.getElementById('closeModal');
const modalTitle = document.getElementById('modalTitle');

const form = document.querySelector('form.form-grid');
const fields = {
  id: document.getElementById('track_id'),
  title: document.getElementById('title'),
  artist: document.getElementById('artist'),
  genre: document.getElementById('genre'),
  mood: document.getElementById('mood'),
  duration: document.getElementById('duration'),
  cover: document.getElementById('cover_url'),
  description: document.getElementById('description'),
  stream: document.getElementById('stream_url'),
  audioFile: document.getElementById('audio_file'),
};

let currentPage = 1;
const pageSize = 10;
let filtered = [];

function cards() {
  return Array.from(trackList?.querySelectorAll('.mini-card') || []);
}

function applyPagination() {
  const allCards = cards();
  const active = filtered.length ? filtered : allCards;
  const totalPages = Math.max(1, Math.ceil(active.length / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;
  const start = (currentPage - 1) * pageSize;
  const end = start + pageSize;

  active.forEach((card, idx) => {
    card.style.display = idx >= start && idx < end ? '' : 'none';
  });
  if (filtered.length) {
    allCards.forEach((card) => {
      if (!filtered.includes(card)) card.style.display = 'none';
    });
  }

  pageInfo.textContent = `${currentPage} / ${totalPages}`;
  prevPage.disabled = currentPage === 1;
  nextPage.disabled = currentPage === totalPages;
}

function filterTracks() {
  const q = (trackSearch?.value || '').toLowerCase().trim();
  const all = cards();
  if (!q) {
    filtered = [];
  } else {
    filtered = all.filter((card) => {
      const hay = `${card.dataset.title} ${card.dataset.artist} ${card.dataset.genre}`.toLowerCase();
      return hay.includes(q);
    });
  }
  currentPage = 1;
  applyPagination();
}

function loadToForm(card) {
  fields.id.value = card.dataset.id || '';
  fields.title.value = card.dataset.title || '';
  fields.artist.value = card.dataset.artist || '';
  fields.genre.value = card.dataset.genre || '';
  fields.mood.value = card.dataset.mood || '';
  fields.duration.value = card.dataset.duration || '';
  fields.cover.value = card.dataset.cover || '';
  fields.description.value = card.dataset.description || '';
  fields.stream.value = card.dataset.stream || '';
  if (modalTitle) modalTitle.textContent = 'Editar música';
  if (modal) {
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  }
}

if (trackSearch) trackSearch.addEventListener('input', filterTracks);
if (prevPage) prevPage.addEventListener('click', () => { currentPage--; applyPagination(); });
if (nextPage) nextPage.addEventListener('click', () => { currentPage++; applyPagination(); });

if (trackList) {
  trackList.addEventListener('click', (e) => {
    const card = e.target.closest('.mini-card');
    if (card) loadToForm(card);
  });
}

applyPagination();

function clearForm() {
  fields.id.value = '';
  fields.title.value = '';
  fields.artist.value = '';
  fields.genre.value = '';
  fields.mood.value = '';
  fields.duration.value = '';
  fields.cover.value = '';
  fields.description.value = '';
  fields.stream.value = '';
  if (fields.audioFile) fields.audioFile.value = '';
}

if (openModalBtn) {
  openModalBtn.addEventListener('click', () => {
    clearForm();
    if (modalTitle) modalTitle.textContent = 'Nova música';
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  });
}

if (closeModalBtn) {
  closeModalBtn.addEventListener('click', () => {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  });
}

if (modal) {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    }
  });
}

if (fields.audioFile) {
  fields.audioFile.addEventListener('change', () => {
    const file = fields.audioFile.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.addEventListener('loadedmetadata', () => {
      const total = Math.round(audio.duration || 0);
      const m = Math.floor(total / 60);
      const s = String(total % 60).padStart(2, '0');
      fields.duration.value = `${m}:${s}`;
      URL.revokeObjectURL(url);
    });
    audio.src = url;
  });
}
