"""Pipeline: osserva la pagina sorgente, crea bozze in italiano, pubblica solo dopo approvazione.

Uso:
  python run.py check                 # cerca nuovi post e crea le bozze (non pubblica nulla)
  python run.py list                  # elenca le bozze e il loro stato
  python run.py publish ID --conferma # pubblica una bozza approvata
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
    from pipeline.illustrate import draw
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
        out = DRAFTS_DIR / post["id"]
        bozza = generate_draft(post)
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
        record = {"stato": "in_attesa", "fonte": post["permalink"], "bozza": bozza.model_dump()}
        (out / "bozza.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
        seen.add(post["id"])
        save_seen(seen)
        print(f"Bozza creata: {out}")


def cmd_list(args):
    for f in sorted(DRAFTS_DIR.glob("*/bozza.json")):
        r = json.loads(f.read_text())
        print(f"{f.parent.name}  [{r['stato']}]  {r['bozza']['argomento']}")


def cmd_publish(args):
    from pipeline.publish import publish_carousel

    if not args.conferma:
        sys.exit("Aggiungi --conferma per pubblicare davvero.")
    folder = DRAFTS_DIR / args.id
    record = json.loads((folder / "bozza.json").read_text())
    if record["stato"] == "pubblicata":
        sys.exit("Bozza già pubblicata.")
    base = env("PUBLIC_IMAGE_BASE_URL", required=True).rstrip("/")
    slides = sorted(folder.glob("slide_*.jpg"), key=lambda p: int(p.stem.split("_")[1]))
    urls = [f"{base}/{args.id}/{p.name}" for p in slides]
    b = record["bozza"]
    caption = b["didascalia"] + "\n\n" + " ".join(f"#{h}" for h in b["hashtag"])
    record["media_id"] = publish_carousel(urls, caption)
    record["stato"] = "pubblicata"
    (folder / "bozza.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(f"Pubblicato: {record['media_id']}")


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
    sub.add_parser("list").set_defaults(fn=cmd_list)
    pb = sub.add_parser("publish"); pb.add_argument("id"); pb.add_argument("--conferma", action="store_true"); pb.set_defaults(fn=cmd_publish)
    d = sub.add_parser("demo"); d.add_argument("file"); d.add_argument("--out", default="esempi"); d.set_defaults(fn=cmd_demo)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
