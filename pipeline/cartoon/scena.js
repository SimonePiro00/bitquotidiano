/* Reel "cartoon" di Bit Quotidiano: ogni fotogramma è un SVG disegnato da disegna(n).
 *
 * Il copione (window.prepara) arriva da pipeline/reel_cartoon.py: testi, icone, scene con i loro
 * fotogrammi di inizio e fine, e il volume della voce per ogni fotogramma (fa muovere la bocca di Bit).
 * Tutto è originale: Bit, le icone e le animazioni sono disegnati qui, niente materiale di terzi.
 */
const W = 1080, H = 1920;
const C = { bg: "#09112A", scuro: "#1C2B55", medio: "#2A3D72", fg: "#F2F5FA", muted: "#8796B4", acc: "#FF7A1A", acc2: "#FFB066" };
let S = null;            // copione
const misura = document.createElement("canvas").getContext("2d");

// ---------- utilità ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const easeOut = k => 1 - Math.pow(1 - clamp(k), 3);
const easeInOut = k => (k = clamp(k), k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const easeBack = k => { k = clamp(k); const c = 1.9; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); };
const elastic = k => { k = clamp(k); return k === 0 || k === 1 ? k : Math.pow(2, -10 * k) * Math.sin((k * 10 - 0.75) * (2 * Math.PI / 3)) + 1; };
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const pulito = s => s.replace(/\*/g, "");

function larghezza(testo, size, peso = 700) {
  misura.font = `${peso} ${size}px Fredoka`;
  return misura.measureText(testo).width;
}

/** Divide in righe un testo con parole *evidenziate*; ogni parola: {p, acc, x, riga}. */
function impagina(testo, size, maxW, peso = 700) {
  const parole = [];
  let acc = false;
  for (const tok of testo.split(/\s+/).filter(Boolean)) {
    let p = tok;
    if (p.startsWith("*")) acc = true;
    const chiude = /\*[^\w]*$/.test(p.slice(1)) || (p.length > 1 && /^\*.*\*/.test(p));
    parole.push({ p: p.replace(/\*/g, ""), acc });
    if (chiude) acc = false;
  }
  const spazio = larghezza(" ", size, peso);
  let x = 0, riga = 0;
  for (const w of parole) {
    const lw = larghezza(w.p, size, peso);
    if (x > 0 && x + lw > maxW) { x = 0; riga++; }
    w.x = x; w.w = lw; w.riga = riga;
    x += lw + spazio;
  }
  return { parole, righe: riga + 1 };
}

// ---------- Bit, la mascotte animata ----------
/* opz: x,y (piedi), s (scala), t (secondi), bocca 0..1, umore ("felice"|"preoccupato"|"sorpreso"|"ammicca"),
 *      bs/bd angolo braccio sinistro/destro in gradi (0 = giù, 150 = alzato), tilt (gradi), squash, guarda [dx,dy] */
function bit(o) {
  const t = o.t, s = o.s || 1, sq = o.squash || 0;
  const blink = o.umore !== "sorpreso" && ((t + 1.5) % 3.1) < 0.12;
  const gx = (o.guarda || [0, 0])[0] * 9, gy = (o.guarda || [0, 0])[1] * 7;
  const antenna = 7 * Math.sin(t * 7.5) + (o.tilt || 0) * -1.2;
  const occhioRy = o.umore === "sorpreso" ? 36 : 30;
  const occhi = (cx) => {
    if (blink) return `<rect x="${cx - 23}" y="236" width="46" height="9" rx="4.5" fill="${C.fg}"/>`;
    if (o.umore === "ammicca" && cx > 300) return `<path d="M${cx - 22} 244 Q${cx} 226 ${cx + 22} 244" stroke="${C.fg}" stroke-width="9" fill="none" stroke-linecap="round"/>`;
    return `<ellipse cx="${cx}" cy="240" rx="23" ry="${occhioRy}" fill="${C.fg}"/>
            <circle cx="${cx + 4 + gx}" cy="${236 + gy}" r="${o.umore === "sorpreso" ? 7 : 9}" fill="${C.bg}"/>
            <circle cx="${cx + 9 + gx}" cy="${229 + gy}" r="3.5" fill="#fff"/>`;
  };
  const sopracciglia = {
    felice: [[228, 196, 272, 190], [328, 190, 372, 196]],
    preoccupato: [[226, 190, 272, 200], [328, 200, 374, 190]],
    sorpreso: [[226, 182, 272, 176], [328, 176, 374, 182]],
    ammicca: [[228, 194, 272, 190], [328, 202, 372, 202]],
  }[o.umore || "felice"].map(([x1, y1, x2, y2]) =>
    `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${C.fg}" stroke-width="9" stroke-linecap="round"/>`).join("");
  const b = clamp(o.bocca || 0);
  let bocca;
  if (o.umore === "sorpreso" && b < 0.15) bocca = `<ellipse cx="300" cy="300" rx="16" ry="18" fill="${C.acc}"/>`;
  else if (b < 0.08) bocca = o.umore === "preoccupato"
    ? `<path d="M270 304 Q300 290 330 304" stroke="${C.acc}" stroke-width="10" fill="none" stroke-linecap="round"/>`
    : `<path d="M262 288 Q300 322 338 288" stroke="${C.acc}" stroke-width="10" fill="none" stroke-linecap="round"/>`;
  else bocca = `<path d="M${270 - 8 * b} 290 Q300 ${292 + 50 * b} ${330 + 8 * b} 290 Z" fill="${C.acc}" stroke="${C.acc}" stroke-width="8" stroke-linejoin="round"/>
                <path d="M${284 - 4 * b} ${294 + 18 * b} Q300 ${300 + 30 * b} ${316 + 4 * b} ${294 + 18 * b}" fill="#C4510A" opacity="${b > 0.3 ? 0.9 : 0}"/>`;
  const braccio = (sx, sy, ang, lato) => {
    const a = ang * Math.PI / 180, L = 108;
    const hx = sx + lato * Math.sin(a) * L, hy = sy + Math.cos(a) * L;
    const mx = (sx + hx) / 2 + lato * Math.cos(a) * 16, my = (sy + hy) / 2 - Math.sin(a) * 10;
    return `<path d="M${sx} ${sy} Q${mx} ${my} ${hx} ${hy}" stroke="${C.fg}" stroke-width="14" fill="none" stroke-linecap="round"/>
            <circle cx="${hx}" cy="${hy}" r="20" fill="${C.acc}" stroke="${C.fg}" stroke-width="6"/>`;
  };
  const cursore = (t % 0.8) < 0.45 ? `<rect x="306" y="462" width="34" height="8" rx="3" fill="${C.acc}"/>` : "";
  const piedi = o.piedi || 0;   // >0 durante i salti: le gambe si ritraggono
  return `<g transform="translate(${o.x} ${o.y}) scale(${s * (1 + sq)} ${s * (1 - sq)}) translate(-300 -560)">
    <ellipse cx="300" cy="566" rx="${150 - 60 * piedi}" ry="16" fill="#000" opacity="${0.35 - 0.2 * piedi}" transform="translate(0 ${piedi * 40}) scale(1 1)"/>
    <g transform="translate(0 ${-piedi * 40})">
      <rect x="236" y="${508 - piedi * 6}" width="36" height="${52 - piedi * 8}" rx="13" fill="${C.muted}" stroke="${C.fg}" stroke-width="5"/>
      <rect x="328" y="${508 - piedi * 6}" width="36" height="${52 - piedi * 8}" rx="13" fill="${C.muted}" stroke="${C.fg}" stroke-width="5"/>
      ${braccio(207, 425, o.bs ?? 20, -1)}
      ${braccio(393, 430, o.bd ?? 20, 1)}
      <rect x="196" y="382" width="208" height="136" rx="44" fill="${C.scuro}" stroke="${C.fg}" stroke-width="10"/>
      <text x="268" y="472" font-family="DejaVu Sans Mono" font-weight="bold" font-size="58" fill="${C.acc}">&gt;</text>
      ${cursore}
      <g transform="rotate(${o.tilt || 0} 300 380)">
        <g transform="rotate(${antenna} 300 132)">
          <line x1="300" y1="132" x2="300" y2="70" stroke="${C.muted}" stroke-width="11" stroke-linecap="round"/>
          <circle cx="300" cy="60" r="${22 + 3 * Math.sin(t * 6)}" fill="${C.acc}" stroke="${C.fg}" stroke-width="5"/>
          <circle cx="293" cy="53" r="6" fill="#fff" opacity="0.7"/>
        </g>
        <rect x="146" y="128" width="308" height="250" rx="66" fill="${C.scuro}" stroke="${C.fg}" stroke-width="11"/>
        <rect x="182" y="162" width="236" height="178" rx="40" fill="${C.bg}"/>
        <path d="M200 182 Q210 170 228 168" stroke="${C.medio}" stroke-width="8" fill="none" stroke-linecap="round"/>
        ${occhi(250)}${occhi(350)}
        ${sopracciglia}
        <ellipse cx="212" cy="292" rx="17" ry="10" fill="${C.acc}" opacity="0.55"/>
        <ellipse cx="388" cy="292" rx="17" ry="10" fill="${C.acc}" opacity="0.55"/>
        ${bocca}
      </g>
    </g>
  </g>`;
}

