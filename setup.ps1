# setup.ps1
Write-Host "Creating Python virtual environment..."
python -m venv venv

Write-Host "Activating virtual environment..."
$env:Path = "$pwd\venv\Scripts;$env:Path"

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

Write-Host "Setup complete! To activate the environment manually in the future, run: .\venv\Scripts\Activate.ps1"
