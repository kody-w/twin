// tools/_qr.mjs — zero-dep QR Code (Model 2) encoder, byte mode -> SVG (§15 shard printing).
//
//   import { qrSvg, qrMatrix } from "./_qr.mjs";
//
// A printed shard is only an heirloom if it can be read back without our software. This is a
// faithful, dependency-free QR encoder (finder/timing/alignment patterns, Reed-Solomon ECC over
// GF(2^8)/0x11D, block interleaving, all 8 data masks with penalty scoring, BCH format/version
// info) so `succession shard --qr` emits standards-compliant, scannable codes. Algorithm and
// error-correction tables follow the ISO/IEC 18004 standard (Nayuki's reference tables).

// --- error-correction level -------------------------------------------------
// ordinal indexes the ECC tables; formatBits is the 2-bit code drawn into the format info.
export const ECC = {
  L: { ordinal: 0, formatBits: 1 },
  M: { ordinal: 1, formatBits: 0 },
  Q: { ordinal: 2, formatBits: 3 },
  H: { ordinal: 3, formatBits: 2 },
};

const ECC_CODEWORDS_PER_BLOCK = [
  [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
  [-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  [-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
];
const NUM_ERROR_CORRECTION_BLOCKS = [
  [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
  [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49],
  [-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68],
  [-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81],
];

const MIN_VERSION = 1;
const MAX_VERSION = 40;

function getBit(x, i) {
  return ((x >>> i) & 1) !== 0;
}

// GF(2^8)/0x11D multiplication (Russian-peasant) — the QR field (generator r=2).
function gfMul(x, y) {
  let z = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d);
    z ^= ((y >>> i) & 1) * x;
  }
  return z & 0xff;
}

function getNumRawDataModules(ver) {
  let result = (16 * ver + 128) * ver + 64;
  if (ver >= 2) {
    const numAlign = Math.floor(ver / 7) + 2;
    result -= (25 * numAlign - 10) * numAlign - 55;
    if (ver >= 7) result -= 36;
  }
  return result;
}

function getNumDataCodewords(ver, ecl) {
  return (
    Math.floor(getNumRawDataModules(ver) / 8) -
    ECC_CODEWORDS_PER_BLOCK[ecl.ordinal][ver] * NUM_ERROR_CORRECTION_BLOCKS[ecl.ordinal][ver]
  );
}

function reedSolomonComputeDivisor(degree) {
  const result = new Array(degree).fill(0);
  result[degree - 1] = 1;
  let root = 1;
  for (let i = 0; i < degree; i++) {
    for (let j = 0; j < result.length; j++) {
      result[j] = gfMul(result[j], root);
      if (j + 1 < result.length) result[j] ^= result[j + 1];
    }
    root = gfMul(root, 0x02);
  }
  return result;
}

function reedSolomonComputeRemainder(data, divisor) {
  const result = divisor.map(() => 0);
  for (const b of data) {
    const factor = b ^ result.shift();
    result.push(0);
    divisor.forEach((coef, i) => (result[i] ^= gfMul(coef, factor)));
  }
  return result;
}

// --- byte-mode segment ------------------------------------------------------
function charCountBits(ver) {
  return ver <= 9 ? 8 : 16; // byte mode: 8 bits (v1-9) else 16 bits (v10-40)
}

function makeDataCodewords(bytes, ver, ecl) {
  const bits = [];
  const push = (val, len) => {
    for (let i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1);
  };
  push(0x4, 4); // byte mode indicator
  push(bytes.length, charCountBits(ver));
  for (const b of bytes) push(b, 8);

  const capacityBits = getNumDataCodewords(ver, ecl) * 8;
  // terminator (up to 4 zero bits)
  for (let i = 0; i < 4 && bits.length < capacityBits; i++) bits.push(0);
  // pad to byte boundary
  while (bits.length % 8 !== 0) bits.push(0);
  // pad bytes 0xEC, 0x11 alternating
  const padBytes = [0xec, 0x11];
  for (let i = 0; bits.length < capacityBits; i++) push(padBytes[i % 2], 8);

  const cw = [];
  for (let i = 0; i < bits.length; i += 8) {
    let v = 0;
    for (let j = 0; j < 8; j++) v = (v << 1) | bits[i + j];
    cw.push(v);
  }
  return cw;
}

function addEccAndInterleave(data, ver, ecl) {
  const numBlocks = NUM_ERROR_CORRECTION_BLOCKS[ecl.ordinal][ver];
  const blockEccLen = ECC_CODEWORDS_PER_BLOCK[ecl.ordinal][ver];
  const rawCodewords = Math.floor(getNumRawDataModules(ver) / 8);
  const numShortBlocks = numBlocks - (rawCodewords % numBlocks);
  const shortBlockLen = Math.floor(rawCodewords / numBlocks);

  const blocks = [];
  const rsDiv = reedSolomonComputeDivisor(blockEccLen);
  for (let i = 0, k = 0; i < numBlocks; i++) {
    const datLen = shortBlockLen - blockEccLen + (i < numShortBlocks ? 0 : 1);
    const dat = data.slice(k, k + datLen);
    k += dat.length;
    const ecc = reedSolomonComputeRemainder(dat, rsDiv);
    if (i < numShortBlocks) dat.push(0);
    blocks.push(dat.concat(ecc));
  }

  const result = [];
  for (let i = 0; i < blocks[0].length; i++) {
    blocks.forEach((block, j) => {
      if (i !== shortBlockLen - blockEccLen || j >= numShortBlocks) result.push(block[i]);
    });
  }
  return result;
}

// --- matrix -----------------------------------------------------------------
function chooseVersion(byteLen, ecl) {
  for (let ver = MIN_VERSION; ver <= MAX_VERSION; ver++) {
    const capBits = getNumDataCodewords(ver, ecl) * 8;
    const usedBits = 4 + charCountBits(ver) + byteLen * 8;
    if (usedBits <= capBits) return ver;
  }
  throw new Error(`data too large for a single QR code (${byteLen} bytes)`);
}

function getAlignmentPatternPositions(ver, size) {
  if (ver === 1) return [];
  const numAlign = Math.floor(ver / 7) + 2;
  const step = Math.floor((ver * 8 + numAlign * 3 + 5) / (numAlign * 4 - 4)) * 2;
  const result = [6];
  for (let pos = size - 7; result.length < numAlign; pos -= step) result.splice(1, 0, pos);
  return result;
}

function buildMatrix(ver, ecl, allCodewords) {
  const size = ver * 4 + 17;
  const modules = Array.from({ length: size }, () => new Array(size).fill(false));
  const isFunction = Array.from({ length: size }, () => new Array(size).fill(false));

  const setFn = (x, y, dark) => {
    modules[y][x] = dark;
    isFunction[y][x] = true;
  };

  // timing patterns
  for (let i = 0; i < size; i++) {
    setFn(6, i, i % 2 === 0);
    setFn(i, 6, i % 2 === 0);
  }
  // finder patterns (+ separators)
  const drawFinder = (x, y) => {
    for (let dy = -4; dy <= 4; dy++) {
      for (let dx = -4; dx <= 4; dx++) {
        const dist = Math.max(Math.abs(dx), Math.abs(dy));
        const xx = x + dx;
        const yy = y + dy;
        if (xx >= 0 && xx < size && yy >= 0 && yy < size) setFn(xx, yy, dist !== 2 && dist !== 4);
      }
    }
  };
  drawFinder(3, 3);
  drawFinder(size - 4, 3);
  drawFinder(3, size - 4);

  // alignment patterns
  const align = getAlignmentPatternPositions(ver, size);
  const na = align.length;
  for (let i = 0; i < na; i++) {
    for (let j = 0; j < na; j++) {
      if ((i === 0 && j === 0) || (i === 0 && j === na - 1) || (i === na - 1 && j === 0)) continue;
      const cx = align[i];
      const cy = align[j];
      for (let dy = -2; dy <= 2; dy++) {
        for (let dx = -2; dx <= 2; dx++) setFn(cx + dx, cy + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
      }
    }
  }

  const drawFormat = (mask) => {
    const data = (ecl.formatBits << 3) | mask;
    let rem = data;
    for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
    const bits = ((data << 10) | rem) ^ 0x5412;
    for (let i = 0; i <= 5; i++) setFn(8, i, getBit(bits, i));
    setFn(8, 7, getBit(bits, 6));
    setFn(8, 8, getBit(bits, 7));
    setFn(7, 8, getBit(bits, 8));
    for (let i = 9; i < 15; i++) setFn(14 - i, 8, getBit(bits, i));
    for (let i = 0; i < 8; i++) setFn(size - 1 - i, 8, getBit(bits, i));
    for (let i = 8; i < 15; i++) setFn(8, size - 15 + i, getBit(bits, i));
    setFn(8, size - 8, true);
  };
  drawFormat(0); // placeholder

  // version info (v7+)
  if (ver >= 7) {
    let rem = ver;
    for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1f25);
    const bits = (ver << 12) | rem;
    for (let i = 0; i < 18; i++) {
      const color = getBit(bits, i);
      const a = size - 11 + (i % 3);
      const b = Math.floor(i / 3);
      setFn(a, b, color);
      setFn(b, a, color);
    }
  }

  // draw data via zigzag
  let i = 0;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let vert = 0; vert < size; vert++) {
      for (let j = 0; j < 2; j++) {
        const x = right - j;
        const upward = ((right + 1) & 2) === 0;
        const y = upward ? size - 1 - vert : vert;
        if (!isFunction[y][x] && i < allCodewords.length * 8) {
          modules[y][x] = getBit(allCodewords[i >>> 3], 7 - (i & 7));
          i++;
        }
      }
    }
  }

  return { size, modules, isFunction };
}

