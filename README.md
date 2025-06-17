# Resume Suite Project

This project is a suite of applications including a Resume Builder, Cover Letter Generator, and a Mock Interview Practice tool.

## Backend Notes
## Stripe Integration Setup

To enable subscription and payment features, you need to configure several environment variables. These variables should be added to your `.env` file in the `backend` directory.

Required environment variables:

- `STRIPE_SECRET_KEY`: Your Stripe secret key (e.g., `sk_test_xxxxxxxxxxxx`).
- `STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key (e.g., `pk_test_xxxxxxxxxxxx`).
- `STRIPE_WEBHOOK_SECRET`: Your Stripe webhook signing secret for the `/stripe_webhook` endpoint (e.g., `whsec_xxxxxxxxxxxx`).
- `DOMAIN_URL`: The base URL of your application, used for redirecting after Stripe checkout. For local development, this is typically `http://127.0.0.1:5000`.

**Price IDs:**
You also need to create products and their corresponding prices in your Stripe dashboard and add their Price IDs to the `.env` file:

- `STRIPE_STARTER_PRICE_ID`: The Price ID for your 'Starter' tier subscription (e.g., `price_xxxxxxxxxxxx`).
- `STRIPE_PRO_PRICE_ID`: The Price ID for your 'Pro' tier subscription (e.g., `price_xxxxxxxxxxxx`).
- `STRIPE_CREDIT_PACK_PRICE_ID`: The Price ID for your one-time credit pack purchase (e.g., `price_xxxxxxxxxxxx`).

**Example `.env` entries:**
```
STRIPE_SECRET_KEY=sk_test_YOUR_STRIPE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_STRIPE_PUBLISHABLE_KEY
STRIPE_STARTER_PRICE_ID=price_YOUR_STARTER_PRICE_ID
STRIPE_PRO_PRICE_ID=price_YOUR_PRO_PRICE_ID
STRIPE_CREDIT_PACK_PRICE_ID=price_YOUR_CREDIT_PACK_PRICE_ID
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET
DOMAIN_URL=http://127.0.0.1:5000
```

