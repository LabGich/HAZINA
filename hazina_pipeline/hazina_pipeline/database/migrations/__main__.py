
import sys

from hazina_pipeline.database.migrations.manager import (
    MigrationError,
    run_migrations,
)


def main() -> int:
    print("Hazina database migration manager")
    print("---------------------------------")

    try:
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