function applyMask(m, mask) {
  const { size, modules, isFunction } = m;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let invert;
      switch (mask) {
        case 0: invert = (x + y) % 2 === 0; break;
        case 1: invert = y % 2 === 0; break;
        case 2: invert = x % 3 === 0; break;
        case 3: invert = (x + y) % 3 === 0; break;
        case 4: invert = (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0; break;
        case 5: invert = ((x * y) % 2) + ((x * y) % 3) === 0; break;
        case 6: invert = (((x * y) % 2) + ((x * y) % 3)) % 2 === 0; break;
        case 7: invert = (((x + y) % 2) + ((x * y) % 3)) % 2 === 0; break;
      }
      if (!isFunction[y][x] && invert) modules[y][x] = !modules[y][x];
    }
  }
}

function penaltyScore(m) {
  const { size, modules } = m;
  const N1 = 3, N2 = 3, N3 = 40, N4 = 10;
  let result = 0;

  const countPatterns = (h) => {
    const n = h[1];
    const core = n > 0 && h[2] === n && h[3] === n * 3 && h[4] === n && h[5] === n;
    return (core && h[0] >= n * 4 && h[6] >= n ? 1 : 0) + (core && h[6] >= n * 4 && h[0] >= n ? 1 : 0);
  };
  const addHistory = (runLen, hist, firstIsInit) => {
    if (hist[0] === 0 && firstIsInit) runLen += size;
    hist.pop();
    hist.unshift(runLen);
  };

  for (let y = 0; y < size; y++) {
    let runColor = false, runX = 0;
    const hist = [0, 0, 0, 0, 0, 0, 0];
    let firstRun = true;
    for (let x = 0; x < size; x++) {
      if (modules[y][x] === runColor) {
        runX++;
        if (runX === 5) result += N1;
        else if (runX > 5) result++;
      } else {
        addHistory(runX, hist, firstRun);
        firstRun = false;
        if (!runColor) result += countPatterns(hist) * N3;
        runColor = modules[y][x];
        runX = 1;
      }
    }
    if (runColor) { addHistory(runX, hist, firstRun); firstRun = false; runX = 0; }
    runX += size;
    addHistory(runX, hist, firstRun);
    result += countPatterns(hist) * N3;
  }
  for (let x = 0; x < size; x++) {
    let runColor = false, runY = 0;
    const hist = [0, 0, 0, 0, 0, 0, 0];
    let firstRun = true;
    for (let y = 0; y < size; y++) {
      if (modules[y][x] === runColor) {
        runY++;
        if (runY === 5) result += N1;
        else if (runY > 5) result++;
      } else {
        addHistory(runY, hist, firstRun);
        firstRun = false;
        if (!runColor) result += countPatterns(hist) * N3;
        runColor = modules[y][x];
        runY = 1;
      }
    }
    if (runColor) { addHistory(runY, hist, firstRun); firstRun = false; runY = 0; }
    runY += size;
    addHistory(runY, hist, firstRun);
    result += countPatterns(hist) * N3;
  }
  for (let y = 0; y < size - 1; y++) {
    for (let x = 0; x < size - 1; x++) {
      const c = modules[y][x];
      if (c === modules[y][x + 1] && c === modules[y + 1][x] && c === modules[y + 1][x + 1]) result += N2;
    }
  }
  let dark = 0;
  for (const row of modules) for (const c of row) if (c) dark++;
  const total = size * size;
  const k = Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1;
  result += k * N4;
  return result;
}

