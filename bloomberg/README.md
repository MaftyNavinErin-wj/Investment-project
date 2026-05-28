# Bloomberg VDI Export

Copy this folder to the Bloomberg VDI or the shared drive, then run:

```powershell
Push-Location "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg"
python .\bloomberg_export.py --request .\bloomberg_request.json
Pop-Location
```

If the files are directly in the `Jie` folder instead of a `bloomberg` subfolder:

```powershell
Push-Location "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python .\bloomberg_export.py --request .\bloomberg_request.json
Pop-Location
```
