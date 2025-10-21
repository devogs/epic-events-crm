"""
Employee Views: Handles all user interface (CLI) interactions for Employee CRUD operations.
It calls the pure business logic functions from the controller layer.
"""

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

# --- CORRECTION CRITIQUE 1: Importation isolée du contrôleur ---
# Utilisez l'alias 'ec' pour toutes les fonctions et options du contrôleur.
import app.controllers.employee_controller as ec

# ---------------------------------------------------------------------------------

# --- CORRECTION CRITIQUE 2: Importation isolée de l'authentification ---
# Utilisez l'alias 'auth' pour check_permission afin d'éviter toute pollution.
import app.authentication as auth

# --------------------------------------------------------------------

from app.models import Employee  # Garder l'importation du modèle pour le type hinting

console = Console()

# --- Utility Functions (Display) ---


def display_employee_table(employees: list, title: str):
    """Utility function to display employees in a Rich Table."""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Full Name", style="cyan", min_width=20)
    table.add_column("Email", min_width=30)
    table.add_column("Phone", min_width=15)
    table.add_column("Department", style="yellow", min_width=10)

    for emp in employees:
        table.add_row(str(emp.id), emp.full_name, emp.email, emp.phone, emp.department)

    console.print(table)


# --- CLI Functions (Interface Layer) ---


def create_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to gather data and call the pure controller function to create a new Employee.
    Requires 'Gestion' permission.
    """
    # Appel de permission isolé via alias 'auth'
    if not auth.check_permission(current_user, "create_employee"):
        console.print(
            "[bold red]Permission denied.[/bold red] Only the 'Gestion' department can create employees."
        )
        return

    console.print("\n[bold green]----- CREATE NEW EMPLOYEE ----- [/bold green]")

    full_name = Prompt.ask("Employee Full Name").strip()
    email = Prompt.ask("Email").strip()
    phone = Prompt.ask("Phone Number\t").strip()

    plain_password = Prompt.ask("Default Password", password=True)

    while True:
        console.print("\n[bold yellow]Select Department:[/bold yellow]")

        # Utilisation des options via alias 'ec'
        options_list = [
            f"  [cyan]{k}[/cyan]: {v}" for k, v in ec.DEPARTMENT_OPTIONS.items()
        ]
        console.print("\n".join(options_list))

        # Utilisation des clés numériques '1', '2', '3'
        dept_choice = Prompt.ask(
            "Enter Department Key [1/2/3]", choices=ec.DEPARTMENT_OPTIONS.keys()
        ).strip()

        if dept_choice in ec.DEPARTMENT_OPTIONS:
            department_name = ec.DEPARTMENT_OPTIONS[dept_choice]
            break
        else:
            console.print(
                "[bold red]Invalid department key. Please try again.[/bold red]"
            )

    # Appel au contrôleur via alias 'ec'
    new_employee = ec.create_employee(
        session,
        current_user,
        full_name=full_name,
        email=email,
        phone=phone,
        department=department_name,
        password=plain_password,
    )

    if new_employee:
        console.print(
            f"\n[bold green]SUCCESS:[/bold green] Employee '{new_employee.full_name}' ({new_employee.department}) created."
        )
    else:
        console.print("\n[bold red]FAILURE:[/bold red] Employee creation failed.")


# ----------------------------------------------------------------------------------------------------


def list_employees_cli(session, current_user: Employee) -> None:
    """
    CLI interface to display the list of all employees.
    Requires 'Gestion' permission.
    """
    # Appel de permission isolé via alias 'auth'
    if not auth.check_permission(current_user, "view_employees"):
        console.print(
            "[bold red]Permission denied.[/bold red] Only the 'Gestion' department can view employees."
        )
        return

    console.print("\n[bold blue]----- EMPLOYEE LIST ----- [/bold blue]")

    # Appel au contrôleur via alias 'ec'
    employees = ec.list_employees(session)

    if employees:
        display_employee_table(employees, "Epic Events Employees")
    else:
        console.print("[yellow]No employees found in the database.[/yellow]")


# ----------------------------------------------------------------------------------------------------


def update_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to update an existing employee.
    Requires 'Gestion' permission.
    """
    # Appel de permission isolé via alias 'auth'
    if not auth.check_permission(current_user, "update_employee"):
        console.print(
            "[bold red]Permission denied.[/bold red] Only the 'Gestion' department can update employees."
        )
        return

    console.print("\n[bold yellow]----- UPDATE EMPLOYEE ----- [/bold yellow]")

    employee_id = None
    while True:
        try:
            employee_id_input = Prompt.ask(
                "Enter the ID of the employee to update (or 'q' to cancel)"
            ).strip()
            if employee_id_input.lower() == "q":
                return
            employee_id = int(employee_id_input)
            break
        except ValueError:
            console.print(
                "[bold red]Invalid ID format. Please enter a number.[/bold red]"
            )

    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    if not employee:
        console.print(f"[bold red]Employee with ID {employee_id} not found.[/bold red]")
        return

    console.print(
        f"\n[bold yellow]Updating Employee:[/bold yellow] [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: {employee.department})"
    )

    updates = {}

    updates["full_name"] = (
        Prompt.ask(f"Full Name (current: {employee.full_name})").strip() or None
    )
    updates["email"] = Prompt.ask(f"Email (current: {employee.email})").strip() or None
    updates["phone"] = Prompt.ask(f"Phone (current: {employee.phone})").strip() or None

    new_password = (
        Prompt.ask("New Password (leave blank to keep current)", password=True).strip()
        or None
    )
    if new_password:
        updates["password"] = new_password

    # Department change
    while True:
        console.print(
            "\n[bold yellow]Select New Department (or leave blank to keep current):[/bold yellow]"
        )

        # Utilisation des options via alias 'ec'
        options_list = [
            f"  [cyan]{k}[/cyan]: {v}" for k, v in ec.DEPARTMENT_OPTIONS.items()
        ]
        console.print("\n".join(options_list))

        # Utilisation des clés numériques '1', '2', '3'
        dept_choice = Prompt.ask(
            f"Enter New Department Key [1/2/3] (current: {employee.department})"
        ).strip()

        if not dept_choice:
            break

        if dept_choice in ec.DEPARTMENT_OPTIONS:
            updates["department"] = ec.DEPARTMENT_OPTIONS[dept_choice]
            break
        else:
            console.print(
                "[bold red]Invalid department key. Please try again.[/bold red]"
            )

    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        console.print(
            "[bold yellow]No changes detected. Aborting update.[/bold yellow]"
        )
        return

    # CORRECTION ICI: Ajout de 'current_user' dans l'appel au contrôleur
    updated_employee = ec.update_employee(
        session,
        current_user,  # <--- ARGUMENT MANQUANT AJOUTÉ
        employee_id=employee_id,
        **updates,
    )

    if updated_employee:
        console.print(
            f"\n[bold green]SUCCESS:[/bold green] Employee '{updated_employee.full_name}' updated."
        )
    else:
        console.print(
            "\n[bold red]FAILURE:[/bold red] Employee update failed (check console for details)."
        )


