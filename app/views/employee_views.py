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
from app.models import Employee # Assurez-vous que l'importation de Employee est correcte

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
        for key, value in DEPARTMENT_OPTIONS.items():
            console.print(f"  {key}. {value}")
            
        department_choice = Prompt.ask("Select option [1/2/3]", choices=list(DEPARTMENT_OPTIONS.keys())).strip()
        department = DEPARTMENT_OPTIONS.get(department_choice)
        
        if department:
            break
        console.print("[bold red]Invalid choice. Please select 1, 2, or 3.[/bold red]")

    try:
        # Note: The email is generated automatically in employee_controller.create_employee 
        # based on the full_name here.
        new_employee = create_employee(session, full_name, phone, department, plain_password)
        
        if new_employee:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{new_employee.full_name}' created!")
            console.print(f"  - ID: {new_employee.id}")
            console.print(f"  - Email: [cyan]{new_employee.email}[/cyan]")
            console.print(f"  - Department: [yellow]{new_employee.department}[/yellow]")
        else:
            console.print("\n[bold red]FAILURE:[/bold red] Employee creation failed (check console for details).")
            
    except ValueError as e:
        console.print(f"\n[bold red]ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")


def list_employees_cli(session, current_user: Employee) -> None:
    """
    CLI interface to display the list of all employees.
    Requires 'view_employees' permission (all departments have it).
    """
    if not check_permission(current_user, 'view_employees'):
        console.print("[bold red]Permission denied.[/bold red] You do not have permission to view employees.")
        return

    employees = list_employees(session)
    
    if not employees:
        console.print("\n[yellow]No employees found in the database.[/yellow]")
        return
        
    console.print("\n[bold blue]----- EMPLOYEE LIST ----- [/bold blue]")

    table = Table(title="Epic Events Employees", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Full Name", style="cyan", min_width=20)
    table.add_column("Email", min_width=30)
    table.add_column("Phone", min_width=15)
    table.add_column("Department", style="yellow", min_width=10)
    
    for emp in employees:
        table.add_row(
            str(emp.id),
            emp.full_name,
            emp.email,
            emp.phone,
            emp.department
        )
        
    console.print(table)


def update_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to gather data and call the pure controller function to update an employee.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'update_employee'):
        console.print("[bold red]Permission denied.[/bold red] Only the 'Gestion' department can update employees.")
        return
        
    console.print("\n[bold yellow]----- UPDATE EMPLOYEE ----- [/bold yellow]")

    employee = None
    employee_id = None
    while True:
        try:
            employee_id_input = Prompt.ask("Enter the ID of the employee to update (or 'q' to cancel)").strip()
            if employee_id_input.lower() == 'q':
                return
            
            employee_id = int(employee_id_input)
            employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
            
            if not employee:
                console.print(f"[bold red]Employee with ID {employee_id} not found.[/bold red]")
                continue
            
            break
        except ValueError:
            console.print("[bold red]Invalid ID format. Please enter a number.[/bold red]")


    console.print(f"\n[bold green]Editing Employee:[/bold green] [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: {employee.department})")

    updates = {}
    
    # 1. Full Name
    new_full_name = Prompt.ask(f"New Full Name (Current: {employee.full_name}) - Press Enter to skip").strip()
    if new_full_name:
        updates['full_name'] = new_full_name
        
    # 2. Email - RESTAURÉ
    new_email = Prompt.ask(f"New Email (Current: {employee.email}) - Press Enter to skip").strip()
    if new_email:
        updates['email'] = new_email # L'email est inclus dans les updates
        
    # 3. Phone
    new_phone = Prompt.ask(f"New Phone Number (Current: {employee.phone}) - Press Enter to skip").strip()
    if new_phone:
        updates['phone'] = new_phone
        
    # 4. Department
    console.print("\n[bold yellow]Select New Department (Current: {}):[/bold yellow]".format(employee.department))
    for key, value in DEPARTMENT_OPTIONS.items():
        console.print(f"  {key}. {value}")
    console.print("  [bold]Press Enter to skip[/bold]")

    department_choice = Prompt.ask("Select option [1/2/3/Enter]").strip()
    new_department = DEPARTMENT_OPTIONS.get(department_choice)
    if new_department and new_department != employee.department:
        updates['department'] = new_department
        
    # 5. Password
    new_password = Prompt.ask("New Password (Leave empty to keep current) - Enter to skip", password=True).strip()
    if new_password:
        updates['plain_password'] = new_password
    
    # Check if there are any changes
    if not updates:
        console.print("[yellow]No changes detected. Operation cancelled.[/yellow]")
        return

    try:
        # CORRECTION : Utilisation de **updates pour déstructurer le dictionnaire
        # en arguments nommés (full_name=x, phone=y, email=z, etc.) requis par le contrôleur.
        updated_employee = update_employee(session, employee_id, **updates) 
        
        if updated_employee:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{updated_employee.full_name}' (ID: {updated_employee.id}) updated. New Email: [cyan]{updated_employee.email}[/cyan]")
        else:
            console.print(f"\n[bold red]FAILURE:[/bold red] Employee update failed (check console for details).")
            
    except ValueError as e:
        console.print(f"\n[bold red]ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")


def delete_employee_cli(session, current_user: Employee) -> None:
    """
    CLI interface to get employee ID and call the controller function to delete an employee.
    Requires 'Gestion' permission.
    """
    if not check_permission(current_user, 'delete_employee'):
        console.print("[bold red]Permission denied.[/bold red] Only the 'Gestion' department can delete employees.")
        return

    console.print("\n[bold red]----- DELETE EMPLOYEE ----- [/bold red]")

    employee_id = None
    while True:
        try:
            employee_id_input = Prompt.ask("Enter the ID of the employee to delete (or 'q' to cancel)").strip()
            if employee_id_input.lower() == 'q':
                return
            
            employee_id = int(employee_id_input)
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