// Redraw the final format bits for the chosen mask (after data+mask are in place).
function drawFinalFormat(m, ecl, mask) {
  const { size } = m;
  const setFn = (x, y, dark) => { m.modules[y][x] = dark; m.isFunction[y][x] = true; };
  const data = (ecl.formatBits << 3) | mask;
  let rem = data;
  for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
  const bits = ((data << 10) | rem) ^ 0x5412;
  for (let i = 0; i <= 5; i++) setFn(8, i, getBit(bits, i));
  setFn(8, 7, getBit(bits, 6));
  setFn(8, 8, getBit(bits, 7));
  setFn(7, 8, getBit(bits, 8));
  for (let i = 9; i < 15; i++) setFn(14 - i, 8, getBit(bits, i));
  for (let i = 0; i < 8; i++) setFn(size - 1 - i, 8, getBit(bits, i));
  for (let i = 8; i < 15; i++) setFn(8, size - 15 + i, getBit(bits, i));
  setFn(8, size - 8, true);
}

// Public: build the boolean module matrix for a UTF-8 string.
export function qrMatrix(text, opts = {}) {
  const ecl = ECC[opts.ecl || "M"] || ECC.M;
  const bytes = Array.from(Buffer.from(String(text), "utf8"));
  const ver = chooseVersion(bytes.length, ecl);
  const dataCw = makeDataCodewords(bytes, ver, ecl);
  const all = addEccAndInterleave(dataCw, ver, ecl);
  const m = buildMatrix(ver, ecl, all);

  // choose best mask
  let bestMask = 0, bestPenalty = Infinity;
  for (let mask = 0; mask < 8; mask++) {
    applyMask(m, mask);
    drawFinalFormat(m, ecl, mask);
    const p = penaltyScore(m);
    if (p < bestPenalty) { bestPenalty = p; bestMask = mask; }
    applyMask(m, mask); // undo (XOR is its own inverse)
  }
  applyMask(m, bestMask);
  drawFinalFormat(m, ecl, bestMask);

  return { size: m.size, modules: m.modules, version: ver, mask: bestMask, ecl: opts.ecl || "M" };
}

// Public: render a QR as a crisp, print-ready SVG string.
export function qrSvg(text, opts = {}) {
  const scale = opts.scale || 8;
  const border = opts.border == null ? 4 : opts.border;
  const { size, modules, version } = qrMatrix(text, opts);
  const dim = (size + border * 2) * scale;
  let rects = "";
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      if (modules[y][x]) rects += `M${(x + border) * scale},${(y + border) * scale}h${scale}v${scale}h-${scale}z`;
    }
  }
  return (
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<svg xmlns="http://www.w3.org/2000/svg" width="${dim}" height="${dim}" viewBox="0 0 ${dim} ${dim}" shape-rendering="crispEdges">\n` +
    `  <rect width="${dim}" height="${dim}" fill="#ffffff"/>\n` +
    `  <path d="${rects}" fill="#000000"/>\n` +
    `  <desc>QR v${version} — twin key shard</desc>\n` +
    `</svg>\n`
  );
}