// ---------- icone animate (box 400x400 centrato in 0,0) ----------
const OUT = `stroke="${C.fg}" stroke-width="10" stroke-linejoin="round" stroke-linecap="round"`;
const ICONE = {
  qr(t) {
    const pel = 0.5 + 0.5 * Math.sin(t * 4);   // l'angolo dell'adesivo si solleva e ricade
    let celle = "";
    const pat = [0b1110111, 0b1010101, 0b1110111, 0b0001000, 0b1101011, 0b0110110, 0b1011101];
    pat.forEach((r, i) => { for (let j = 0; j < 7; j++) if (r >> (6 - j) & 1) celle += `<rect x="${-112 + j * 32}" y="${-112 + i * 32}" width="30" height="30" rx="4" fill="${C.bg}"/>`; });
    const p = 70 + 40 * pel;
    return `<g transform="rotate(-6)">
      <rect x="-150" y="-150" width="300" height="300" rx="26" fill="${C.fg}" stroke="${C.fg}" stroke-width="10"/>
      ${celle}
      <path d="M150 ${150 - p} L150 150 L${150 - p} 150 Z" fill="${C.bg}"/>
      <path d="M150 ${150 - p} L${150 - p} 150 L${150 - p * 0.62} ${150 - p * 0.62} Z" fill="${C.acc}" ${OUT}/>
      <rect x="-190" y="-196" width="120" height="44" rx="12" fill="${C.acc}" transform="rotate(-12 -130 -174)"/>
      <text x="-130" y="-163" font-size="30" font-weight="700" fill="${C.bg}" text-anchor="middle" transform="rotate(-12 -130 -174)">FALSO</text>
    </g>`;
  },
  carta(t) {
    const su = 26 * Math.sin(t * 3.2), rot = 6 * Math.sin(t * 3.2 + 0.6);
    return `<line x1="40" y1="-260" x2="40" y2="${-92 + su}" stroke="${C.muted}" stroke-width="6"/>
      <g transform="translate(0 ${su}) rotate(${rot})">
        <path d="M40 -92 L40 -40 Q40 -6 12 -6 Q-14 -6 -14 -30" stroke="${C.fg}" stroke-width="12" fill="none" stroke-linecap="round"/>
        <path d="M-14 -30 L-28 -14 M-14 -30 L0 -16" stroke="${C.fg}" stroke-width="10" stroke-linecap="round"/>
        <g transform="rotate(-10) translate(0 40)">
          <rect x="-170" y="-20" width="340" height="210" rx="26" fill="${C.acc}" ${OUT}/>
          <rect x="-170" y="30" width="340" height="40" fill="${C.bg}" opacity="0.85"/>
          <rect x="-130" y="96" width="70" height="52" rx="10" fill="${C.acc2}" stroke="${C.bg}" stroke-width="5"/>
          <text x="-40" y="160" font-size="34" font-weight="700" fill="${C.bg}">•••• 4821</text>
        </g>
      </g>`;
  },
  telefono(t) {
    const pop = elastic(clamp((t % 2.4) / 0.6));
    return `<g transform="rotate(${4 * Math.sin(t * 2)})">
      <rect x="-120" y="-200" width="240" height="400" rx="36" fill="${C.scuro}" ${OUT}/>
      <rect x="-96" y="-160" width="192" height="300" rx="14" fill="${C.bg}"/>
      ${[0, 1, 2].map(r => [0, 1, 2].map(c => `<rect x="${-80 + c * 58}" y="${-140 + r * 62}" width="44" height="44" rx="12" fill="${(r * 3 + c) === 4 ? C.acc : C.medio}"/>`).join("")).join("")}
      <rect x="-30" y="168" width="60" height="10" rx="5" fill="${C.muted}"/>
      <g transform="translate(110 -170) scale(${pop})">
        <circle r="62" fill="${C.acc}" ${OUT}/>
        <path d="M-28 2 L-8 22 L30 -20" stroke="${C.bg}" stroke-width="14" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </g>`;
  },
  stop(t) {
    const w = 8 * Math.sin(t * 9) * Math.max(0, Math.sin(t * 1.6));
    const pts = [...Array(8)].map((_, i) => { const a = Math.PI / 8 + i * Math.PI / 4; return `${170 * Math.cos(a)},${170 * Math.sin(a)}`; }).join(" ");
    return `<g transform="rotate(${w})">
      <rect x="-12" y="120" width="24" height="120" rx="8" fill="${C.muted}" stroke="${C.fg}" stroke-width="6"/>
      <polygon points="${pts}" fill="${C.acc}" ${OUT}/>
      <text y="22" font-size="80" font-weight="700" fill="${C.bg}" text-anchor="middle">STOP</text>
    </g>`;
  },
  avviso(t) {
    const sc = 1 + 0.06 * Math.sin(t * 8);
    return `<g transform="rotate(${5 * Math.sin(t * 11)}) scale(${sc})">
      <path d="M0 -170 L180 140 L-180 140 Z" fill="${C.acc}" ${OUT} stroke-width="14"/>
      <rect x="-16" y="-70" width="32" height="130" rx="16" fill="${C.bg}"/>
      <circle cy="100" r="20" fill="${C.bg}"/>
    </g>`;
  },
  lucchetto(t) {
    const ch = easeBack(clamp(((t % 2.6) - 0.3) / 0.5));
    return `<path d="M-90 ${-30 - 50 * (1 - ch)} L-90 -90 Q-90 -180 0 -180 Q90 -180 90 -90 L90 ${-30 - 50 * (1 - ch) + 40 * (1 - ch)}" stroke="${C.fg}" stroke-width="34" fill="none" stroke-linecap="round"/>
      <rect x="-150" y="-40" width="300" height="230" rx="40" fill="${C.acc}" ${OUT}/>
      <circle cy="50" r="28" fill="${C.bg}"/><rect x="-11" y="56" width="22" height="64" rx="10" fill="${C.bg}"/>`;
  },
  chat(t) {
    const pallini = [0, 1, 2].map(i => `<circle cx="${-50 + i * 50}" cy="${130 + -10 * Math.max(0, Math.sin(t * 8 - i))}" r="16" fill="${C.muted}"/>`).join("");
    return `<path d="M-180 -170 H180 Q200 -170 200 -150 V20 Q200 40 180 40 H-90 L-150 90 L-140 40 H-180 Q-200 40 -200 20 V-150 Q-200 -170 -180 -170 Z" fill="${C.fg}" ${OUT}/>
      <text y="-90" font-size="40" font-weight="500" fill="${C.bg}" text-anchor="middle">Il tuo codice:</text>
      <text y="-10" font-size="74" font-weight="700" fill="${C.acc}" text-anchor="middle" letter-spacing="6">${(t % 1.2) < 0.6 ? "482 913" : "••• •••"}</text>
      <rect x="-100" y="100" width="200" height="60" rx="30" fill="${C.scuro}" stroke="${C.fg}" stroke-width="6"/>${pallini}`;
  },
  pacco(t) {
    const salta = Math.abs(Math.sin(t * 4)) * 30;
    return `<g transform="translate(0 ${-salta})">
      <path d="M-160 -60 L0 -130 L160 -60 L160 130 L0 190 L-160 130 Z" fill="#C98A4B" ${OUT}/>
      <path d="M-160 -60 L0 10 L160 -60 M0 10 L0 190" stroke="${C.fg}" stroke-width="10" fill="none"/>
      <path d="M-80 -96 L80 -26" stroke="${C.acc2}" stroke-width="22"/>
      <circle cx="120" cy="-130" r="58" fill="${C.acc}" ${OUT}/>
      <text x="120" y="-108" font-size="68" font-weight="700" fill="${C.bg}" text-anchor="middle">?</text>
    </g>`;
  },
  link(t) {
    const sep = 18 + 18 * Math.max(0, Math.sin(t * 3));
    return `<g transform="rotate(-30)">
      <rect x="${-190 - sep}" y="-60" width="200" height="120" rx="60" fill="none" stroke="${C.fg}" stroke-width="30"/>
      <rect x="${-10 + sep}" y="-60" width="200" height="120" rx="60" fill="none" stroke="${C.acc}" stroke-width="30"/>
    </g>
    <circle cx="140" cy="-150" r="52" fill="${C.acc}" ${OUT}/><text x="140" y="-128" font-size="64" font-weight="700" fill="${C.bg}" text-anchor="middle">!</text>`;
  },
  soldi(t) {
    let m = "";
    for (let i = 0; i < 4; i++) {
      const f = ((t * 0.9 + i * 0.25) % 1);
      m += `<g transform="translate(${-100 + i * 66} ${-40 - f * 220}) scale(${1 - f * 0.4})" opacity="${1 - f}">
        <circle r="44" fill="${C.acc2}" stroke="${C.fg}" stroke-width="7"/><text y="16" font-size="46" font-weight="700" fill="${C.bg}" text-anchor="middle">€</text></g>`;
    }
    return `${m}<path d="M-170 40 Q-170 -10 -120 -10 H120 Q170 -10 170 40 V160 Q170 200 120 200 H-120 Q-170 200 -170 160 Z" fill="${C.scuro}" ${OUT}/>
      <rect x="60" y="60" width="130" height="80" rx="20" fill="${C.acc}" ${OUT}/>`;
  },
  batteria(t) {
    const liv = 0.15 + 0.1 * Math.sin(t * 5);
    return `<rect x="-110" y="-200" width="220" height="380" rx="36" fill="${C.scuro}" ${OUT}/>
      <rect x="-40" y="-236" width="80" height="36" rx="10" fill="${C.fg}"/>
      <rect x="-80" y="${150 - 320 * liv}" width="160" height="${320 * liv}" rx="18" fill="${C.acc}"/>
      <path d="M20 -120 L-40 10 L10 10 L-20 110 L50 -30 L0 -30 Z" fill="${C.acc2}" stroke="${C.fg}" stroke-width="6" stroke-linejoin="round" opacity="${0.6 + 0.4 * Math.sin(t * 7)}"/>`;
  },
};
const icona = (nome, t) => (ICONE[nome] || ICONE.avviso)(t);

