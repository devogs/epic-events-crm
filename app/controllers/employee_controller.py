"""
Employee Controller: Handles all CRUD operations related to the Employee model.
These functions are called by the department menus (like Management Menu).
"""
import re
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from app.models import Employee  # Assuming Employee model is imported


console = Console()

# Department options for menus
DEPARTMENT_OPTIONS = {
    '1': 'Gestion',
    '2': 'Commercial',
    '3': 'Support'
}


# --- Utility Functions ---

def format_email(full_name: str, session) -> str:
    """
    Generates a unique email address based on the employee's full name.
    Format: firstname.lastname[N]@epicevents.com

    Args:
        full_name: The full name of the employee (e.g., "Billy Bob").
        session: SQLAlchemy session for checking email uniqueness.

    Returns:
        A unique email address string.
    """
    # 1. Standardize the name
    # Replace any non-alphabetic characters (except spaces) with nothing,
    # convert to lowercase, and replace spaces with dots.
    base_name = re.sub(r'[^a-zA-Z\s]', '', full_name).lower().strip()
    parts = base_name.split()
    
    # If the name is composed of multiple words, use first.last
    if len(parts) > 1:
        base_email_prefix = f"{parts[0]}.{parts[-1]}"
    else:
        # If only one word, just use that word
        base_email_prefix = parts[0]

    email_suffix = "@epicevents.com"
    final_email_prefix = base_email_prefix
    
    # 2. Check for uniqueness and add numerical suffix if necessary
    counter = 1
    while True:
        email = f"{final_email_prefix}{email_suffix}"
        
        # Check if email exists in the database
        exists = session.query(Employee).filter_by(email=email).one_or_none()
        
        if not exists:
            return email
        
        # If it exists, increment the counter and update the prefix
        counter += 1
        final_email_prefix = f"{base_email_prefix}{counter}"


# --- CRUD Operations CLI ---

def create_employee_cli(session) -> None:
    """
    Interactively gathers data and creates a new Employee.
    This function is intended to be called by the Management Menu.
    """
    console.print("\n[bold blue]----- CREATE NEW EMPLOYEE ----- [/bold blue]")

    full_name = Prompt.ask("Enter employee's full name (e.g., Jane Doe)").strip()
    
    # Automatic email generation logic
    generated_email = format_email(full_name, session)
    console.print(f"[yellow]Generated Email:[/yellow] [bold]{generated_email}[/bold]")

    # Check if the user wants to use the generated email or enter a custom one
    use_generated = Prompt.ask("Use generated email? (yes/no)", choices=["yes", "no"], default="yes")
    
    if use_generated == "yes":
        email = generated_email
    else:
        while True:
            email = Prompt.ask("Enter a custom unique email").strip()
            if '@' not in email:
                console.print("[bold red]Invalid email format. Please include '@'.[/bold red]")
                continue
            
            # Check for uniqueness manually
            if session.query(Employee).filter_by(email=email).one_or_none():
                console.print("[bold red]This email already exists. Please choose another one.[/bold red]")
            else:
                break
        
    phone = Prompt.ask("Enter phone number").strip()
    password = Prompt.ask("Enter a default password", password=True)

    # Department Selection Menu
    
    while True:
        console.print("\n[bold yellow]Select Department:[/bold yellow]")
        for key, value in DEPARTMENT_OPTIONS.items():
            console.print(f"  {key}: {value}")
            
        choice = Prompt.ask("Enter number", choices=DEPARTMENT_OPTIONS.keys())
        department = DEPARTMENT_OPTIONS[choice]
        break

    try:
        # Create the new Employee object
        new_employee = Employee(
            full_name=full_name,
            email=email,
            phone=phone,
            department=department
        )
        # The password setter handles the hashing automatically
        new_employee.password = password 

        session.add(new_employee)
        session.commit()
        console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{full_name}' ({department}) created with ID: {new_employee.id}.")

    except (IntegrityError, SQLAlchemyError) as e:
        session.rollback()
        # Log the specific error for debugging
        console.print(f"\n[bold red]ERROR:[/bold red] Failed to create employee. Details: {e}")
        console.print("The database integrity check failed. Check email uniqueness or data format.")


