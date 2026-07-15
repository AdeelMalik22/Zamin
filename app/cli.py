import argparse
import json

from app.db.database import init_database
from app.db.session import SessionLocal
from app.services.auth_service import seed_admin
from app.services.demo_data_service import DemoDataService


def main() -> None:
    parser = argparse.ArgumentParser(description="Real Estate Listings Platform management commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("seed-admin", help="create the bootstrap admin if it does not exist")
    seed.add_argument("--email", required=True)
    seed.add_argument("--password", required=True)
    seed.add_argument("--name", default="Platform Admin")
    seed.add_argument("--phone", default="+10000000000")

    demo = subparsers.add_parser("seed-demo-data", help="seed realistic Pakistani local demo data")
    demo.add_argument(
        "--keep-legacy-mock-data",
        action="store_true",
        help="do not remove the older Mock City/Mock Listing dataset",
    )
    args = parser.parse_args()

    if args.command == "seed-admin":
        init_database()
        admin = seed_admin(args.email, args.password, args.name, args.phone)
        print(f"Admin is ready: {admin.email}")
    elif args.command == "seed-demo-data":
        init_database()
        with SessionLocal() as db:
            result = DemoDataService(db).seed(replace_legacy_mock_data=not args.keep_legacy_mock_data)
        print(json.dumps(result.summary.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
