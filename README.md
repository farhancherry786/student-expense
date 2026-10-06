# SmartSpend – Student Expense Tracker

A complete Flask + SQLite expense tracker for students.

## Features

- User registration and secure password hashing
- Login/logout
- Add income and expenses
- Categories, date and notes
- Monthly budget
- Dashboard with income, expenses and remaining budget
- Category-wise spending chart
- Daily spending chart
- 80% budget warning
- 100% budget exceeded warning
- Transaction history
- Filters
- Edit/delete transactions
- Spending insight
- Demo account

## Requirements

- Python 3.10 or newer
- VS Code or another code editor
- A web browser

## Installation – Windows

Open Command Prompt or the VS Code terminal inside this project folder:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:

http://127.0.0.1:5000

## Demo account

Email:
demo@student.com

Password:
Demo@123

## Run on Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Project structure

```text
student-expense-tracker/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_transaction.html
│   ├── transactions.html
│   └── budget.html
└── static/
    ├── css/style.css
    └── js/
        ├── dashboard.js
        ├── transactions.js
        ├── add_transaction.js
        └── budget.js
```

The SQLite database is automatically created in the `instance/` directory on first run.

## Hackathon demo

1. Register or use the demo account.
2. Open Dashboard.
3. Set a monthly budget.
4. Add income.
5. Add several expenses.
6. Watch total spending and charts update.
7. When spending reaches 80%, the warning appears.
8. When spending reaches/exceeds 100%, the exceeded-budget alert appears.

## API endpoints

- `POST /api/register` – registration is handled by the web form
- `POST /api/login` – login is handled by the web form
- `GET /api/profile`
- `GET/POST /api/transactions`
- `PUT/DELETE /api/transactions/<id>`
- `GET/POST/PUT /api/budget`
- `GET /api/dashboard`
- `GET /api/category-summary`
- `GET /api/monthly-summary`
- `GET /api/insight`
