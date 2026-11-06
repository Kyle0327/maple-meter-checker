$ErrorActionPreference = 'Stop'
python -m unittest discover -s $PSScriptRoot -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
python -m PyInstaller --noconfirm --onedir --noupx --clean --windowed --name MapleMeterChecker --version-file "$PSScriptRoot\version.txt" --icon "$PSScriptRoot\checker.ico" --add-data "$PSScriptRoot\glyphs.json;." --add-data "$PSScriptRoot\checker.ico;." --add-data "$PSScriptRoot\checker.png;." --add-data "$PSScriptRoot\brand-mark.png;." --add-data "$PSScriptRoot\panel-mark.png;." --add-data "$PSScriptRoot\Pretendard-Bold.otf;." --add-data "$PSScriptRoot\Pretendard-ExtraBold.otf;." --distpath "$PSScriptRoot\dist" --workpath "$PSScriptRoot\build" --specpath $PSScriptRoot "$PSScriptRoot\app.py"
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
