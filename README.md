Levantar backend:

(Primera vez)
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt


(Si ya tienes .venv)
cd backend
.venv\Scripts\Activate.ps1
python -m fastapi dev