// ---------- elementi comuni ----------
function sfondo(t) {
  let s = `<rect width="${W}" height="${H}" fill="${C.bg}"/>
    <defs><radialGradient id="alone"><stop offset="0" stop-color="${C.medio}" stop-opacity="0.75"/><stop offset="1" stop-color="${C.bg}" stop-opacity="0"/></radialGradient></defs>
    <circle cx="${540 + 60 * Math.sin(t * 0.7)}" cy="900" r="720" fill="url(#alone)"/>`;
  // bit che salgono lentamente: 0, 1 e piccoli segni +
  for (let i = 0; i < 22; i++) {
    const x = (i * 197 + 61) % W, v = 30 + (i * 37) % 50;
    const y = H - ((t * v + i * 311) % (H + 100));
    const g = ["0", "1", "+", "•"][i % 4];
    s += `<text x="${x + 20 * Math.sin(t + i)}" y="${y}" font-size="${34 + (i % 3) * 14}" font-weight="700" fill="${C.scuro}" opacity="0.9">${g}</text>`;
  }
  return s;
}

function aereo(x, y, sc, rot) {
  return `<g transform="translate(${x} ${y}) rotate(${rot}) scale(${sc})">
    <path d="M-30 -24 L34 0 L-30 24 L-18 0 Z" fill="${C.bg}" stroke="${C.bg}" stroke-width="5" stroke-linejoin="round"/>
    <path d="M-18 0 L34 0" stroke="${C.acc}" stroke-width="4"/></g>`;
}

