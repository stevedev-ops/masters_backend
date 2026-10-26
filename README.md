# The Masters - Django REST API Backend (Render Ready)

A clean, production-ready Django REST Framework backend engineered for **The Masters Barber & Executive Spa** platform.

---

## 🔐 Default Production Credentials

| Account | Username | Password | Role & Permissions |
| :--- | :--- | :--- | :--- |
| **Boss / Admin** | `admin` | `masters2026!` | Full Executive Access, Tip Payoffs, Pricing, Expenses Audit |
| **Shee (Worker)** | `shee` | `masters123` | Staff Portal, Dual Service (Barber & Spa) Tips, Expense Logger |

---

## 🚀 Quick Start (Local Development)

```bash
# 1. Enter the backend directory
cd backend

# 2. Activate virtual environment
source venv/bin/activate

# 3. Run migrations & seed data (creates users & catalog)
python manage.py migrate
python manage.py seed_masters

# 4. Start local development server
python manage.py runserver 127.0.0.1:8000
```

The API will be live at:
- **API Root**: [http://127.0.0.1:8000/api/](http://127.0.0.1:8000/api/)
- **Auth Login**: `POST http://127.0.0.1:8000/api/auth/login/`
- **Django Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- **Services Catalog**: [http://127.0.0.1:8000/api/services/](http://127.0.0.1:8000/api/services/)
- **Staff Team**: [http://127.0.0.1:8000/api/staff/](http://127.0.0.1:8000/api/staff/)
- **Transactions Ledger**: [http://127.0.0.1:8000/api/transactions/](http://127.0.0.1:8000/api/transactions/)
- **Operational Expenses**: [http://127.0.0.1:8000/api/expenses/](http://127.0.0.1:8000/api/expenses/)
- **Shift Closings**: [http://127.0.0.1:8000/api/closing_records/](http://127.0.0.1:8000/api/closing_records/)

---

## ☁️ Deploying to Render (with PostgreSQL)

### Step 1: Create a PostgreSQL Database on Render
1. Go to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **PostgreSQL**.
3. Name: `masters-postgres`
4. Database Name: `masters_db`
5. Select the **Starter ($7/mo)** plan.
6. Click **Create Database**. Copy the **Internal Database URL**.

### Step 2: Create the Web Service for the API
1. In Render, click **New +** -> **Web Service**.
2. Connect your GitHub repository: `stevedev-ops/masters`.
3. Configure the settings:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn masters_core.wsgi:application`
   - **Plan**: Starter
4. Under **Environment Variables**, add:
   - `DATABASE_URL`: (Paste the connection string from Step 1, or link directly via Render UI)
   - `SECRET_KEY`: (Click generate or enter a secure random key)
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `.onrender.com,localhost,127.0.0.1`

### Step 3: Connect Frontend to Render Backend
In your frontend (e.g. Vercel or Render static site), set the environment variable:
```env
VITE_API_URL=https://your-masters-api.onrender.com/api
```