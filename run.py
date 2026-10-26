"""Pipeline: osserva la pagina sorgente, crea bozze in italiano, pubblica solo dopo approvazione.

Uso:
  python run.py check                 # cerca nuovi post e crea le bozze (non pubblica nulla)
  python run.py piano [--giorni N]    # crea le bozze del calendario editoriale da domani
  python run.py list                  # elenca le bozze e il loro stato
  python run.py publish ID --conferma # pubblica una bozza approvata
  python run.py leggi "LINK1 LINK2" --account NOME  # scarica testo e immagini di post indicati
  python run.py analisi --dal AAAA-MM-GG --al AAAA-MM-GG  # risultati dei post pubblicati nel periodo
  python run.py reel ID [ID...]      # crea reel.mp4 dalle slide della bozza (voce: pip install piper-tts)
  python run.py demo FILE.json        # disegna le slide da una bozza di esempio, senza API
"""
import argparse
import json
import sys
from pathlib import Path

from pipeline.config import DRAFTS_DIR, env
from pipeline.render import render_draft


def cmd_check(args):
    from pipeline.generate import generate_draft
    from pipeline.monitor import fetch_recent_media, load_seen, new_posts, save_seen

    seen = load_seen()
    media = fetch_recent_media()
    if not seen:
        # Primo avvio: segna come già visti i post esistenti, così si parte dai post futuri.
        # Con --backfill N si generano comunque bozze di prova dagli N post più recenti.
        recent = sorted(media, key=lambda m: m["timestamp"], reverse=True)[: args.backfill]
        seen = {m["id"] for m in media} - {m["id"] for m in recent}
        save_seen(seen)
        print(f"Primo avvio: {len(seen)} post segnati come già visti, {len(recent)} in elaborazione.")
    todo = new_posts(media, seen)
    if args.rigenera:
        ids = {i.strip() for i in args.rigenera.split(",") if i.strip()}
        todo += [m for m in media if m["id"] in ids and m not in todo]
    for post in todo:
        _salva_bozza(DRAFTS_DIR / post["id"], generate_draft(post), post["permalink"])
        seen.add(post["id"])
        save_seen(seen)


