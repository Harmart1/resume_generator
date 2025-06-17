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

To deploy this application on Render, follow these steps:

1.  **Ensure you have a `requirements.txt` file:**
    This file lists all the Python dependencies required by your application. You can generate it using:
    ```bash
    pip freeze > requirements.txt
    ```
    Commit this file to your repository.

2.  **Create a new Web Service on Render:**
    - Go to the Render Dashboard and click "New +".
    - Select "Web Service".
    - Connect your Git repository (GitHub, GitLab, etc.).

3.  **Configure the Web Service:**
    - **Name:** Give your service a name (e.g., `my-python-app`).
    - **Region:** Choose a region closest to your users.
    - **Branch:** Select the branch you want to deploy (e.g., `main` or `master`).
    - **Root Directory:** If your application is not in the root of the repository, specify the path here. Otherwise, leave it blank.
    - **Runtime:** Select "Python 3".
    - **Build Command:** Render usually auto-detects this for Python projects. A common command is `pip install -r requirements.txt`.
    - **Start Command:** This command starts your web application.
        - For Flask applications using Gunicorn: `gunicorn app:app` (assuming your main Flask app instance is named `app` in a file named `app.py`).
        - For Django applications using Gunicorn: `gunicorn myproject.wsgi:application` (replace `myproject` with your project's name).
        - Adjust the command based on your application structure and WSGI server.
    - **Instance Type:** Choose an appropriate instance type based on your application's needs. The free tier is available for small projects.

4.  **Add Environment Variables (if any):**
    - In your service settings on Render, go to the "Environment" section.
    - Add any necessary environment variables your application requires (e.g., `DATABASE_URL`, `SECRET_KEY`, `FLASK_ENV=production`).

5.  **Deploy:**
    - Click "Create Web Service". Render will automatically build and deploy your application.
    - You can monitor the deployment logs in the Render dashboard.

6.  **Set up a Custom Domain (Optional):**
    - Once deployed, you can add a custom domain in your service's settings on Render.

**Example `app.py` (for Flask):**

```python
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello from Render!'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
```

**Notes:**

*   Make sure your application's host is set to `0.0.0.0` to be accessible externally.
*   Render injects a `PORT` environment variable that your application should listen on. The example above shows how to use it.
*   For more complex applications or specific frameworks, refer to the official Render documentation for Python.
