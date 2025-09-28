"""Orchestrate the foreclosure processing pipeline."""

from __future__ import annotations

import argparse
import importlib
import sys
from typing import Callable, Dict

from settings import ensure_directories


def run_scraper():
    module = importlib.import_module("LOCAL_oc_records_search")
    module.main()


def run_vision():
    from vision_docs import process_all_pdfs_in_directory
    from settings import CASE_DOCS_DIR, OUTPUT_DIR

    ensure_directories()
    process_all_pdfs_in_directory(CASE_DOCS_DIR, OUTPUT_DIR)


def run_prompt_builder():
    from prompt_builder import create_combination_text
    from settings import OUTPUT_DIR

    ensure_directories()
    create_combination_text(OUTPUT_DIR)


def run_vertex():
    import vertex_processor  # pylint: disable=unused-import


def run_style_foreclosure():
    import get_style_foreclosure  # pylint: disable=unused-import


def run_appraiser():
    import get_appraiser_data  # pylint: disable=unused-import


def run_all_appraiser():
    import get_all_appraiser_data  # pylint: disable=unused-import


def run_zillow():
    import get_zillow_data  # pylint: disable=unused-import


def run_firestore_upload():
    import manual_firestore_uploader  # pylint: disable=unused-import


def run_assign_record_id():
    import init_record_id  # pylint: disable=unused-import


def run_mark_start():
    import new_start_script  # pylint: disable=unused-import


def run_mark_finish():
    import f  # pylint: disable=unused-import


PIPELINE_STEPS: Dict[str, Callable[[], None]] = {
    "scrape": run_scraper,
    "vision": run_vision,
    "prompt": run_prompt_builder,
    "vertex": run_vertex,
    "style": run_style_foreclosure,
    "appraiser": run_appraiser,
    "appraiser_all": run_all_appraiser,
    "zillow": run_zillow,
    "firestore": run_firestore_upload,
    "assign_record_id": run_assign_record_id,
    "mark_start": run_mark_start,
    "mark_finish": run_mark_finish,
}


ORDERED_STEPS = [
    "scrape",
    "vision",
    "prompt",
    "vertex",
    "style",
    "appraiser",
    "appraiser_all",
    "zillow",
    "mark_start",
    "firestore",
    "assign_record_id",
    "mark_finish",
]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the foreclosure processing pipeline.")
    parser.add_argument(
        "steps",
        nargs="*",
        choices=list(PIPELINE_STEPS.keys()) + ["all"],
        default=["all"],
        help="Specific steps to run in order; default runs the full pipeline.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    ensure_directories()

    steps = ORDERED_STEPS if "all" in args.steps else args.steps

    for step in steps:
        action = PIPELINE_STEPS[step]
        print(f"\n=== Running step: {step} ===")
        action()

    print("\nPipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