def _salva_bozza(out: Path, bozza, fonte: str) -> None:
    """Disegna illustrazioni e slide della bozza in `out` e la salva in attesa di approvazione."""
    from pipeline.illustrate import draw

    for old in [*out.glob("slide_*.jpg"), *out.glob("illustrazione_*.png")]:
        old.unlink()
    out.mkdir(parents=True, exist_ok=True)
    disegnate = 0
    for k, slide in enumerate(bozza.slides):
        if slide.illustrazione and disegnate < 5:
            ill = draw(slide.illustrazione, f"{slide.titolo}. {slide.testo}")
            if ill is not None:
                ill.save(out / f"illustrazione_{k}.png")
                disegnate += 1
    print(f"Illustrazioni disegnate: {disegnate}")
    render_draft(bozza, out, env("BRAND_HANDLE", "@bitquotidiano.it"))
    record = {"stato": "in_attesa", "fonte": fonte, "bozza": bozza.model_dump()}
    (out / "bozza.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(f"Bozza creata: {out}")


def cmd_piano(args):
    """Crea le bozze del calendario editoriale per i prossimi giorni (da domani), una per giorno con angolo."""
    from datetime import date, timedelta

    from pipeline.calendario import CALENDARIO
    from pipeline.generate import generate_from_angle

    inizio = date.fromisoformat(args.data) if args.data else date.today() + timedelta(days=1)
    for i in range(args.giorni):
        giorno = inizio + timedelta(days=i)
        angolo = CALENDARIO[giorno.weekday()]
        out = DRAFTS_DIR / f"cal-{giorno.isoformat()}"
        if angolo is None:
            print(f"{giorno}: giorno libero, nessuna bozza dal calendario.")
            continue
        if (out / "bozza.json").exists() and not args.rigenera:
            print(f"{giorno}: bozza già presente ({out.name}).")
            continue
        gia_fatti = [json.loads(f.read_text())["bozza"]["argomento"] for f in DRAFTS_DIR.glob("*/bozza.json")]
        bozza = generate_from_angle(angolo, giorno.isoformat(), gia_fatti)
        _salva_bozza(out, bozza, f"calendario: {angolo.nome} ({giorno.isoformat()})")


def cmd_list(args):
    for f in sorted(DRAFTS_DIR.glob("*/bozza.json")):
        r = json.loads(f.read_text())
        print(f"{f.parent.name}  [{r['stato']}]  {r['bozza']['argomento']}")


def _attendi_pages(files: list[Path], urls: list[str], tentativi: int = 30) -> None:
    """Instagram scarica le immagini da GitHub Pages: prima di pubblicare controlla che Pages
    serva già la versione attuale di ogni file, altrimenti uscirebbero slide vecchie."""
    import time
    import requests

    for _ in range(tentativi):
        vecchi = [u for f, u in zip(files, urls)
                  if requests.get(u, timeout=30, headers={"Cache-Control": "no-cache"}).content != f.read_bytes()]
        if not vecchi:
            return
        print(f"Pages non è ancora aggiornato ({len(vecchi)} file), riprovo tra 20 secondi...")
        time.sleep(20)
    sys.exit("GitHub Pages serve ancora immagini vecchie: pubblicazione annullata.")


def cmd_publish(args):
    from pipeline.publish import publish_carousel, publish_reel, publish_story

    if not args.conferma:
        sys.exit("Aggiungi --conferma per pubblicare davvero.")
    folder = DRAFTS_DIR / args.id
    record = json.loads((folder / "bozza.json").read_text())
    story, reel = folder / "story.jpg", folder / "reel.mp4"
    fai_post = record["stato"] != "pubblicata"
    fai_storia = story.exists() and not args.senza_storia and not record.get("story_id")
    fai_reel = reel.exists() and not args.senza_reel and not record.get("reel_id")
    if not (fai_post or fai_storia or fai_reel):
        sys.exit("Bozza già pubblicata.")
    base = env("PUBLIC_IMAGE_BASE_URL", required=True).rstrip("/")
    slides = sorted(folder.glob("slide_*.jpg"), key=lambda p: int(p.stem.split("_")[1]))
    urls = [f"{base}/{args.id}/{p.name}" for p in slides]
    files = slides + [f for f, usa in [(story, fai_storia), (reel, fai_reel)] if usa]
    _attendi_pages(files, [f"{base}/{args.id}/{p.name}" for p in files])
    b = record["bozza"]
    hashtag = " ".join(f"#{h}" for h in b["hashtag"])
    salva = lambda: (folder / "bozza.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    if fai_post:
        record["media_id"] = publish_carousel(urls, b["didascalia"] + "\n\n" + hashtag)
        record["stato"] = "pubblicata"
        salva()
        print(f"Post pubblicato: {record['media_id']}")
    else:
        print(f"Post già pubblicato ({record.get('media_id')}).")
    if fai_storia:
        record["story_id"] = publish_story(f"{base}/{args.id}/story.jpg")
        salva()
        print(f"Storia pubblicata: {record['story_id']}")
    if fai_reel:
        # La didascalia del Reel parte dal titolo, così non si confonde con quella del carosello.
        titolo = b["slides"][0]["titolo"]
        record["reel_id"] = publish_reel(f"{base}/{args.id}/reel.mp4", f"{titolo}\n\n{b['didascalia']}\n\n{hashtag}")
        salva()
        print(f"Reel pubblicato: {record['reel_id']}")


def cmd_reel(args):
    from pipeline.reel import make_reel

    for id_ in args.id:
        folder = DRAFTS_DIR / id_
        b = json.loads((folder / "bozza.json").read_text())["bozza"]
        print(make_reel(folder, b["slides"]))


def cmd_leggi(args):
    from pipeline.fonti import salva

    salva(args.account.lstrip("@"), [l for l in args.link.replace(",", " ").split() if l])


def cmd_analisi(args):
    from pipeline.analisi import analizza

    risultato = analizza(args.dal, args.al)
    out = Path("analisi") / f"{args.dal}_{args.al}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(risultato, ensure_ascii=False, indent=2))
    print(json.dumps(risultato, ensure_ascii=False, indent=2))


def cmd_demo(args):
    from pipeline.generate import Bozza

    bozza = Bozza.model_validate(json.loads(Path(args.file).read_text()))
    out = Path(args.out)
    paths = render_draft(bozza, out, env("BRAND_HANDLE", "@bitquotidiano.it"))
    print("\n".join(str(p) for p in paths))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--backfill", type=int, default=0); c.add_argument("--rigenera", default=""); c.set_defaults(fn=cmd_check)
    pn = sub.add_parser("piano"); pn.add_argument("--giorni", type=int, default=1); pn.add_argument("--data", default=""); pn.add_argument("--rigenera", action="store_true"); pn.set_defaults(fn=cmd_piano)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    pb = sub.add_parser("publish"); pb.add_argument("id"); pb.add_argument("--conferma", action="store_true"); pb.add_argument("--senza-storia", action="store_true"); pb.add_argument("--senza-reel", action="store_true"); pb.set_defaults(fn=cmd_publish)
    lg = sub.add_parser("leggi"); lg.add_argument("link"); lg.add_argument("--account", default="technologybrief"); lg.set_defaults(fn=cmd_leggi)
    an = sub.add_parser("analisi"); an.add_argument("--dal", required=True); an.add_argument("--al", required=True); an.set_defaults(fn=cmd_analisi)
    rl = sub.add_parser("reel"); rl.add_argument("id", nargs="+"); rl.set_defaults(fn=cmd_reel)
    d = sub.add_parser("demo"); d.add_argument("file"); d.add_argument("--out", default="esempi"); d.set_defaults(fn=cmd_demo)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
