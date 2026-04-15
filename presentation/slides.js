// Slide Navigation
const slides = document.querySelectorAll('.slide');
const curEl = document.getElementById('cur');
const totEl = document.getElementById('tot');
let current = 0;

totEl.textContent = slides.length;

function show(n) {
  slides[current].classList.remove('active');
  current = (n + slides.length) % slides.length;
  slides[current].classList.add('active');
  curEl.textContent = current + 1;

  // Apply dark bg
  const bg = slides[current].getAttribute('data-bg');
  document.body.classList.toggle('slide-dark', bg === 'dark');
}

function next() { show(current + 1); }
function prev() { show(current - 1); }

document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); next(); }
  if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
  if (e.key === 'Home') { e.preventDefault(); show(0); }
  if (e.key === 'End') { e.preventDefault(); show(slides.length - 1); }
});

// Touch support
let touchStartX = 0;
document.addEventListener('touchstart', e => { touchStartX = e.changedTouches[0].screenX; });
document.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].screenX - touchStartX;
  if (Math.abs(dx) > 50) { dx < 0 ? next() : prev(); }
});
