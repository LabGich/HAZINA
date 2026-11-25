
import argparse
import sys

from hazina_pipeline.database.migrations.manager import (
    MigrationError,
    baseline_existing_database,
    run_migrations,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hazina database migration manager"
    )
    parser.add_argument(
        "--baseline-existing",
        action="store_true",
        help=(
            "Register the existing database's migrations without "
            "executing their SQL. Use only after verifying that all "
            "migrations were previously applied successfully."
        ),
    )
    args = parser.parse_args()

    print("Hazina database migration manager")
    print("---------------------------------")

    try:
        if args.baseline_existing:
            adopted = baseline_existing_database()

            print("\nExisting database successfully adopted.")
            print("Registered migrations:")

            for filename in adopted:
                print(f"  BASELINED  {filename}")

            print(f"\nTotal baseline entries: {len(adopted)}")
            print("No migration SQL was executed.")
            return 0

        summary = run_migrations()

        if summary.applied:
            print("\nSuccessfully applied migrations:")
            for filename in summary.applied:
                print(f"  APPLIED  {filename}")
        else:
            print("\nNo pending migrations.")

        print(
            f"\nApplied during this run: {summary.applied_count}"
        )
        print(
            "Already applied: "
            f"{len(summary.already_applied)}"
        )
        print("\nDatabase migrations completed successfully.")
        return 0

    except MigrationError as exc:
        print(f"\nMIGRATION FAILED: {exc}", file=sys.stderr)
        return 1

    except Exception as exc:
        print(
            f"\nUNEXPECTED ERROR: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