/** Pillola in alto "Mandalo a ...": visibile dal primo fotogramma, ogni tanto saltella. */
function pillola(t, alfa = 1) {
  const testo = pulito(S.invio);
  const size = 46, tw = larghezza(testo, size), w = tw + 130, x = 60, y = 150;
  const ciclo = t % 2.5, salto = ciclo < 0.5 ? Math.sin(ciclo / 0.5 * Math.PI) : 0;
  return `<g opacity="${alfa}" transform="translate(${x} ${y - 14 * salto}) rotate(${-2 * salto} 0 45)">
    <rect x="6" y="10" width="${w}" height="92" rx="46" fill="#000" opacity="0.3"/>
    <rect width="${w}" height="92" rx="46" fill="${C.acc}" stroke="${C.fg}" stroke-width="6"/>
    ${aereo(58, 46, 1.05, -12 + 14 * salto)}
    <text x="100" y="62" font-size="${size}" font-weight="700" fill="${C.bg}">${esc(testo)}</text>
  </g>`;
}

/** Testo con parole che entrano a scatti (k = secondi dall'inizio della scena; k<0 = tutte già visibili).
 *  Sottotitoli: kara = [[da, a], ...] fotogrammi in cui ogni parola viene detta; la parola detta in quel
 *  momento si accende in un riquadro arancio, così chi guarda senza audio segue la voce. */
function testo(str, x, y, size, maxW, k, colore = C.fg, ritmo = 0.07, kara = null, n = 0, peso = 700) {
  const { parole, righe } = impagina(str, size, maxW, peso);
  let out = "";
  parole.forEach((w, i) => {
    const e = k < 0 ? 1 : easeBack((k - i * ritmo) / 0.28);
    if (e <= 0.001) return;
    const px = x + w.x, py = y + w.riga * size * 1.12;
    const kk = kara && kara[i];
    const ora = kk && n >= kk[0] && n < kk[1];
    const kpop = ora ? 1 + 0.05 * easeBack((n - kk[0]) / 4) : 1;
    const sc = (0.4 + 0.6 * e) * kpop;
    const cx = px + w.w / 2, cy = py - size * 0.35;
    const fill = ora ? C.bg : w.acc ? C.acc : colore;
    const box = ora ? `<rect x="${px - 8}" y="${py - size * 0.86}" width="${w.w + 16}" height="${size * 1.08}" rx="${size * 0.22}" fill="${w.acc ? C.fg : C.acc}"/>` : "";
    out += `<g transform="translate(${cx} ${cy}) scale(${sc}) translate(${-cx} ${-cy})" opacity="${clamp(e * 1.5)}">${box}
      <text x="${px}" y="${py}" font-size="${size}" font-weight="${peso}" fill="${fill}" ${ora ? "" : `stroke="${C.bg}" stroke-width="12" paint-order="stroke"`}>${esc(w.p)}</text></g>`;
  });
  return { svg: out, fondo: y + (righe - 1) * size * 1.12, n: parole.length };
}

function lineeVelocita(t, alfa) {
  if (alfa <= 0) return "";
  let s = "";
  for (let i = 0; i < 9; i++) {
    const y = 300 + i * 160 + 40 * Math.sin(i * 7), l = 200 + (i * 83) % 260;
    s += `<rect x="${(i * 211 + t * 3000) % (W + 400) - 400}" y="${y}" width="${l}" height="10" rx="5" fill="${C.fg}" opacity="${0.25 * alfa}"/>`;
  }
  return s;
}