def list_employees_cli(session) -> None:
    """
    Displays a table with all existing employees in the database.
    """
    console.print("\n[bold blue]----- EMPLOYEE LIST ----- [/bold blue]")
    
    employees = session.query(Employee).all()

    if not employees:
        console.print("[yellow]No employees found in the database.[/yellow]")
        return

    table = Table(title="Epic Events Employees", show_header=True, header_style="bold magenta")
    
    # Define columns
    table.add_column("ID", style="dim", width=4)
    table.add_column("Full Name", style="cyan", min_width=20)
    table.add_column("Email", style="yellow", min_width=25)
    table.add_column("Phone", min_width=15)
    table.add_column("Department", style="green", min_width=10)

    # Add rows
    for emp in employees:
        table.add_row(
            str(emp.id),
            emp.full_name,
            emp.email,
            emp.phone,
            emp.department
        )

    console.print(table)
    console.print("\nPress [bold]ENTER[/bold] to return to the menu.")
    Prompt.ask("") # Wait for user to press enter


def update_employee_cli(session) -> None:
    """
    Interactively updates an existing Employee's data.
    """
    console.print("\n[bold blue]----- UPDATE EMPLOYEE ----- [/bold blue]")
    
    # 1. Get the employee ID to update
    while True:
        try:
            employee_id = Prompt.ask("Enter the ID of the employee to update (or 'q' to quit)").strip()
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

    console.print(f"\n[bold yellow]Editing Employee:[/bold yellow] [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: {employee.department})")

    try:
        # 2. Gather new data (allowing empty input to keep current value)
        new_full_name = Prompt.ask(f"New Full Name (Current: {employee.full_name})").strip()
        new_phone = Prompt.ask(f"New Phone Number (Current: {employee.phone})").strip()
        
        # 3. Department update menu
        while True:
            console.print("\n[bold yellow]Select New Department (or press ENTER to skip):[/bold yellow]")
            for key, value in DEPARTMENT_OPTIONS.items():
                console.print(f"  {key}: {value}")
                
            choice = Prompt.ask("Enter number").strip()
            
            if not choice: # Skip update
                new_department = employee.department
                break
            
            if choice in DEPARTMENT_OPTIONS:
                new_department = DEPARTMENT_OPTIONS[choice]
                break
            else:
                console.print("[bold red]Invalid choice. Please enter 1, 2, 3, or press ENTER.[/bold red]")

        # 4. Apply changes only if new values are provided
        if new_full_name:
            employee.full_name = new_full_name
        if new_phone:
            employee.phone = new_phone
        if new_department != employee.department:
            employee.department = new_department

        session.commit()
        console.print(f"\n[bold green]SUCCESS:[/bold green] Employee ID {employee.id} updated.")

    except SQLAlchemyError as e:
        session.rollback()
        console.print(f"\n[bold red]ERROR:[/bold red] Failed to update employee. Details: {e}")


def delete_employee_cli(session) -> None:
    """
    Interactively deletes an existing Employee by ID after confirmation.
    """
    console.print("\n[bold red]----- DELETE EMPLOYEE ----- [/bold red]")

    # 1. Get the employee ID to delete
    while True:
        try:
            employee_id = Prompt.ask("Enter the ID of the employee to delete (or 'q' to quit)").strip()
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

    # 2. Confirmation
    console.print(f"\nYou are about to delete: [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: {employee.department})")
    
    if Confirm.ask("[bold red]Are you absolutely sure you want to delete this employee?[/bold red]"):
        try:
            session.delete(employee)
            session.commit()
            console.print(f"\n[bold green]SUCCESS:[/bold green] Employee '{employee.full_name}' (ID: {employee.id}) has been successfully deleted.")
        
        except SQLAlchemyError as e:
            session.rollback()
            console.print(f"\n[bold red]ERROR:[/bold red] Failed to delete employee. Details: {e}")
    else:
        console.print("\n[yellow]Deletion cancelled.[/yellow]")
