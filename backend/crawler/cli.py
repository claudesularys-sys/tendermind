"""
TenderMind Crawler CLI

Usage:
  python -m crawler.cli list
  python -m crawler.cli test sam_gov
  python -m crawler.cli test ted_eu --limit 10
  python -m crawler.cli run goszakup_kz
  python -m crawler.cli new my_source AU asia --country-name Australia
"""
import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path


def cmd_list(_args):
    from crawler.registry import get_all_crawlers
    crawlers = get_all_crawlers()
    if not crawlers:
        print("No crawlers found.")
        return
    print(f"\n{'Source ID':<28} {'CC':<5} {'Region':<15} {'Schedule'}")
    print("─" * 65)
    for sid, c in sorted(crawlers.items()):
        print(f"{sid:<28} {c.country_code:<5} {c.region:<15} {c.schedule}")
    print(f"\nTotal: {len(crawlers)} sources registered\n")


def cmd_test(args):
    from crawler.registry import get_crawler
    from crawler.plugin import test_crawler

    crawler = get_crawler(args.source_id)
    if not crawler:
        print(f"\n❌  Source '{args.source_id}' not found.")
        print("   Run: python -m crawler.cli list\n")
        sys.exit(1)

    print(f"\n🔍  Testing {args.source_id} — dry run (no DB writes)...\n")

    result = asyncio.run(test_crawler(crawler, limit=args.limit))

    icon = "✅" if result.ok else "❌"
    print(f"{icon}  {result.source_id}")
    print(f"    Fetched : {result.fetched}")
    print(f"    Valid   : {result.valid}")
    if result.invalid:
        print(f"    Invalid : {result.invalid}")

    if result.errors:
        print(f"\n⚠️   Validation errors ({len(result.errors)}):")
        for e in result.errors:
            print(f"    · {e}")

    if result.sample:
        today = date.today()
        print(f"\n📋  Sample ({len(result.sample)} tenders):")
        for t in result.sample:
            days = (t.deadline - today).days
            deadline_color = "🔴" if days <= 7 else "🟡" if days <= 30 else "🟢"
            print(f"\n    🆔  {t.external_id}")
            print(f"    📌  {t.title[:80]}{'…' if len(t.title) > 80 else ''}")
            print(f"    🌍  {t.country_name}{f'  ·  {t.city}' if t.city else ''}")
            print(f"    {deadline_color}  {t.deadline}  ({days} days left)")
            print(f"    🔗  {t.url[:80]}{'…' if len(t.url) > 80 else ''}")
            if t.budget_usd:
                print(f"    💰  ~${t.budget_usd:,.0f}")
    print()


def cmd_run(args):
    from crawler.registry import get_crawler
    from crawler.pipeline import process_tenders
    from crawler.base import CrawlResult

    crawler = get_crawler(args.source_id)
    if not crawler:
        print(f"\n❌  Source '{args.source_id}' not found.\n")
        sys.exit(1)

    print(f"\n🚀  Running {args.source_id} → saving to DB...\n")

    async def _run():
        result, tenders = await crawler.run()
        print(f"    Fetched : {result.fetched}  |  Status: {result.status}")
        if result.error_msg:
            print(f"    Error   : {result.error_msg}")
        if result.status == "ok" and tenders:
            await process_tenders(tenders, result)
        print(f"    New     : {result.new_tenders}")
        print(f"    Matched : {result.matched}")
        print()

    asyncio.run(_run())


def cmd_new(args):
    regions = {"americas", "europe", "asia", "cis", "mena", "international"}
    if args.region not in regions:
        print(f"\n❌  Unknown region '{args.region}'.")
        print(f"   Valid: {', '.join(sorted(regions))}\n")
        sys.exit(1)

    template = Path(__file__).parent / "sources" / "_template.py"
    if not template.exists():
        print(f"\n❌  Template not found: {template}\n")
        sys.exit(1)

    target_dir = Path(__file__).parent / "sources" / args.region
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{args.source_id}.py"

    if target_file.exists():
        print(f"\n❌  File already exists: {target_file}\n")
        sys.exit(1)

    country_name = args.country_name or args.country_code.upper()
    content = (
        template.read_text()
        .replace("TEMPLATE_SOURCE_ID", args.source_id)
        .replace("TEMPLATE_COUNTRY_CODE", args.country_code.upper())
        .replace("TEMPLATE_COUNTRY_NAME", country_name)
        .replace("TEMPLATE_REGION", args.region)
    )
    target_file.write_text(content)

    print(f"\n✅  Created: {target_file}")
    print(f"\nNext steps:")
    print(f"  1. Open {target_file}")
    print(f"  2. Set base_url, implement fetch_tenders() and _normalize()")
    print(f"  3. Test:  python -m crawler.cli test {args.source_id}")
    print(f"  4. Run:   python -m crawler.cli run  {args.source_id}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="python -m crawler.cli",
        description="TenderMind crawler management",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("list", help="List all registered crawlers")

    p_test = sub.add_parser("test", help="Dry-run a crawler (no DB writes)")
    p_test.add_argument("source_id")
    p_test.add_argument("--limit", type=int, default=5, metavar="N",
                        help="Number of sample tenders to show (default: 5)")

    p_run = sub.add_parser("run", help="Run a crawler and save results to DB")
    p_run.add_argument("source_id")

    p_new = sub.add_parser("new", help="Generate a new source file from template")
    p_new.add_argument("source_id", help="snake_case ID, e.g. austender_au")
    p_new.add_argument("country_code", help="ISO 3166-1 alpha-2, e.g. AU")
    p_new.add_argument("region",
                       help="americas | europe | asia | cis | mena | international")
    p_new.add_argument("--country-name", dest="country_name", default="",
                       help="Display name, e.g. 'Australia' (defaults to country_code)")

    args = parser.parse_args()
    {
        "list": cmd_list,
        "test": cmd_test,
        "run": cmd_run,
        "new": cmd_new,
    }.get(args.command, lambda _: parser.print_help())(args)


if __name__ == "__main__":
    main()
