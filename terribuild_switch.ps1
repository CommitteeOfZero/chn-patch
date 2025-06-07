function PrintSection {
    param ([string]$desc)
    $line = "------------------------------------------------------------------------"
    $len = (($line.length, $desc.legnth) | Measure -Max).Maximum
    
    Write-Host ""
    Write-Host $line.PadRight($len) -BackgroundColor DarkBlue -ForegroundColor Cyan
    Write-Host ("      >> " + $desc).PadRight($len) -BackgroundColor DarkBlue -ForegroundColor Cyan
    Write-Host $line.PadRight($len) -BackgroundColor DarkBlue -ForegroundColor Cyan
    Write-Host ""
}

Write-Output "                          ＴＥＲＲＩＢＵＩＬＤ"
Write-Output "Rated World's #1 Build Script By Leading Game Industry Officials"
Write-Output ""
Write-Output "------------------------------------------------------------------------"
Write-Output ""

PrintSection "Creating new DIST and temp"
Remove-Item -Force -Recurse -ErrorAction SilentlyContinue .\DIST
New-Item -ItemType directory -Path .\DIST | Out-Null

PrintSection "Pulling latest script changes"
cd chn-patched-scripts-builder
& git pull
cd data/txt_eng
& git pull
cd ../../..

PrintSection "Pulling subskd9 to exefs"
New-Item -ItemType directory -Path ".\DIST\atmosphere\contents\ID\exefs" | Out-Null
Invoke-RestMethod -Uri "https://github.com/CommitteeOfZero/RegionalDialect/releases/latest/download/subsdk9" -OutFile .\DIST\atmosphere\contents\ID\exefs\subsdk9

PrintSection "Patching scripts"
cd chn-patched-scripts-builder
python .\build_switch_eng.py
Copy-Item -Recurse .\out\switch_eng ..\DIST\atmosphere\contents\ID\romfs
cd ..

PrintSection "Copying assets to romfs"

$patchFolderName = "CHNSwitchPatch-v$version_string-Setup"