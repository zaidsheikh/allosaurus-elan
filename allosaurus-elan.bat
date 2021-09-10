@echo off

set PYTHONLEGACYWINDOWSIOENCODING=True
set PYTHONIOENCODING=:replace

If not exist venv\ (
  echo "Creating virtual env and installing dependencies..."
  python3 -m venv venv
  call .\venv\Scripts\activate
  python3 -m pip --no-input install -r requirements.txt
  call deactivate
)

echo "Activating venv..."
call .\venv\Scripts\activate
echo "Running allosaurus_elan.py..."
python3 .\allosaurus-elan.py
call deactivate