### Local Webhook Testing
For testing the `/stripe_webhook` endpoint locally, it's recommended to use the Stripe CLI:
1. Install the [Stripe CLI](https://stripe.com/docs/stripe-cli).
2. Log in: `stripe login`
3. Forward events to your local webhook endpoint:
   ```bash
   stripe listen --forward-to http://127.0.0.1:5000/stripe_webhook
   ```
This command will provide you with a webhook signing secret to use for `STRIPE_WEBHOOK_SECRET` for local testing if you haven't configured a persistent one in your dashboard for the local endpoint.
```

## Frontend Notes

## Deployment on Render

This guide provides step-by-step instructions to deploy your Flask application to Render. This application uses a `backend/` subdirectory for the main Flask app and its `requirements.txt`, and includes steps for NLP model downloads and database migrations.

### 1. Render Deployment Overview

Render is a Platform-as-a-Service (PaaS) that simplifies deploying Flask applications. For this application, you’ll deploy a Web Service to run the Flask app with Gunicorn (a production WSGI server) and can configure a PostgreSQL database for production (recommended over SQLite for scalability). The `setup_migrations.py` script will handle database initialization during the build process.

Render will:
*   Pull your code from your connected Git repository.
*   Execute the build command to install dependencies, download NLP models, and run migrations.
*   Use the start command to launch the application.
*   Route HTTP traffic to your app via Gunicorn.

### 2. Build Command

The build command installs Python dependencies from `backend/requirements.txt`, downloads necessary NLP models (spaCy, TextBlob), and runs the `setup_migrations.py` script for database initialization or upgrades.

Set the following as your **Build Command** in Render:
```bash
pip install -r backend/requirements.txt && python -m spacy download en_core_web_sm && python -m textblob.download_corpora && python setup_migrations.py
```

**Explanation:**
*   `pip install -r backend/requirements.txt`: Installs dependencies specified in `backend/requirements.txt`.
*   `python -m spacy download en_core_web_sm`: Downloads the spaCy English model.
*   `python -m textblob.download_corpora`: Downloads TextBlob corpora.
*   `python setup_migrations.py`: Runs your migration script. Ensure `setup_migrations.py` is in the project root. This script should handle database table creation, apply migrations, and potentially manage backups. It's crucial that the `FLASK_APP=backend.app` environment variable is set for this script to function correctly.

**Note:** If using a PostgreSQL database on Render, ensure `DATABASE_URL` is set in your environment variables to override any default SQLite configuration in your application. The `setup_migrations.py` script should be designed to dynamically detect the database type based on this variable.

### 3. Start Command

The start command launches your Flask application using Gunicorn. Your application is located in `backend/app.py`, and the Flask app instance is named `app`.

Set the following as your **Start Command** in Render:
```bash
gunicorn --chdir backend app:app
```

**Explanation:**
*   `gunicorn`: Runs the Gunicorn WSGI server.
*   `--chdir backend`: Changes the working directory to `backend/` where `app.py` resides.
*   `app:app`: Specifies the Python module (`app.py`) and the Flask application instance within that module (named `app`).

Render automatically binds Gunicorn to the host `0.0.0.0` and the port specified by the `PORT` environment variable.

**Alternative (Using a `Procfile`):**
Instead of setting the start command in Render’s dashboard, you can create a `Procfile` in your project root. This is often preferred as it keeps the command under version control.

**`Procfile` content:**
```
web: gunicorn --chdir backend app:app
```
If a `Procfile` is present, Render will use it automatically.

**Note on Application Factories:** If your `backend/app.py` uses an application factory pattern (e.g., a function like `create_app()`), your start command would look like: `gunicorn --chdir backend "app:create_app()"`. Adjust accordingly based on your app's structure.

### 4. Environment Variables

Set these environment variables in Render’s dashboard under the **Environment** tab for your Web Service.

**Required Environment Variables:**
*   `FLASK_APP=backend.app`: Specifies the Flask application path for commands like those used by `setup_migrations.py` (e.g., Flask-Migrate).
*   `SECRET_KEY`: A long, random string for Flask session security and CSRF protection. Generate one using:
    ```bash
    python -c 'import secrets; print(secrets.token_hex(32))'
    ```
*   `PYTHON_VERSION=3.11`: (Or your project's Python version) Ensures Render uses the correct Python version.
*   `DATABASE_URL`: If using Render's PostgreSQL, this will be provided by Render. Set it to connect your application to the database. If not set, your application might default to SQLite (e.g., `sqlite:///instance/site.db` as per your `setup_migrations.py`).
*   `WEB_CONCURRENCY=3`: (Optional) Sets the number of Gunicorn worker processes. Adjust based on your instance type's memory (e.g., for Render's free tier, 2 or 3 might be suitable).

**Example:**
```
FLASK_APP=backend.app
SECRET_KEY=your_generated_secret_key_here
PYTHON_VERSION=3.11
DATABASE_URL=postgresql://user:password@host:port/dbname # Provided by Render for PostgreSQL
WEB_CONCURRENCY=3
```

### 5. Additional Configuration

**`Procfile` (Recommended):**
As mentioned, create a `Procfile` in the project root:
```
web: gunicorn --chdir backend app:app
```
Commit this to your repository.

**Database Setup:**
*   **SQLite (Development/Default):** Your `setup_migrations.py` might default to a local SQLite database (e.g., `sqlite:///instance/site.db`). Ensure the `instance/` directory is writable by your application if you intend for it to create the SQLite file there.
*   **PostgreSQL (Production on Render):**
    1.  In Render’s dashboard, create a new PostgreSQL service: **New > PostgreSQL**.
    2.  Configure it (e.g., name, PostgreSQL version like 15).
    3.  Once created, go to its **Info** tab and copy the **Internal Connection String** or **External Connection String** to use as your `DATABASE_URL` environment variable in your Web Service. Your `setup_migrations.py` should then use this to connect to PostgreSQL.

