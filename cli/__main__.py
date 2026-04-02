"""
Memory Capsule CLI — for power users and scripts.

Usage:
  capsule add <file>                     Add a file
  capsule add --text "some text"         Add text directly
  capsule search "quote from Ahmed"      Search
  capsule list                           List recent capsules
  capsule status                         Show system status
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="capsule",
        description="Open Memory Capsule — capture everything, search naturally",
    )
    subparsers = parser.add_subparsers(dest="command")

    # capsule add
    add_parser = subparsers.add_parser("add", help="Add content to memory")
    add_parser.add_argument("file", nargs="?", help="File to add")
    add_parser.add_argument("--text", "-t", help="Text to add directly")
    add_parser.add_argument("--url", "-u", help="URL to capture")
    add_parser.add_argument("--sender", "-s", help="Who sent this (name)")
    add_parser.add_argument("--source", default="cli", help="Source app name")

    # capsule search
    search_parser = subparsers.add_parser("search", help="Search your memory")
    search_parser.add_argument("query", help="Natural language query")
    search_parser.add_argument("--limit", "-l", type=int, default=5)
    search_parser.add_argument("--source", help="Filter by source app")
    search_parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")

    # capsule list
    list_parser = subparsers.add_parser("list", help="List recent capsules")
    list_parser.add_argument("--limit", "-l", type=int, default=10)
    list_parser.add_argument("--source", help="Filter by source app")

    # capsule status
    subparsers.add_parser("status", help="Show system status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    asyncio.run(_dispatch(args))


async def _dispatch(args):
    if args.command == "add":
        await _cmd_add(args)
    elif args.command == "search":
        await _cmd_search(args)
    elif args.command == "list":
        await _cmd_list(args)
    elif args.command == "status":
        await _cmd_status()


async def _cmd_add(args):
    from config import get_config
    from capsule.store.sqlite import SQLiteStore
    from capsule.store.vector import VectorStore
    from capsule.pipeline import Pipeline
    from capsule.models import SourceApp

    cfg = get_config()
    pipeline = Pipeline(
        SQLiteStore(cfg.storage.sqlite_path),
        VectorStore(cfg.storage.chroma_path),
    )

    try:
        source_app = SourceApp(args.source)
    except ValueError:
        source_app = SourceApp.CLI

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        print(f"Processing {path.name}...")
        capsule = await pipeline.process_file(
            file_path=str(path),
            source_app=source_app,
            source_sender=args.sender,
        )

    elif args.text:
        print("Processing text...")
        capsule = await pipeline.process_text(
            text=args.text,
            source_app=source_app,
            source_sender=args.sender,
        )

    elif args.url:
        print(f"Capturing URL: {args.url}")
        capsule = await pipeline.process_text(
            text="",
            source_app=source_app,
            source_url=args.url,
        )

    else:
        print("Error: provide a file, --text, or --url", file=sys.stderr)
        sys.exit(1)

    print(f"\nCaptured:")
    print(f"  ID      : {capsule.id}")
    print(f"  Summary : {capsule.summary}")
    print(f"  Tags    : {', '.join(capsule.tags)}")
    if capsule.action_items:
        print(f"  Actions : {', '.join(capsule.action_items)}")


async def _cmd_search(args):
    from config import get_config
    from capsule.store.sqlite import SQLiteStore
    from capsule.store.vector import VectorStore
    from capsule.search.engine import SearchEngine

    cfg = get_config()
    engine = SearchEngine(
        SQLiteStore(cfg.storage.sqlite_path),
        VectorStore(cfg.storage.chroma_path),
    )

    results = await engine.search(
        query=args.query,
        limit=args.limit,
        source_app=args.source,
    )

    if args.as_json:
        print(json.dumps([{
            "id": r.capsule.id,
            "summary": r.capsule.summary,
            "tags": r.capsule.tags,
            "score": r.score,
            "source_app": r.capsule.source_app.value,
            "timestamp": r.capsule.timestamp.isoformat(),
            "snippet": r.snippet,
        } for r in results], indent=2))
        return

    if not results:
        print(f"No results for: {args.query}")
        return

    print(f"\nResults for: \"{args.query}\"\n")
    for i, r in enumerate(results, 1):
        c = r.capsule
        print(f"  {i}. [{c.source_app.value}] {c.timestamp.strftime('%Y-%m-%d %H:%M')}")
        if c.source_sender:
            print(f"     From   : {c.source_sender}")
        print(f"     Summary: {r.snippet}")
        if c.tags:
            print(f"     Tags   : {', '.join(c.tags)}")
        print(f"     Score  : {r.score:.2f}  |  ID: {c.id[:8]}...")
        print()


async def _cmd_list(args):
    from config import get_config
    from capsule.store.sqlite import SQLiteStore

    cfg = get_config()
    sqlite = SQLiteStore(cfg.storage.sqlite_path)
    capsules = sqlite.list(limit=args.limit, source_app=args.source)

    if not capsules:
        print("No capsules yet.")
        return

    print(f"\nRecent capsules ({len(capsules)}):\n")
    for c in capsules:
        print(f"  {c.timestamp.strftime('%Y-%m-%d %H:%M')}  [{c.source_app.value}]", end="")
        if c.source_sender:
            print(f"  from {c.source_sender}", end="")
        print()
        if c.summary:
            print(f"    {c.summary[:80]}")
        print()


async def _cmd_status():
    from config import get_config
    from capsule.store.sqlite import SQLiteStore
    from capsule.store.vector import VectorStore
    from providers import get_llm, get_embed

    cfg = get_config()

    print("\nMemory Capsule Status\n")
    print(f"  LLM       : {cfg.llm.model}")
    print(f"  Transcribe: {cfg.transcribe.model}")
    print(f"  Storage   : {cfg.storage.sqlite_path}")

    sqlite = SQLiteStore(cfg.storage.sqlite_path)
    vector = VectorStore(cfg.storage.chroma_path)
    print(f"  Capsules  : {sqlite.count()}")
    print(f"  Vectors   : {vector.count()}")

    llm_ok = await get_llm().health_check()
    embed_ok = await get_embed().health_check()
    print(f"  LLM       : {'ok' if llm_ok else 'UNREACHABLE'}")
    print(f"  Embeddings: {'ok' if embed_ok else 'UNREACHABLE'}")

    ig = cfg.integrations
    print(f"\n  Integrations:")
    print(f"    WhatsApp Personal : {'enabled' if ig.whatsapp_enabled else 'disabled'}")
    print(f"    WhatsApp Business : {'enabled' if ig.whatsapp_business_enabled else 'disabled'}")
    print(f"    Telegram          : {'enabled' if ig.telegram_enabled else 'disabled'}")
    print(f"    Email             : {'enabled' if ig.email_enabled else 'disabled'}")
    print(f"    Zoom              : {'enabled' if ig.zoom_enabled else 'disabled'}")
    print(f"    Watch Downloads   : {'enabled' if ig.watch_downloads else 'disabled'}")
    print(f"    Watch Screenshots : {'enabled' if ig.watch_screenshots else 'disabled'}")
    print()


if __name__ == "__main__":
    main()
