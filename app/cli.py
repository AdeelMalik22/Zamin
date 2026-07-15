import argparse
import json

from app.db.database import init_database
from app.services.auth_service import seed_admin
from app.services.mock_data_service import MOCK_ADMIN_EMAIL, MockDataService
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Real Estate Listings Platform management commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed = subparsers.add_parser("seed-admin", help="create the bootstrap admin if it does not exist")
    seed.add_argument("--email", required=True)
    seed.add_argument("--password", required=True)
    seed.add_argument("--name", default="Platform Admin")
    seed.add_argument("--phone", default="+10000000000")
    mock = subparsers.add_parser("seed-mock-data", help="seed deterministic local demo data")
    mock.add_argument("--admin-password", default="MockAdmin123!")
    args = parser.parse_args()

    if args.command == "seed-admin":
        init_database()
        admin = seed_admin(args.email, args.password, args.name, args.phone)
        print(f"Admin is ready: {admin.email}")
    elif args.command == "seed-mock-data":
        init_database()
        with SessionLocal() as db:
            summary = MockDataService(db).seed(admin_password=args.admin_password)
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        if summary.admin_email == MOCK_ADMIN_EMAIL:
            print(f"Mock admin password: {args.admin_password}")


if __name__ == "__main__":
    main()