**`backend/requirements.txt`:**
Ensure this file (located in your `backend/` directory) is complete and includes all necessary packages. Based on your provided information, it should contain:
```
Flask==2.3.2
Flask-WTF==1.2.1
Flask-Login==0.6.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.7
alembic==1.13.2
python-docx==1.1.2
spacy==3.7.6
textblob==0.18.0.post0
gunicorn==22.0.0
psycopg2-binary==2.9.9
python-dotenv==1.0.1
# Add any other dependencies your project needs
```

**`.gitignore`:**
Ensure your `.gitignore` file (in the project root) includes entries to prevent committing unnecessary files:
```
# SQLite
instance/*.db
instance/*.db-journal
instance/backups/

# Logs and environment files
migrations.log
*.log
.env
env/
venv/
.venv/

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# Flask session files
flask_session/

# Other
.DS_Store
build/
dist/
*.egg-info/
```

### 6. Step-by-Step Deployment on Render

1.  **Prepare Your Repository:**
    *   Ensure your project structure is correct (especially `backend/app.py`, `backend/requirements.txt`, `setup_migrations.py` in root, and optionally `Procfile` in root).
    *   Commit all your latest changes to your Git repository:
        ```bash
        git add .
        git commit -m "Prepare for Render deployment"
        git push origin main # Or your deployment branch
        ```

2.  **Create a Render Account & Connect Git:**
    *   Sign up or log in at [dashboard.render.com](https://dashboard.render.com).
    *   Connect your GitHub (or GitLab/Bitbucket) account to Render if you haven't already.

3.  **Create a PostgreSQL Database (Recommended for Production):**
    *   In Render’s dashboard: **New + > PostgreSQL**.
    *   Provide a name, select a PostgreSQL version (e.g., 15), region, and instance type.
    *   Click **Create Database**.
    *   After creation, navigate to the database’s **Info** page and copy the **Internal Connection String**. You'll use this for the `DATABASE_URL` environment variable.

4.  **Create a Web Service for Your Application:**
    *   In Render’s dashboard: **New + > Web Service**.
    *   Select your Git repository and the branch to deploy.
    *   **Configuration:**
        *   **Name:** Choose a name for your service (e.g., `my-flask-app`).
        *   **Region:** Select a region.
        *   **Root Directory:** Leave blank if `setup_migrations.py` and your `Procfile` (if used) are in the root. If your entire project relevant to Render is within `backend/` (unlikely given `setup_migrations.py` in root), you might specify `backend/`. Based on your info, leave blank.
        *   **Runtime:** Select "Python".
        *   **Build Command:** `pip install -r backend/requirements.txt && python -m spacy download en_core_web_sm && python -m textblob.download_corpora && python setup_migrations.py`
        *   **Start Command:** `gunicorn --chdir backend app:app` (Render will use your `Procfile` if it exists and this field might be disabled or auto-filled).
        *   **Instance Type:** Choose an appropriate type (e.g., "Free" for testing).
    *   Click **Create Web Service**. This will typically save and trigger an initial deploy.

5.  **Set Environment Variables:**
    *   Go to your newly created Web Service's dashboard on Render.
    *   Navigate to the **Environment** tab.
    *   Add the environment variables listed in Section 4 (e.g., `FLASK_APP`, `SECRET_KEY`, `PYTHON_VERSION`, `DATABASE_URL` with the value from your Render PostgreSQL service).

6.  **Trigger Deployment (if not already started):**
    *   After setting environment variables, Render usually starts a new deployment automatically. If not, you can trigger one manually from your service's dashboard ("Manual Deploy" > "Deploy latest commit").

7.  **Monitor Logs:**
    *   Check the **Logs** and **Events** tabs in your Render service dashboard to monitor the build and deployment process. Address any errors that appear.

Your application should now be deployed on Render!
