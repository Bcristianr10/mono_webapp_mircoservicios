<#
Levanta toda la arquitectura de microservicios de Eduflex en el orden correcto:
red ADSL -> reverse proxy -> bases de datos -> APIs -> BFF/WebApp.
#>

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "== Verificando red ADSL ==" -ForegroundColor Cyan
$existing = docker network ls --filter name=^ADSL$ --format "{{.Name}}"
if (-not $existing) {
    docker network create --driver bridge ADSL --subnet=172.30.0.0/16
} else {
    Write-Host "La red ADSL ya existe." -ForegroundColor Yellow
}

Write-Host "== Levantando reverse_proxy ==" -ForegroundColor Cyan
Push-Location "$root/reverse_proxy"; docker compose up -d; Pop-Location

Write-Host "== Levantando micro_dbs ==" -ForegroundColor Cyan
Push-Location "$root/micro_dbs"; docker compose up -d; Pop-Location

Write-Host "== Construyendo y levantando micro_webapp (APIs) ==" -ForegroundColor Cyan
Push-Location "$root/micro_webapp"; docker compose up -d --build; Pop-Location

Write-Host "== Construyendo y levantando micro_bff_app ==" -ForegroundColor Cyan
Push-Location "$root/micro_bff_app"; docker compose up -d --build; Pop-Location

Write-Host "== Listo. Estado de los contenedores: ==" -ForegroundColor Green
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
