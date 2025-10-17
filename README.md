# Epic Events CRM CLI (Client Relationship Management - Command-Line Interface)

Welcome to the Epic Events CRM project. This command-line interface (CLI) application is designed for managing clients, contracts, and events by the Management, Sales, and Support teams.

This project utilizes Python, SQLAlchemy for the ORM, PostgreSQL via Docker for the database, and Sentry for error monitoring.

## 1. Initial Setup

Follow these steps to clone the repository, set up the virtual environment, and prepare the configuration file.

### 1.1. Clone the Git Repository

Open your terminal and use the git clone command to get a local copy of the project:

Clone the repository (replace the URL with yours)
```bash
git clone <YOUR_REPOSITORY_URL>
```

Navigate into the project directory
```bash
cd epic-events-crm
```


### 1.2. Create and Activate the Virtual Environment (venv)

It is crucial to use a virtual environment to isolate the project's dependencies.

## 1. Create the virtual environment (named 'venv')

```bash
python3 -m venv venv
```

## 2. Activate the virtual environment

On macOS/Linux:
```bash
source venv/bin/activate
```

On Windows (Command Prompt):
```bash
venv\Scripts\activate.bat
```

On Windows (PowerShell):
```bash
venv\Scripts\Activate.ps1
```

# 3. Install project dependencies

```bash
pip install -r requirements.txt
```

(You should now see (venv) appear at the start of your command line, indicating the environment is active.)

## 1.3. Configuration File .env

The project uses an .env file to store critical environment variables (DB and Sentry).

Create a folder named database in the project root, then create an .env file inside this new folder (database/.env):

Example to create the file (Linux/macOS)
```bash
mkdir database
touch database/.env
```

The content of database/.env must be as follows:

--- DATABASE CONFIGURATION (PostgreSQL) ---
These variables are used by SQLAlchemy in app/models.py
```bash
DB_HOST=localhost
DB_NAME=epicevents_db
DB_USER=epicevents_user
DB_PASSWORD=epicevents_pass
DB_PORT=5432
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# --- SENTRY CONFIGURATION ---
# Replace <YOUR_SENTRY_DSN> with your Sentry project DSN key
SENTRY_DSN=<YOUR_SENTRY_DSN>
```


# 2. Database (PostgreSQL via Docker)

We use Docker Compose to start an isolated instance of PostgreSQL for the database.

## 2.1. Prerequisites

Ensure you have Docker and Docker Compose installed on your machine.

## 2.2. Build and Start the Database

Make sure the docker-compose.yml file is present in the root of your project.

Start the database container:
```bash
docker compose up -d
```


The PostgreSQL service is now started and accessible via localhost:5432.

# 3. Application Startup

## 3.1. Database and Role Initialization

The main.py script handles the creation of tables and the initialization of roles (Gestion, Commercial, Support) during its first run.

Run the main script
```bash
python3 main.py
```

During the first run, the system will prompt you to create a user account (the first user will be assigned the 'Gestion' role).

## 3.2. Login

Use the email and password of the created user to log in. The application will automatically route you to the menu corresponding to your department.

# 4. Error Monitoring with Sentry

This project is instrumented with the Sentry SDK to capture unhandled errors and important logs, even in production or on remote machines.

## 4.1. How Sentry is Used

Configuration: The SDK is initialized in main.py using the SENTRY_DSN variable read from database/.env.

Exception Capture: All fatal errors (uncaught exceptions) are automatically sent to your Sentry dashboard.

Informal Logging: For important actions that are not errors (like the creation of a new employee or the signing of a contract), informational messages are sent using sentry_sdk.capture_message(message, level='info').

## 4.2. Testing Sentry Integration

To verify that Sentry is working correctly, you should:

Test an Info Log (Contract Signing): Log in, update a contract by changing its status from status_signed=False to True. An informational message should appear in your Sentry dashboard.

Test a Captured Exception: Try to trigger an unexpected error (e.g., passing an incorrect data type) to see if the error appears in Sentry.

# 5. Testing

(NOTE: These instructions are based on using the pytest framework.)

## 5.1. Install the Testing Framework

```bash
pip install pytest
```

## 5.2. Run the Tests

Ensure the PostgreSQL container is started (docker compose up -d).

Run all tests:
```bash
pytest
```

If you have test files in a folder named tests/, this command will execute them automatically.