// ---------- scene ----------
function scenaGancio(sc, k, t, b) {
  const kara = sc.parole || null;
  const tx = testo(S.gancio, 60, 420, 96, 900, -1, C.fg, 0, kara, Math.round(t * S.fps));
  const an = testo(S.annuncio, 60, tx.fondo + 110, 54, 900, -1, C.acc, 0, kara && kara.slice(tx.n), Math.round(t * S.fps));
  const fr = 22 * Math.abs(Math.sin(t * 4));
  // fumetto "!" che pulsa vicino alla testa di Bit
  const pop = 1 + 0.12 * Math.sin(t * 8);
  return `${tx.svg}
    ${an.svg}
    <g transform="translate(${105 + larghezza(S.annuncio, 54)} ${an.fondo - 18 + fr * 0.5})">
      <path d="M0 -26 L0 18 M-16 4 L0 20 L16 4" stroke="${C.acc}" stroke-width="9" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>
    <g transform="translate(710 1250) rotate(${-8 + 4 * Math.sin(t * 2.5)}) scale(0.82)">${icona(S.icona_gancio, t)}</g>
    ${bit({ x: 300, y: 1600 - 10 * Math.abs(Math.sin(t * 3)), s: 0.95, t, bocca: b, umore: "preoccupato", bs: 150 + 12 * Math.sin(t * 6), bd: 70, tilt: 6 * Math.sin(t * 1.7), guarda: [1, -0.3], squash: 0.02 * Math.sin(t * 6) })}
    <g transform="translate(150 960) scale(${pop})">
      <path d="M-60 -58 H60 Q76 -58 76 -42 V36 Q76 52 60 52 H-6 L-36 82 L-30 52 H-60 Q-76 52 -76 36 V-42 Q-76 -58 -60 -58 Z" fill="${C.fg}" stroke="${C.bg}" stroke-width="6"/>
      <text y="26" font-size="86" font-weight="700" fill="${C.acc}" text-anchor="middle">!?</text></g>`;
}

function badge(n, k, attivo) {
  const e = attivo ? elastic(k / 0.7) : 1;
  return `<g transform="translate(130 395) scale(${e}) rotate(${(1 - e) * -40})">
    <circle r="74" fill="${C.acc}" stroke="${C.fg}" stroke-width="8"/>
    <text y="34" font-size="100" font-weight="700" fill="${C.bg}" text-anchor="middle">${n}</text></g>`;
}

function puntini(n) {
  return S.punti.map((_, i) => `<circle cx="${780 + i * 56}" cy="395" r="${i === n ? 20 : 14}" fill="${i <= n ? C.acc : C.scuro}" stroke="${C.fg}" stroke-width="${i <= n ? 5 : 3}"/>`).join("");
}

function scenaPunto(sc, k, t, b) {
  const i = sc.i, p = S.punti[i];
  const ultimo = i === S.punti.length - 1;
  const e = easeBack(k / 0.45);
  const tremo = ultimo ? 6 * Math.sin(t * 30) * Math.max(0, 1 - k / 0.6) : 0;
  const tx = testo(p.testo, 60, 1080, 88, 940, k - 0.1, ultimo ? C.acc : C.fg, 0.07, sc.parole, Math.round(t * S.fps));
  const titolo = `${S.serie}${S.titolo ? " · " + S.titolo : ""}`;
  const pose = [{ bs: 30, bd: 140, umore: "felice", guarda: [1, -1] },
                { bs: 150, bd: 30, umore: "ammicca", guarda: [1, -1] },
                { bs: 160, bd: 160, umore: "sorpreso", guarda: [0.5, -1] }][Math.min(i, 2)];
  return `${badge(i + 1, k, true)}
    <text x="232" y="380" font-size="42" font-weight="500" fill="${C.muted}">${esc(titolo)}</text>
    <text x="232" y="430" font-size="42" font-weight="700" fill="${C.fg}">${ultimo ? "Il più subdolo" : "Segnale " + (i + 1)}</text>
    ${puntini(i)}
    <g transform="translate(${540 + tremo} 730) scale(${0.25 + 0.75 * e}) rotate(${(1 - e) * 25})">
      <circle r="250" fill="${C.scuro}" opacity="0.8"/>${icona(p.icona, t)}</g>
    ${tx.svg}
    ${bit({ x: 250, y: 1680 - 60 * Math.max(0, Math.sin(clamp(k / 0.5) * Math.PI)), s: 0.72, t, bocca: b, ...pose,
           bs: pose.bs + 10 * Math.sin(t * 5), tilt: 8 * Math.sin(t * 2.2), squash: k < 0.12 ? 0.08 : 0.015 * Math.sin(t * 6),
           piedi: Math.max(0, Math.sin(clamp(k / 0.5) * Math.PI)) })}`;
}

function scenaFine(sc, k, t, b) {
  const tx = testo(S.invio, 60, 480, 104, 940, k, C.fg, 0.06, sc.parole, Math.round(t * S.fps));
  // aeroplanino che parte dalla mano di Bit e vola in alto a destra, in loop
  const v = (k % 1.6) / 1.6;
  const ax = lerp(560, 1200, easeInOut(v)), ay = lerp(1260, 250, easeInOut(v)) - 120 * Math.sin(v * Math.PI);
  let scia = "";
  for (let j = 1; j < 9; j++) {
    const vv = Math.max(0, v - j * 0.025);
    scia += `<circle cx="${lerp(560, 1200, easeInOut(vv))}" cy="${lerp(1260, 250, easeInOut(vv)) - 120 * Math.sin(vv * Math.PI)}" r="${8 - j * 0.7}" fill="${C.fg}" opacity="${0.5 - j * 0.05}"/>`;
  }
  const btnY = Math.max(tx.fondo + 110, 860);
  const pul = 1 + 0.05 * Math.sin(t * 7);
  const segui = "+ Segui per la prossima";
  const bw = larghezza(segui, 54) + 90;
  const tocco = ((k + 0.4) % 1.2) < 0.25;
  const salto = Math.abs(Math.sin(t * 5));
  return `${tx.svg}
    <g transform="translate(${60 + bw / 2} ${btnY + 55}) scale(${pul * (tocco ? 0.94 : 1)})">
      <rect x="${-bw / 2}" y="-55" width="${bw}" height="110" rx="55" fill="${C.acc}" stroke="${C.fg}" stroke-width="7"/>
      <text y="19" font-size="54" font-weight="700" fill="${C.bg}" text-anchor="middle">${segui}</text></g>
    <g transform="translate(${60 + bw - 40} ${btnY + 90 + (tocco ? 0 : 18)}) rotate(-20)">
      <path d="M0 0 L0 -20 Q0 -36 14 -36 Q28 -36 28 -20 L28 30 L60 22 Q78 20 80 38 L80 80 Q80 110 50 116 L10 116 Q-10 110 -18 90 L-40 40 Q-46 26 -32 22 Q-20 18 -10 30 L0 44 Z" fill="${C.fg}" stroke="${C.bg}" stroke-width="6" stroke-linejoin="round"/></g>
    ${scia}${`<g transform="translate(${ax} ${ay}) rotate(-38) scale(2.6)"><path d="M-30 -24 L34 0 L-30 24 L-18 0 Z" fill="${C.fg}" stroke="${C.bg}" stroke-width="3" stroke-linejoin="round"/><path d="M-18 0 L34 0" stroke="${C.acc}" stroke-width="4"/></g>`}
    ${bit({ x: 330, y: 1640 - 70 * salto, s: 0.9, t, bocca: b, umore: "felice", bs: 165 + 18 * Math.sin(t * 12), bd: 120, tilt: -6, guarda: [1, -1],
           squash: salto < 0.15 ? 0.07 : -0.03, piedi: salto })}`;
}


