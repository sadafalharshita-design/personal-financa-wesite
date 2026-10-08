# Wealth — Living Product Specification

## Product
Wealth is an INR-first personal-finance decision-support application. It persists each user's accounts, transactions, monthly budget, savings goals, and What-If scenarios. The core promise is to explain what changes next, not only where money went.

## Authentication and ownership
- Local email/password authentication with PBKDF2 password hashing and a signed 7-day httpOnly session cookie.
- New users sign up, complete onboarding, then enter the protected product.
- Existing users sign in and go directly to the dashboard.
- Every private database query derives `user_id` from the server-validated session; client-provided user IDs are never accepted.

## Core flows
1. Landing → sign in or sign up.
2. New account → 3-step onboarding → initial account, budget, optional goal → dashboard.
3. Accounts → create, rename, set default, delete only when no transactions exist.
4. Transactions → create, edit, delete, bulk-delete, search, filter, sort; account balance effects are applied/reversed.
5. Budget → set monthly limit and alert threshold; usage derives from current-month completed expenses.
6. Goals → create, contribute, track remaining amount/progress/projected completion, delete.
7. What-If → ask in natural language → Gemini intent interpretation → deterministic baseline/projections/goal impact → grounded explanation → saved history.
8. Receipt scanner → upload JPG/PNG/WEBP → Gemini multimodal extraction → Pydantic validation → editable review → explicit confirmation through the standard transaction endpoint.

## Persistence model
- `users`: id, email, password_hash, name, image_url, onboarded, timestamps.
- `accounts`: id, user_id, name, type, balance_paise, is_default, timestamps.
- `transactions`: id, user_id, account_id, type, amount_paise, description, date, category, merchant, recurrence fields, status, timestamps.
- `budgets`: user_id, monthly_limit_paise, alert_threshold, timestamps.
- `goals`: id, user_id, name, target_paise, current_paise, target_date, priority, category, timestamps.
- `scenarios`: saved request, baseline, deterministic result, goal impact, AI explanation, assumptions, timestamps.
- `ai_usage`: per-user timestamps for the 10 simulations/hour limit.

Money is stored as integer paise. API responses expose rupee numbers for typed frontend formatting.

## What-If calculation rules
- Baseline averages recorded income/expenses across distinct activity months.
- AI interprets intent only. All savings, projection, affordability, and goal calculations run in Python.
- Horizons: 0, 1, 3, 6, 12 months.
- Category reductions are capped to the recorded average when that category exists.
- Affordability preserves the user-selected safety buffer.
- Goal completion uses remaining amount divided by positive monthly savings, rounded up.
- AI failures fall back to deterministic interpretation/explanation and are labeled in the UI.

## Seed facts
- Demo user is fully onboarded.
- One HDFC savings account, three months of salary/expense history, ₹35,000 monthly budget, and a partially funded MacBook Pro goal.
- Seed data supports dashboard charts, budget state, category analytics, and goal-aware simulation immediately.

## Current release boundary
Implemented: landing, local auth, onboarding, accounts, transactions, budget, goals, dashboard analytics, Gemini-backed What-If simulation, saved scenario history, Gemini receipt/bill scanning with confirmation, responsive UI, ownership checks, validation, and separate AI request limits.

Receipt images are limited to 8 MB, verified by file signature, processed in memory, and discarded after extraction. AI never writes a transaction directly.

Deferred from the broader roadmap: scheduled recurring processing, automated email reports, and third-party social authentication.