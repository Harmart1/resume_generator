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

To deploy this Python application (using Poetry for dependency management) on Render, follow these steps:

1.  **Ensure `pyproject.toml` and `poetry.lock` are in your repository:**
    These files are essential for Poetry to manage your project's dependencies. Make sure they are committed to your Git repository.
    If you've added dependencies, ensure your `poetry.lock` file is up-to-date by running:
    ```bash
    poetry lock
    ```
    And commit any changes.

2.  **Create a new Web Service on Render:**
    - Go to the Render Dashboard and click "New +".
    - Select "Web Service".
    - Connect your Git repository (GitHub, GitLab, etc.).

3.  **Configure the Web Service:**
    - **Name:** Give your service a name (e.g., `my-python-app`).
    - **Region:** Choose a region closest to your users.
    - **Branch:** Select the branch you want to deploy (e.g., `main` or `master`).
    - **Root Directory:** If your application is not in the root of the repository, specify the path here. Otherwise, leave it blank.
    - **Runtime:** Select "Python 3". Render should automatically detect you're using Poetry if `pyproject.toml` is present.
    - **Build Command:** Render will likely auto-detect the build command for Poetry projects. Common options are:
        - `poetry install --no-dev --no-root` (to install only production dependencies)
        - Render might also default to `poetry install` or handle it automatically. You can often leave this as "auto" or set it explicitly if needed.
        - *Based on the user's log, Render detected Poetry, so this step might be automatically handled. The key is ensuring `pyproject.toml` and `poetry.lock` are correct.*
    - **Start Command:** This command starts your web application using Poetry.
        - For Flask applications using Gunicorn: `poetry run gunicorn app:app` (assuming your main Flask app instance is named `app` in a file named `app.py`).
        - For Django applications using Gunicorn: `poetry run gunicorn myproject.wsgi:application` (replace `myproject` with your project's name).
        - Adjust the command based on your application structure and WSGI server.
    - **Instance Type:** Choose an appropriate instance type based on your application's needs. The free tier is available for small projects.

4.  **Add Environment Variables (if any):**
    - In your service settings on Render, go to the "Environment" section.
    - Add any necessary environment variables your application requires (e.g., `DATABASE_URL`, `SECRET_KEY`, `FLASK_ENV=production`).

5.  **Deploy:**
    - Click "Create Web Service". Render will automatically build and deploy your application using your Poetry setup.
    - You can monitor the deployment logs in the Render dashboard. If the build fails, check that `pyproject.toml` and `poetry.lock` are consistent and that your start command is correct.

6.  **Set up a Custom Domain (Optional):**
    - Once deployed, you can add a custom domain in your service's settings on Render.

**Example `app.py` (for Flask, compatible with Poetry execution):**

```python
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello from Render!'

if __name__ == "__main__":
    # When run with Gunicorn via `poetry run gunicorn app:app`,
    # Gunicorn handles the port and host.
    # This __main__ block is useful for local development: `poetry run python app.py`
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
```

**Notes:**

*   Ensure your application's host is set to `0.0.0.0` in your WSGI server command (Gunicorn does this by default) to be accessible externally.
*   Render injects a `PORT` environment variable that your WSGI server (like Gunicorn) should listen on. Gunicorn typically handles this automatically.
*   The `poetry.lock` file ensures reproducible builds. Keep it consistent with `pyproject.toml`.
*   If you encounter issues, Render's logs are the first place to check. They often provide specific error messages related to Poetry or your application.