// ================== stile "palco" ==================
/* Bit su un piccolo palco illuminato; accanto a lui compaiono icone ed etichette-timbro.
 * Sotto, una fascia di sottotitoli grandi, 1-3 parole alla volta, con la parola detta evidenziata. */
function parseParole(str) { return impagina(str, 10, 1e9).parole.map(w => ({ p: w.p, acc: w.acc })); }

function paroleScena(sc) {
  if (sc.tipo === "gancio") return parseParole(S.gancio).concat(parseParole(S.annuncio));
  if (sc.tipo === "punto") return parseParole(S.punti[sc.i].testo).map(w => ({ ...w, acc: w.acc || sc.i === S.punti.length - 1 && false }));
  return parseParole(S.invio).concat(parseParole(S.segui || ""));
}

function blocchi(parole) {
  const out = [];
  let cur = [];
  parole.forEach((w, i) => {
    cur.push(i);
    const lettere = cur.reduce((a, j) => a + parole[j].p.length + 1, 0);
    if (cur.length >= 3 || lettere > 15 || /[.,:;?!]$/.test(w.p)) { out.push(cur); cur = []; }
  });
  if (cur.length) out.push(cur);
  return out;
}

function sottotitoli(sc, n) {
  const parole = paroleScena(sc), kara = sc.parole || [];
  if (sc.suspense && n < sc.voce_da) {   // attesa prima del terzo: domanda in sovrimpressione
    const p = 1 + 0.06 * Math.sin(n / 2);
    return `<text x="540" y="1500" font-size="${96 * p}" font-weight="700" fill="${C.acc}" text-anchor="middle" stroke="${C.bg}" stroke-width="14" paint-order="stroke">E IL TERZO…</text>`;
  }
  if (!parole.length || n < (kara[0] || [0])[0]) return "";
  let ora = kara.findIndex(([a, b]) => n >= a && n < b);
  if (ora < 0) ora = n >= (kara[kara.length - 1] || [0, 0])[1] ? parole.length - 1 : -1;
  if (ora < 0) return "";
  const blocco = blocchi(parole).find(b => b.includes(ora));
  const size = 96, spazio = 26;
  const larg = blocco.map(j => larghezza(parole[j].p.toUpperCase(), size));
  const tot = larg.reduce((a, b) => a + b, 0) + spazio * (blocco.length - 1);
  const scala = Math.min(1, 940 / tot);
  const inizioBlocco = kara[blocco[0]] ? kara[blocco[0]][0] : 0;
  const ent = n - inizioBlocco < 0 ? 1 : easeBack((n - inizioBlocco) / 5);
  let x = 540 - tot * scala / 2, out = "";
  blocco.forEach((j, q) => {
    const w = parole[j], lw = larg[q] * scala, attiva = j === ora;
    const testoW = esc(w.p.toUpperCase());
    if (attiva) out += `<rect x="${x - 12}" y="${1500 - size * scala * 0.86}" width="${lw + 24}" height="${size * scala * 1.1}" rx="18" fill="${w.acc ? C.fg : C.acc}" transform="rotate(-2 ${x + lw / 2} 1500)"/>`;
    out += `<text x="${x}" y="1500" font-size="${size * scala}" font-weight="700" fill="${attiva ? C.bg : w.acc ? C.acc : C.fg}"
      ${attiva ? "" : `stroke="${C.bg}" stroke-width="14" paint-order="stroke"`}>${testoW}</text>`;
    x += lw + spazio * scala;
  });
  return `<g transform="translate(540 1470) scale(${0.85 + 0.15 * ent}) translate(-540 -1470)">${out}</g>`;
}

function palco(t) {
  return `<defs>
      <radialGradient id="faro" cx="0.5" cy="0" r="1"><stop offset="0" stop-color="${C.acc2}" stop-opacity="0.28"/><stop offset="0.6" stop-color="${C.acc}" stop-opacity="0.05"/><stop offset="1" stop-color="${C.bg}" stop-opacity="0"/></radialGradient>
      <radialGradient id="pavimento"><stop offset="0" stop-color="${C.medio}" stop-opacity="0.95"/><stop offset="1" stop-color="${C.bg}" stop-opacity="0"/></radialGradient>
    </defs>
    <polygon points="380,330 700,330 1040,1250 40,1250" fill="url(#faro)" opacity="${0.85 + 0.15 * Math.sin(t * 2)}"/>
    <ellipse cx="540" cy="1250" rx="560" ry="90" fill="url(#pavimento)"/>
    <rect x="0" y="1340" width="${W}" height="250" fill="#050A1C" opacity="0.75"/>`;
}

function timbro(testo, x, y, k, rot = -8, pieno = false, size = 54) {
  testo = testo.toUpperCase();
  let tw = larghezza(testo, size);
  if (tw + 52 > 900) { size = size * 848 / tw; tw = larghezza(testo, size); }
  x = clamp(x, (tw + 52) / 2 + 50, W - (tw + 52) / 2 - 50);
  const e = elastic(k / 0.6);
  const box = `<rect x="${-tw / 2 - 26}" y="${-size * 0.95}" width="${tw + 52}" height="${size * 1.45}" rx="16"
      fill="${pieno ? C.acc : C.bg}" stroke="${C.acc}" stroke-width="7"/>`;
  return `<g transform="translate(${x} ${y}) rotate(${rot}) scale(${e > 0 ? 0.3 + 0.7 * e : 0})" opacity="${clamp(k / 0.1)}">${box}
    <text y="0" font-size="${size}" font-weight="700" fill="${pieno ? C.bg : C.acc}" text-anchor="middle">${esc(testo)}</text></g>`;
}

function etichetta(testo, x, y) {
  const size = 40, tw = larghezza(testo, size);
  return `<g transform="translate(${x} ${y})"><rect width="${tw + 40}" height="64" rx="12" fill="${C.bg}" stroke="${C.fg}" stroke-width="4"/>
    <text x="20" y="45" font-size="${size}" font-weight="700" fill="${C.fg}">${esc(testo)}</text></g>`;
}

