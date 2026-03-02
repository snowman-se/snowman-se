'use strict';

// ===== Constants =====
const TOTAL_CANDIES = 60; // 30 × 2 sets
const CANDY_COLORS  = ['blue', 'red', 'yellow'];
const COLOR_LABELS  = { blue: '青', red: '赤', yellow: '黄色' };
const FLAVOR_LABELS = ['バナナ', 'イチゴ', 'パイナップル', 'サイダー'];

// ===== State =====
let candyColors = [];   // pre-assigned color per thread slot
let stock       = 0;    // remaining unpulled count

// ===== DOM refs =====
const threadsArea  = document.getElementById('threadsArea');
const stockCount   = document.getElementById('stockCount');
const resultPanel  = document.getElementById('resultPanel');
const resultCandy  = document.getElementById('resultCandy');
const resultText   = document.getElementById('resultText');
const historyList  = document.getElementById('historyList');
const resetBtn     = document.getElementById('resetBtn');

// ===== Helpers =====

/** Fisher-Yates shuffle in-place */
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/** Pick a random flavor label */
function randomFlavor() {
  return FLAVOR_LABELS[Math.floor(Math.random() * FLAVOR_LABELS.length)];
}

// ===== Build thread elements =====
function buildThreads() {
  threadsArea.innerHTML = '';

  // Distribute colors evenly: 20 each (60 total / 3 colors)
  const baseColors = [];
  CANDY_COLORS.forEach(c => {
    for (let i = 0; i < TOTAL_CANDIES / CANDY_COLORS.length; i++) {
      baseColors.push(c);
    }
  });
  candyColors = shuffle(baseColors);
  stock       = TOTAL_CANDIES;

  for (let i = 0; i < TOTAL_CANDIES; i++) {
    const item = document.createElement('div');
    item.className  = 'thread-item';
    item.dataset.idx = i;

    const string = document.createElement('div');
    string.className = 'thread-string';

    const ring = document.createElement('div');
    ring.className = 'thread-ring';

    const dot = document.createElement('div');
    dot.className = 'candy-dot';

    item.appendChild(dot);   // dot above the string to simulate candy revealed
    item.appendChild(string);
    item.appendChild(ring);

    item.addEventListener('click', onThreadPull);
    threadsArea.appendChild(item);
  }

  updateStockDisplay();
  clearResult();
}

// ===== Event: pull a thread =====
function onThreadPull(e) {
  if (stock <= 0) return;

  const item  = e.currentTarget;
  const idx   = parseInt(item.dataset.idx, 10);
  const color = candyColors[idx];

  // Mark thread as pulled
  item.classList.add('pulled');
  item.removeEventListener('click', onThreadPull);

  // Show candy dot
  const dot = item.querySelector('.candy-dot');
  dot.classList.add(color);

  const flavor = randomFlavor();
  stock -= 1;
  updateStockDisplay(true);
  showResult(color, flavor);
  addHistory(color, flavor);

  if (stock === 0) {
    showEmptyMessage();
  }
}

// ===== UI updates =====

function updateStockDisplay(animate = false) {
  stockCount.textContent = stock;
  if (animate) {
    stockCount.classList.remove('bump');
    // Force reflow to restart animation
    void stockCount.offsetWidth;
    stockCount.classList.add('bump');
  }
}

function showResult(color, flavor) {
  resultCandy.className = `result-candy ${color}`;
  resultText.innerHTML =
    `<span class="color-name ${color}">${COLOR_LABELS[color]}</span>の飴（${flavor}）<br>` +
    `残り <strong>${stock}</strong> 個`;
}

function clearResult() {
  resultCandy.className = 'result-candy hidden';
  resultText.innerHTML  = '<span style="color:#bbb">糸を引いてみよう！</span>';
}

function addHistory(color, flavor) {
  const li = document.createElement('li');

  const dot = document.createElement('span');
  dot.className = `history-dot ${color}`;

  const now   = new Date();
  const time  = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;

  li.appendChild(dot);
  li.append(`${time}　${COLOR_LABELS[color]}の飴（${flavor}）`);

  // Prepend so newest is at top
  historyList.insertBefore(li, historyList.firstChild);
}

function showEmptyMessage() {
  const msg = document.createElement('div');
  msg.className = 'empty-msg';
  msg.textContent = '🎉 全部引きました！「リセット（入荷）」で再スタート！';
  threadsArea.appendChild(msg);
}

// ===== Reset =====
resetBtn.addEventListener('click', () => {
  historyList.innerHTML = '';
  buildThreads();
});

// ===== Init =====
buildThreads();
