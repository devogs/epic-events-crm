"""
Employee Views: Handles all user interface (CLI) interactions for Employee CRUD operations.
It calls the pure business logic functions from the controller layer.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from app.controllers.employee_controller import (
    create_employee,      # Main creation function
    list_employees,       # Main listing function
    update_employee,      # Main update function
    delete_employee,      # Main deletion function
    DEPARTMENT_OPTIONS    # Shared department options (with French names)
)

from app.authentication import check_permission
from app.models import Employee

console = Console()

# --- CLI Functions (Interface Layer) ---

def create_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to gather data and call the pure controller function to create a new Employee.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'create_employee'):
        console.print("[bold red]Permission denied.[/bold red] Only the 'Gestion' department can create employees.")
        return

    console.print("\n[bold green]----- CREATE NEW EMPLOYEE ----- [/bold green]")

    full_name = Prompt.ask("Employee Full Name").strip()
    phone = Prompt.ask("Phone Number").strip()
    
    plain_password = Prompt.ask("Default Password", password=True)
    
    while True:
        console.print("\n[bold yellow]Select Department:[/bold yellow]")
        options_list = [f"  {key}: {value}" for key, value in DEPARTMENT_OPTIONS.items()]
        console.print("\n".join(options_list))
        
        choice = Prompt.ask("Enter the number", choices=DEPARTMENT_OPTIONS.keys())
        department = DEPARTMENT_OPTIONS[choice]
        break

    try:
        employee = create_employee(
            session,
            full_name=full_name,
            phone=phone,
            department=department,
            plain_password=plain_password
        )
        
        if employee:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{employee.full_name}' ({employee.department}) created with ID: {employee.id}. Email: [cyan]{employee.email}[/cyan]")
        else:
            console.print("\n[bold red]FAILURE:[/bold red] Employee creation failed.")
            
    except ValueError as e:
        console.print(f"\n[bold red]VIEW ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")


def list_employees_cli(session, current_user: Employee) -> None:
    """
    CLI interface to display the list of all employees.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'list_employees'):
        console.print("[bold red]Permission denied.[/bold red] Only the 'Gestion' department can list employees.")
        return

    console.print("\n[bold blue]----- LIST OF EMPLOYEES ----- [/bold blue]")
    
    employees = list_employees(session)

    if not employees:
        console.print("[yellow]No employee found.[/yellow]")
        return

    table = Table(title="Epic Events Employees", show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Full Name", min_width=20)
    table.add_column("Email", min_width=30)
    table.add_column("Phone", min_width=15)
    table.add_column("Department", style="magenta", min_width=15)

    for emp in employees:
        table.add_row(
            str(emp.id),
            emp.full_name,
            emp.email,
            emp.phone if emp.phone else "N/A",
            emp.department
        )

    console.print(table)


def update_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to gather data and call the pure controller function to update an employee.
    Requires 'Gestion' permission.
    Now includes prompts for Full Name and Email.
    """
    if not check_permission(current_user, 'update_employee'):
        console.print("[bold red]Permission denied.[/bold red] Only the 'Gestion' department can update employees.")
        return
        
    console.print("\n[bold yellow]----- UPDATE EMPLOYEE ----- [/bold yellow]")

    employee = None
    while True:
        try:
            employee_id = Prompt.ask("Enter the ID of the employee to update (or 'q' to cancel)").strip()
            if employee_id.lower() == 'q':
                return
            
            employee_id = int(employee_id)
            

            employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
            if employee:
                break
            else:
                console.print(f"[bold red]Employee with ID {employee_id} not found.[/bold red]")
                
        except ValueError:
            console.print("[bold red]Invalid ID format. Please enter a number.[/bold red]")

    updates = {}
    
    new_full_name = Prompt.ask(f"New Full Name (Current: [cyan]{employee.full_name}[/cyan], Leave empty to keep current)").strip()
    if new_full_name and new_full_name != employee.full_name:
        updates['full_name'] = new_full_name

    new_email = Prompt.ask(f"New Email (Current: [cyan]{employee.email}[/cyan], Leave empty to keep current)").strip()
    if new_email and new_email != employee.email:
        updates['email'] = new_email
        
    new_phone = Prompt.ask(f"New Phone Number (Current: [cyan]{employee.phone if employee.phone else 'N/A'}[/cyan], Leave empty to keep current)").strip()
    if new_phone:
        updates['phone'] = new_phone

    console.print("\n[bold yellow]New Department:[/bold yellow]")
    options_list = [f"  {key}: {value}" for key, value in DEPARTMENT_OPTIONS.items()]
    options_list.append("  0: Do not change")
    console.print("\n".join(options_list))
    console.print(f"Current Department: [cyan]{employee.department}[/cyan]")
    
    dept_choice = Prompt.ask("Enter the number", choices=list(DEPARTMENT_OPTIONS.keys()) + ['0'], default='0')
    if dept_choice != '0':
        updates['department'] = DEPARTMENT_OPTIONS[dept_choice]

    update_password_choice = Confirm.ask("Do you want to update the password?", default=False)
    if update_password_choice:
        new_password = Prompt.ask("New Password", password=True)
        updates['plain_password'] = new_password 

    if not updates:
        console.print("[yellow]No changes detected. Operation cancelled.[/yellow]")
        return

    try:
        updated_employee = update_employee(session, employee_id, updates)
        
        if updated_employee:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{updated_employee.full_name}' (ID: {updated_employee.id}) updated. New Email: [cyan]{updated_employee.email}[/cyan]")
        else:
            console.print(f"\n[bold red]FAILURE:[/bold red] Employee update failed (check console for details).")
            
    except ValueError as e:
        console.print(f"\n[bold red]VIEW ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")


def delete_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to handle employee deletion.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'delete_employee'):
        console.print("[bold red]Permission denied.[/bold red] Only the 'Gestion' department can delete employees.")
        return
        
    console.print("\n[bold red]----- DELETE EMPLOYEE ----- [/bold red]")

    employee = None
    while True:
        try:
            employee_id = Prompt.ask("Enter the ID of the employee to delete (or 'q' to cancel)").strip()
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
            success = delete_employee(session, employee_id)

            if success:
                console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{employee.full_name}' (ID: {employee.id}) has been successfully deleted.")
            else:
                console.print("\n[bold red]FAILURE:[/bold red] Deletion failed (check console for details).")
                
        except ValueError as e:
            console.print(f"\n[bold red]ERROR:[/bold red] {e}")
        except Exception as e:
            console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")
    else:
        console.print("[yellow]Deletion cancelled.[/yellow]")