/* Pannello dei 3 segnali: quelli non ancora detti restano coperti ("???"), il terzo ha un lucchetto.
 * È il motivo per restare: si vede subito che c'è qualcosa da scoprire. */
function pannello(rivelati, attivo, k, t, x0, y0, w, sblocco = 1) {
  let out = "";
  const h = 92, gap = 18;
  S.punti.forEach((p, j) => {
    const y = y0 + j * (h + gap), visto = j < rivelati, ora = j === attivo;
    const terzo = j === S.punti.length - 1;
    const pop = ora ? easeBack(k / 0.35) : 1;
    const bordo = ora ? C.acc : terzo && !visto ? C.acc : C.muted;
    let contenutoRiga;
    if (visto) {
      const size = Math.min(48, 48 * (w - 150) / Math.max(1, larghezza(p.testo, 48)));
      contenutoRiga = `<text x="118" y="${h / 2 + size * 0.36}" font-size="${size}" font-weight="700" fill="${ora ? C.bg : C.fg}">${esc(p.testo)}</text>`;
    } else {
      const lamp = 0.5 + 0.5 * Math.sin(t * 6 - j);
      contenutoRiga = `<rect x="118" y="${h / 2 - 14}" width="${w - 260}" height="28" rx="14" fill="${C.medio}" opacity="${0.6 + 0.3 * lamp}"/>
        <text x="${w - 120}" y="${h / 2 + 17}" font-size="48" font-weight="700" fill="${C.acc}">???</text>`;
      if (terzo) {
        const tr = (1 - sblocco) * 10 * Math.sin(t * 40) + 3 * Math.sin(t * 9);
        contenutoRiga += `<g transform="translate(${w - 175} ${h / 2}) rotate(${tr}) scale(0.16)">${ICONE.lucchetto(0.2)}</g>`;
      }
    }
    out += `<g transform="translate(${x0} ${y}) translate(${w / 2} ${h / 2}) scale(${0.85 + 0.15 * pop}) translate(${-w / 2} ${-h / 2})">
      <rect width="${w}" height="${h}" rx="22" fill="${ora ? C.acc : C.bg}" stroke="${bordo}" stroke-width="${ora ? 7 : 5}" ${!visto && !ora ? 'stroke-dasharray="14 10"' : ""}/>
      <circle cx="56" cy="${h / 2}" r="32" fill="${visto || ora ? (ora ? C.bg : C.acc) : C.scuro}" stroke="${C.fg}" stroke-width="4"/>
      <text x="56" y="${h / 2 + 15}" font-size="42" font-weight="700" fill="${ora ? C.acc : visto ? C.bg : C.muted}" text-anchor="middle">${j + 1}</text>
      ${contenutoRiga}</g>`;
  });
  return out;
}

function palcoGancio(sc, k, t, b) {
  const tx = testo(S.gancio, 60, 450, 80, 960, -1);
  const pop = 1 + 0.1 * Math.sin(t * 8);
  return `${tx.svg}
    <g transform="translate(730 ${1000 + 10 * Math.sin(t * 3)}) rotate(${-6 + 4 * Math.sin(t * 2.5)}) scale(0.62)">${icona(S.icona_gancio, t)}</g>
    ${timbro(S.annuncio, 640, 740, k + 0.6, 4, true, 40)}
    ${bit({ x: 290, y: 1250, s: 0.72, t, bocca: b, umore: "preoccupato", bs: 150 + 12 * Math.sin(t * 6), bd: 70, tilt: 6 * Math.sin(t * 1.7), guarda: [1, -0.2], squash: 0.02 * Math.sin(t * 6) })}
    <g transform="translate(300 ${790}) scale(${pop})"><circle r="48" fill="${C.fg}"/><text y="24" font-size="70" font-weight="700" fill="${C.acc}" text-anchor="middle">?</text></g>`;
}

function palcoPunto(sc, k, t, b) {
  const i = sc.i, p = S.punti[i], ultimo = i === S.punti.length - 1;
  const e = easeBack(k / 0.45);
  const tremo = ultimo ? 8 * Math.sin(t * 30) * Math.max(0, 1 - k / 0.7) : 0;
  const pose = [{ bs: 30, bd: 140, umore: "felice" }, { bs: 150, bd: 30, umore: "ammicca" }, { bs: 160, bd: 160, umore: "sorpreso" }][Math.min(i, 2)];
  const salto = Math.max(0, Math.sin(clamp(k / 0.5) * Math.PI));
  // titoletti già visti in piccolo, come "ricordo" dei punti precedenti
  let ricordi = "";
  for (let j = 0; j < i; j++) ricordi += `<g opacity="0.55">${etichetta(`${j + 1}. ${S.punti[j].testo}`, 60, 330 + j * 80)}</g>`;
  return `${ricordi}
    <g transform="translate(60 ${330 + i * 80})">${badgePiccolo(i + 1, k)}</g>
    <g transform="translate(${710 + tremo} 1000) scale(${(0.25 + 0.75 * e) * 0.66}) rotate(${(1 - e) * 25})">${icona(p.icona, t)}</g>
    ${timbro(p.testo, 640, 700, k - 0.25, ultimo ? 4 : -5, ultimo, 52)}
    ${bit({ x: 270, y: 1250 - 70 * salto, s: 0.72, t, bocca: b, ...pose, guarda: [1, -0.6], bs: pose.bs + 10 * Math.sin(t * 5),
           tilt: 8 * Math.sin(t * 2.2), squash: k < 0.12 ? 0.08 : 0.015 * Math.sin(t * 6), piedi: salto })}`;
}

function badgePiccolo(n, k) {
  const e = elastic(k / 0.6);
  return `<g transform="translate(36 32) scale(${e})"><circle r="40" fill="${C.acc}" stroke="${C.fg}" stroke-width="5"/>
    <text y="18" font-size="52" font-weight="700" fill="${C.bg}" text-anchor="middle">${n}</text></g>`;
}

