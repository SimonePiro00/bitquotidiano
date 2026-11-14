// Disegna i fotogrammi del Reel cartoon in Chromium (Playwright) e li passa a ffmpeg.
// Uso: node pipeline/cartoon/disegna.js copione.json uscita.mp4 [audio.wav]
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

(async () => {
  const [copioneFile, uscita, audio] = process.argv.slice(2);
  const copione = JSON.parse(fs.readFileSync(copioneFile, "utf8"));
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.join(__dirname, "scena.html"));
  await page.evaluate(c => window.prepara(c), copione);
  await page.evaluate(() => window.pronto());

  const solo = process.env.SOLO_FOTOGRAMMI;   // es. "0,90,200": salva solo questi come jpg (per le prove)
  const audioIn = audio && fs.existsSync(audio) ? ["-i", audio] : ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"];
  const ff = solo ? null : spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", String(copione.fps), "-i", "-",
    ...audioIn, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "medium",
    "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-shortest", "-movflags", "+faststart", uscita], { stdio: ["pipe", "inherit", "inherit"] });
  for (let n = 0; n < copione.frames; n++) {
    if (solo && !solo.split(",").includes(String(n))) continue;
    await page.evaluate(i => window.disegna(i), n);
    const jpg = await page.screenshot({ type: "jpeg", quality: 93 });
    if (solo) fs.writeFileSync(`${uscita}.${n}.jpg`, jpg);
    else if (!ff.stdin.write(jpg)) await new Promise(r => ff.stdin.once("drain", r));
  }
  if (ff) {
    ff.stdin.end();
    await new Promise((ok, ko) => ff.on("close", c => (c ? ko(new Error("ffmpeg ha fallito")) : ok())));
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
