param ([string]$region)

$version_string = "1.1.2"

switch ($region) {
    "EU" { $title_id = "0100D650180CA000"; $suffix = "eng"; break }
    "US" { $title_id = "0100C17017CBC000"; $suffix = "eng"; break }
    "JP" { $title_id = "0100957016B90000"; $suffix = "jpn"; break }
    Default {}
}

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
cd coalesc3
& git pull
cd data/chaos_head/txt_eng
& git pull
cd ../../../..

PrintSection "Patching scripts and copying to romfs"
cd coalesc3
python build.py chaos_head switch $suffix --clean
Copy-Item -Recurse .\out\chaos_head\switch_$suffix ..\DIST\atmosphere\contents\$title_id\romfs
cd ..

PrintSection "Copying assets to romfs"
Copy-Item -Recurse .\c0data_switch_$suffix\* .\DIST\atmosphere\contents\$title_id\romfs

PrintSection "Building RegionalDialect and copying to exefs"
cd RegionalDialect
docker build -t regiondialect-build .
docker run --rm -v ${PWD}:/workspace regiondialect-build bash -c "cmake --preset Release . -DTITLE_ID=$title_id && cmake --build . --preset Release"
New-Item -ItemType directory -Path ..\DIST\atmosphere\contents\$title_id\exefs | Out-Null
Copy-Item .\output\Release\main.npdm ..\DIST\atmosphere\contents\$title_id\exefs\main.npdm
Copy-Item .\output\Release\subsdk9 ..\DIST\atmosphere\contents\$title_id\exefs\subsdk9
cd ..

PrintSection "Copying readme and license"
Copy-Item -Recurse .\content\* .\DIST\atmosphere\contents\$title_id

PrintSection "Clean"
Get-ChildItem -Path .\DIST -Include .gitkeep -Recurse | foreach { $_.Delete()}

PrintSection "Packing the patch"
$patchFolderName = "CHNSwitch${region}Patch-v$version_string-Setup"
cd .\DIST
7z a -mx=5 "$patchFolderName.zip" "."
Remove-Item -Force -Recurse .\atmosphere
cd ..