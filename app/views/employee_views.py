"""
Employee Views: Handles all user interface (CLI) interactions for Employee CRUD operations.
It calls the pure business logic functions from the controller layer.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from app.controllers.employee_controller import (
    create_employee,
    list_employees,
    update_employee,
    delete_employee,
    DEPARTMENT_OPTIONS
)

from app.authentication import check_permission
from app.models import Employee

console = Console()

# --- CLI Functions  ---

def create_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to gather data and call the pure controller function to create a new Employee.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'create_employee'):
        console.print("[bold red]PERMISSION DENIED:[/bold red] Only 'Gestion' can create employees.")
        return

    console.print("\n[bold blue]----- CREATE NEW EMPLOYEE ----- [/bold blue]")

    full_name = Prompt.ask("Enter employee's full name").strip()
    
    while True:
        console.print("\n[bold yellow]Select Department:[/bold yellow]")
        for key, value in DEPARTMENT_OPTIONS.items():
            console.print(f"  {key}: {value}")
            
        choice = Prompt.ask("Enter number", choices=DEPARTMENT_OPTIONS.keys())
        department = DEPARTMENT_OPTIONS[choice]
        break
        
    phone = Prompt.ask("Enter phone number").strip()
    password = Prompt.ask("Enter a default password", password=True)

    try:
        new_employee = create_employee(
            session=session,
            full_name=full_name,
            phone=phone,
            password=password,
            department=department
        )
        
        console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{new_employee.full_name}' (Email: {new_employee.email}, Dept: {department}) created with ID: {new_employee.id}.")

    except ValueError as e:
        console.print(f"\n[bold red]ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")


def list_employees_cli(session, current_user: Employee) -> None:
    """
    CLI interface to display a table with all existing employees.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'list_employees'):
        console.print("[bold red]PERMISSION DENIED:[/bold red] Only 'Gestion' can list all employee details.")
        return

    console.print("\n[bold blue]----- EMPLOYEE LIST ----- [/bold blue]")
    
    employees = list_employees(session)

    if not employees:
        console.print("[yellow]No employees found in the database.[/yellow]")
        return

    table = Table(title="Epic Events Employees", show_header=True, header_style="bold magenta")
    
    table.add_column("ID", style="dim", width=4)
    table.add_column("Full Name", style="cyan", min_width=20)
    table.add_column("Email", style="yellow", min_width=25)
    table.add_column("Phone", min_width=15)
    table.add_column("Department", style="green", min_width=10)

    for emp in employees:
        table.add_row(
            str(emp.id),
            emp.full_name,
            emp.email,
            emp.phone,
            emp.department
        )

    console.print(table)
    Prompt.ask("\nPress [bold]ENTER[/bold] to return to the menu.")


def update_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to interactively update an existing Employee's data.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'update_employee'):
        console.print("[bold red]PERMISSION DENIED:[/bold red] Only 'Gestion' can update employees.")
        return
        
    console.print("\n[bold blue]----- UPDATE EMPLOYEE ----- [/bold blue]")
    
    while True:
        try:
            employee_id = Prompt.ask("Enter the ID of the employee to update (or 'q' to quit)").strip()
            if employee_id.lower() == 'q':
                return
            
            employee_id = int(employee_id)
            break
        except ValueError:
            console.print("[bold red]Invalid ID format. Please enter a number.[/bold red]")

    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    if not employee:
        console.print(f"[bold red]Employee with ID {employee_id} not found.[/bold red]")
        return

    console.print(f"\n[bold yellow]Editing Employee:[/bold yellow] [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: {employee.department})")

    new_full_name = Prompt.ask(f"New Full Name (Current: {employee.full_name})").strip()
    new_phone = Prompt.ask(f"New Phone Number (Current: {employee.phone})").strip()
    
    new_department = employee.department
    while True:
        console.print("\n[bold yellow]Select New Department (or press ENTER to skip):[/bold yellow]")
        for key, value in DEPARTMENT_OPTIONS.items():
            console.print(f"  {key}: {value}")
            
        choice = Prompt.ask("Enter number").strip()
        
        if not choice:
            break
        
        if choice in DEPARTMENT_OPTIONS:
            new_department = DEPARTMENT_OPTIONS[choice]
            break
        else:
            console.print("[bold red]Invalid choice. Please enter 1, 2, 3, or press ENTER.[/bold red]")

    try:
        update_data = {}
        if new_full_name: update_data['full_name'] = new_full_name
        if new_phone: update_data['phone'] = new_phone
        if new_department != employee.department: update_data['department'] = new_department

        if update_data:
            update_employee(session, employee_id, update_data)
            console.print(f"\n[bold green]SUCCESS:[/bold green] Employee ID {employee_id} updated.")
        else:
            console.print("\n[yellow]No changes detected, update skipped.[/yellow]")

    except ValueError as e:
        console.print(f"\n[bold red]ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")


def delete_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to delete an existing Employee by ID after confirmation.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'delete_employee'):
        console.print("[bold red]PERMISSION DENIED:[/bold red] Only 'Gestion' can delete employees.")
        return
        
    console.print("\n[bold red]----- DELETE EMPLOYEE ----- [/bold red]")

    while True:
        try:
            employee_id = Prompt.ask("Enter the ID of the employee to delete (or 'q' to quit)").strip()
            if employee_id.lower() == 'q':
                return
            
            employee_id = int(employee_id)
            break
        except ValueError:
            console.print("[bold red]Invalid ID format. Please enter a number.[/bold red]")

    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    if not employee:
        console.print(f"[bold red]Employee with ID {employee_id} not found.[/bold red]")
        return
        
    console.print(f"\nYou are about to delete: [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: {employee.department})")
    
    if Confirm.ask("[bold red]Are you absolutely sure you want to delete this employee?[/bold red]"):
        try:
            delete_employee(session, employee_id)
            console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{employee.full_name}' (ID: {employee.id}) has been successfully deleted.")
        except ValueError as e:
            console.print(f"\n[bold red]ERROR:[/bold red] {e}")
        except Exception as e:
            console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")
    else:
        console.print("\n[yellow]Deletion cancelled.[/yellow]")
