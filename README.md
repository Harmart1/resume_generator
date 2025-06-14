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