# ----------------------------------------------------------------------------------------------------


def delete_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to delete an existing employee.
    Requires 'Gestion' permission.
    """
    # Appel de permission isolé via alias 'auth'
    if not auth.check_permission(current_user, "delete_employee"):
        console.print(
            "[bold red]Permission denied.[/bold red] Only the 'Gestion' department can delete employees."
        )
        return

    console.print("\n[bold red]----- DELETE EMPLOYEE ----- [/bold red]")

    employee_id = None
    while True:
        try:
            employee_id_input = Prompt.ask(
                "Enter the ID of the employee to delete (or 'q' to cancel)"
            ).strip()
            if employee_id_input.lower() == "q":
                return

            employee_id = int(employee_id_input)
            break
        except ValueError:
            console.print(
                "[bold red]Invalid ID format. Please enter a number.[/bold red]"
            )

    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    if not employee:
        console.print(f"[bold red]Employee with ID {employee_id} not found.[/bold red]")
        return

    if employee.id == current_user.id:
        console.print("[bold red]ERROR:[/bold red] You cannot delete your own account.")
        return

    console.print(
        f"\nYou are about to delete: [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: {employee.department})"
    )

    if Confirm.ask(
        "[bold red]Are you absolutely sure you want to delete this employee?[/bold red]"
    ):
        try:
            # Appel au contrôleur via alias 'ec'
            success = ec.delete_employee(session, employee_id)

            if success:
                console.print(
                    f"\n[bold green]SUCCESS:[/bold green] Employee '{employee.full_name}' (ID: {employee.id}) has been successfully deleted."
                )
            else:
                console.print(
                    "\n[bold red]FAILURE:[/bold red] Deletion failed (check console for details)."
                )

        except ValueError as e:
            console.print(f"\n[bold red]ERROR:[/bold red] {e}")
        except Exception as e:
            console.print(
                f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}"
            )
    else:
        console.print("[bold yellow]Deletion cancelled.[/bold yellow]")
