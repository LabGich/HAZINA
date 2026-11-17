
import getpass
import sys

from server.auth.password import hash_password
from server.services.auth_service import AuthService


def prompt_required(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print(f"{label} is required.")


def prompt_password() -> str:
    while True:
        password = getpass.getpass("Admin password (minimum 12 characters): ")

        if len(password) < 12:
            print("Password must contain at least 12 characters.")
            continue

        confirmation = getpass.getpass("Confirm admin password: ")

        if password != confirmation:
            print("Passwords do not match. Try again.")
            continue

        return password


def main() -> int:
    print("Hazina — Initial Organization and Admin Setup")
    print("---------------------------------------------")

    organization_name = prompt_required("Organization name")
    organization_slug = prompt_required("Organization slug").lower()
    email = prompt_required("Admin email").lower()
    full_name = prompt_required("Admin full name")
    password = prompt_password()

    try:
        result = AuthService.create_organization_with_admin(
            organization_name=organization_name,
            organization_slug=organization_slug,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
        )
    except Exception as exc:
        # Do not print database details or credentials.
        print(
            "\nBootstrap failed. The organization and admin were not created."
        )
        print(
            "Check whether the organization slug or email is already in use, "
            "and verify database connectivity."
        )
        return 1

    print("\nBootstrap completed successfully.")
    print(f"Organization: {result['organization_name']}")
    print(f"Organization slug: {result['organization_slug']}")
    print(f"Admin email: {result['email']}")
    print(f"Admin user ID: {result['user_id']}")
    print(f"Organization ID: {result['organization_id']}")
    print("Role: ADMIN")

    return 0


if __name__ == "__main__":
    sys.exit(main())
