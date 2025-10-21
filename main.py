"""
This is the main script for the Epic Events CRM command-line interface.
It handles user authentication using JWT and routes to different functionalities 
based on user permissions.
"""

import os
import sys

from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy.orm import sessionmaker

from app.models import Employee, Base, engine, initialize_roles
from app.authentication import (
    check_password,
    create_access_token,
    get_employee_from_token,
)
from app.views.management_menu import management_menu
from app.views.sales_menu import sales_menu
from app.views.support_menu import support_menu

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

console = Console()

GLOBAL_JWT_TOKEN: str | None = None


def init_sentry():
    """Initializes Sentry SDK using DSN from environment variable (SENTRY_DSN)."""
    sentry_dsn = os.environ.get("SENTRY_DSN")

    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=1.0,
            environment="cli-prod",
            integrations=[
                SqlalchemyIntegration(),
            ],
            send_default_pii=False,
        )
        console.print("[bold green]Sentry Initialized (DSN found).[/bold green]")
    else:
        console.print(
            "[bold yellow]Sentry DSN not found. Running without error logging. "
            "Check SENTRY_DSN environment variable.[/bold yellow]"
        )


def get_session():
    """
    Creates and returns a new SQLAlchemy session. 
    Every operation (login or menu cycle) must use a new session.
    """
    try:
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        # Tentative de capture si Sentry est initialisé
        if sentry_sdk.HUB.get_global_scope().client:
            sentry_sdk.capture_exception(e)
        console.print(
            f"[bold red]ERREUR FATALE lors de la création de la session:[/bold red] {e}"
        )
        sys.exit(1)


def login_cli(session) -> Employee | None:
    """Manages the login interface, validates credentials, and generates a JWT token."""
    global GLOBAL_JWT_TOKEN

    console.print("\n" + "=" * 50, style="bold blue")
    console.print("[bold blue]EPIC EVENTS CRM LOGIN[/bold blue]")
    console.print("=" * 50, style="bold blue")

    email = Prompt.ask("Enter your Email").strip()
    password = Prompt.ask("Enter your Password", password=True).strip()

    employee = session.query(Employee).filter_by(email=email).one_or_none()

    # LOGIQUE DE CONNEXION RESTAURÉE DE main_trusted.py
    if employee and employee._password and check_password(password, employee._password):
        # Authentification réussie
        token, expiration_display = create_access_token(
            employee.id, employee.department
        )
        GLOBAL_JWT_TOKEN = token

        console.print(
            f"\n[bold green]Welcome {employee.full_name} ({employee.department})![/bold green]"
        )
        console.print(f"[bold dim]Session expires in: {expiration_display}[/bold dim]")
        return employee

    # Échec de l'authentification
    console.print("[bold red]ERROR:[/bold red] Invalid email or password.")
    return None


def main_menu_router(employee: Employee, session, token: str) -> tuple[str, str | None]:
    """
    Routes the user to the appropriate menu based on their department.
    Returns:
        tuple[str, str | None]: (action: 'stay' | 'logout' | 'quit', new_token: str | None)
    """

    department = employee.department

    if department == "Gestion":
        return management_menu(session, employee, token)
    elif department == "Commercial":
        return sales_menu(session, employee, token)
    elif department == "Support":
        return support_menu(session, employee, token)
    else:
        console.print(
            f"[bold red]ERROR:[/bold red] Unknown department '{department}'. Logging out."
        )
        return "logout", None


def main():
    """Main entry point of the application."""
    global GLOBAL_JWT_TOKEN

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(base_dir, "database", ".env")

    try:
        is_loaded = load_dotenv(dotenv_path)

        if not is_loaded:
            console.print(
                f"[bold yellow]WARNING:[/bold yellow] Failed to load .env file from "
                f"{dotenv_path}. Check file existence and path."
            )
        else:
            console.print(
                f"[bold green]INFO:[/bold green] .env loaded successfully from "
                f"{dotenv_path}."
            )

    except Exception as e:
        console.print(
            f"[bold red]FATAL WARNING:[/bold red] Error during .env load: {e}"
        )

    console.print(
        "[bold cyan]--- Initializing Database Structure & Roles ---[/bold cyan]"
    )

    Base.metadata.create_all(engine)

    init_session = get_session()

    try:
        initialize_roles(init_session, engine)
    except Exception as e:
        if sentry_sdk.HUB.get_global_scope().client:
            sentry_sdk.capture_exception(e)
            sentry_sdk.flush(timeout=1.0)
        console.print(
            f"[bold red]ERREUR FATALE lors de l'initialisation de la DB:[/bold red] {e}"
        )
        sys.exit(1)
    finally:
        init_session.close()

    # --- INITIALISATION SENTRY (NOUVEAU) ---
    init_sentry()

    try:
        while True:
            if GLOBAL_JWT_TOKEN is None:
                login_session = get_session()
                logged_in_employee = login_cli(login_session)
                login_session.close()

                if logged_in_employee is None:
                    Prompt.ask("Press Enter to try logging in again...")

            else:
                session = get_session()
                action = "stay"

                try:
                    logged_in_employee = get_employee_from_token(
                        GLOBAL_JWT_TOKEN, session
                    )

                    if logged_in_employee:
                        action, new_token_from_menu = main_menu_router(
                            logged_in_employee, session, GLOBAL_JWT_TOKEN
                        )

                        GLOBAL_JWT_TOKEN = new_token_from_menu
                    else:
                        action = "logout"
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    console.print(
                        f"[bold red]An unexpected error occurred in the main loop:[/bold red] "
                        f"{e}. Error logged to Sentry."
                    )
                    action = "logout"
                finally:
                    session.close()

                if action == "quit":
                    console.print(
                        "\n[bold yellow]Exiting the application.[/bold yellow]"
                    )
                    console.print(
                        "[bold yellow]Flushing Sentry events before exiting...[/bold yellow]"
                    )
                    sentry_sdk.flush(timeout=1.0)

                    break
                if action == "logout":
                    GLOBAL_JWT_TOKEN = None
                    console.print(
                        "\n[bold blue]You have been logged out. " \
                        "Returning to login screen.[/bold blue]"
                    )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        console.print(
            f"[bold red]FATAL CRASH:[/bold red] Application encountered an unhandled error. "
            "Error logged to Sentry."
        )

        console.print(
            "[bold yellow]Flushing Sentry events after crash...[/bold yellow]"
        )
        sentry_sdk.flush(timeout=2.0)
        sys.exit(1)


if __name__ == "__main__":
    main()
