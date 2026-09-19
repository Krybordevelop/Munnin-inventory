from getpass import getpass

import typer
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import AdminUser

cli = typer.Typer(help="Muninn Inventory administration")


@cli.command("bootstrap-admin")
def bootstrap_admin(username: str = typer.Option(..., prompt=True)) -> None:
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 12:
        raise typer.BadParameter("Password must be at least 12 characters")
    if password != confirmation:
        raise typer.BadParameter("Passwords do not match")
    with SessionLocal.begin() as db:
        if db.scalar(select(AdminUser).where(AdminUser.username == username)):
            raise typer.BadParameter("Administrator already exists")
        db.add(AdminUser(username=username, password_hash=hash_password(password)))
    typer.echo(f"Administrator {username!r} created")


if __name__ == "__main__":
    cli()