function campanella(t) {
  const r = 18 * Math.sin(t * 18) * Math.max(0, Math.sin(t * 2.5));
  return `<g transform="rotate(${r} 0 -40)">
    <path d="M-34 14 Q-34 -40 0 -44 Q34 -40 34 14 L44 26 L-44 26 Z" fill="${C.bg}" stroke="${C.bg}" stroke-width="6" stroke-linejoin="round"/>
    <circle cy="36" r="10" fill="${C.bg}"/><circle cy="-48" r="7" fill="${C.bg}"/></g>`;
}

function palcoFine(sc, k, t, b) {
  const salto = Math.abs(Math.sin(t * 5));
  const tocco = ((k + 0.3) % 1.1) < 0.22, pul = 1 + 0.05 * Math.sin(t * 7);
  const e = easeBack(k / 0.5);
  const card = `<g transform="translate(540 640) scale(${(0.3 + 0.7 * e) * pul * (tocco ? 0.95 : 1)})">
      <rect x="-440" y="-170" width="880" height="340" rx="48" fill="${C.acc}" stroke="${C.fg}" stroke-width="9"/>
      <g transform="translate(-330 -40) scale(1.5)">${campanella(t)}</g>
      <text x="-230" y="-30" font-size="96" font-weight="700" fill="${C.bg}">SEGUI</text>
      <text x="-230" y="50" font-size="54" font-weight="700" fill="${C.bg}">${esc(S.prossima ? "per la " + S.prossima : "per la prossima")}</text>
      <text x="0" y="128" font-size="40" font-weight="500" fill="${C.bg}" text-anchor="middle">@bitquotidiano.it</text></g>`;
  const mano = `<g transform="translate(${800} ${640 + (tocco ? 0 : 24)}) rotate(-20)">
      <path d="M0 0 L0 -20 Q0 -36 14 -36 Q28 -36 28 -20 L28 30 L60 22 Q78 20 80 38 L80 80 Q80 110 50 116 L10 116 Q-10 110 -18 90 L-40 40 Q-46 26 -32 22 Q-20 18 -10 30 L0 44 Z" fill="${C.fg}" stroke="${C.bg}" stroke-width="6" stroke-linejoin="round"/></g>`;
  let coriandoli = "";
  for (let j = 0; j < 18; j++) {
    const f = ((k * 0.7 + j * 0.13) % 1);
    coriandoli += `<rect x="${(j * 151) % W}" y="${300 + f * 1000}" width="18" height="10" rx="3" fill="${j % 3 ? C.acc : C.fg}" opacity="${0.8 * (1 - f)}" transform="rotate(${t * 300 + j * 40} ${(j * 151) % W} ${300 + f * 1000})"/>`;
  }
  return `${coriandoli}
    ${testo(S.invio, 60, 370, Math.min(70, 70 * 960 / larghezza(pulito(S.invio), 70)), 960, k, C.fg, 0.05).svg}
    ${card}${mano}
    ${bit({ x: 330, y: 1260 - 60 * salto, s: 0.6, t, bocca: b, umore: "felice", bs: 165 + 18 * Math.sin(t * 12), bd: 150, tilt: -6, guarda: [1, -1],
           squash: salto < 0.15 ? 0.07 : -0.03, piedi: salto })}`;
}
const PALCO = { gancio: palcoGancio, punto: palcoPunto, fine: palcoFine };

const DISEGNA = { gancio: scenaGancio, punto: scenaPunto, fine: scenaFine };

function contenuto(sc, n) {
  const k = (n - sc.da) / S.fps, t = n / S.fps;
  const b = S.bocca[n] || 0;
  const pill = sc.tipo === "fine" ? "" : pillola(t);
  if (S.stile === "palco") {
    const zoom = 1;
    const scena = PALCO[sc.tipo](sc, k, t, b);
    return palco(t) + `<g transform="translate(540 900) scale(${zoom}) translate(-540 -900)">${scena}</g>` + sottotitoli(sc, n) + pill;
  }
  return DISEGNA[sc.tipo](sc, k, t, b) + pill;
}

// ---------- API usata da disegna.js ----------
window.prepara = (copione) => { S = copione; };
window.pronto = () => document.fonts.ready.then(() => document.fonts.load("700 40px Fredoka")).then(() => document.fonts.load("500 40px Fredoka")).then(() => true);

window.disegna = (n) => {
  const t = n / S.fps;
  const idx = S.scene.findIndex(s => n >= s.da && n < s.a);
  const sc = S.scene[idx < 0 ? S.scene.length - 1 : idx];
  let corpo = contenuto(sc, n);
  // Transizione a fumetto: una banda arancio spazza lo schermo e scopre la scena nuova.
  const TR = Math.round(0.32 * S.fps);
  const prec = S.scene[idx - 1];
  if (prec && n - sc.da < TR) {
    const k = (n - sc.da) / TR;
    const fronte = lerp(-300, W + 500, easeInOut(k));
    const vecchio = contenuto(prec, n);
    corpo = `<defs><clipPath id="nuovo"><polygon points="-400,0 ${fronte},0 ${fronte - 300},${H} -400,${H}"/></clipPath>
               <clipPath id="vecchio"><polygon points="${fronte},0 ${W + 900},0 ${W + 900},${H} ${fronte - 300},${H}"/></clipPath></defs>
      <g clip-path="url(#vecchio)">${vecchio}</g><g clip-path="url(#nuovo)">${corpo}</g>
      <polygon points="${fronte - 60},0 ${fronte + 30},0 ${fronte - 270},${H} ${fronte - 360},${H}" fill="${C.acc}"/>
      <polygon points="${fronte + 50},0 ${fronte + 70},0 ${fronte - 230},${H} ${fronte - 250},${H}" fill="${C.fg}"/>`;
  }
  const vel = prec && n - sc.da < TR * 1.6 ? 1 - (n - sc.da) / (TR * 1.6) : 0;
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${sfondo(t)}${lineeVelocita(t, vel)}${corpo}`;
  // Barra di avanzamento in alto.
  svg += `<rect width="${W}" height="12" fill="${C.scuro}"/><rect width="${W * n / S.frames}" height="12" fill="${C.acc}"/>`;
  // Ultimi fotogrammi: dissolvenza verso il primo, così il loop del Reel non si nota.
  const coda = Math.round(0.25 * S.fps);
  if (n >= S.frames - coda) {
    const a = (n - (S.frames - coda)) / coda;
    svg += `<g opacity="${a}">${sfondo(0)}${contenuto(S.scene[0], 0)}</g>`;
  }
  document.getElementById("scena").innerHTML = svg + "</svg>";
  return true;
};
