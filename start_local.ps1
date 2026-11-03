$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$containerName = "bimetrics-mongodb-local"
$volumeName = "bimetrics-mongodb-data"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI no está instalado. Instala Docker Desktop y vuelve a ejecutar este script."
}

& docker info --format "{{.ServerVersion}}" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop no está listo. Ábrelo, espera a que indique que está ejecutándose y vuelve a lanzar .\start_local.ps1."
}

if (-not (Test-Path $python)) {
    throw "No encuentro el entorno Python del proyecto en $python. Crea .venv e instala backend\requirements.txt."
}

$existingContainer = & docker ps -a --filter "name=^/$containerName$" --format "{{.Names}}"
if ($LASTEXITCODE -ne 0) {
    throw "No pude consultar Docker. Revisa que Docker Desktop esté iniciado."
}

if ($existingContainer -contains $containerName) {
    $running = & docker inspect --format "{{.State.Running}}" $containerName
    if ($running -ne "true") {
        & docker start $containerName
        if ($LASTEXITCODE -ne 0) { throw "No pude iniciar el contenedor MongoDB local existente." }
    }
} else {
    & docker run -d `
        --name $containerName `
        --publish 127.0.0.1:27017:27017 `
        --mount "source=$volumeName,target=/data/db" `
        --restart unless-stopped `
        mongo:8.0
    if ($LASTEXITCODE -ne 0) { throw "No pude crear MongoDB local con Docker." }
}

$mongoReady = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    $ping = & docker exec $containerName mongosh --quiet --eval 'db.adminCommand({ping: 1}).ok' 2>$null
    if ($LASTEXITCODE -eq 0 -and "$ping".Trim() -eq "1") {
        $mongoReady = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $mongoReady) {
    throw "El contenedor arrancó, pero MongoDB no respondió al ping. Revisa con: docker logs $containerName"
}

$previousMongoUri = $env:MONGO_URI
$hadMongoUri = Test-Path Env:MONGO_URI
$previousDnsServers = $env:MONGO_DNS_SERVERS
$hadDnsServers = Test-Path Env:MONGO_DNS_SERVERS
$previousCatalogUrl = $env:CATALOG_DATABASE_URL
$hadCatalogUrl = Test-Path Env:CATALOG_DATABASE_URL

try {
    $env:MONGO_URI = "mongodb://127.0.0.1:27017"
    $env:MONGO_DNS_SERVERS = ""
    $catalogDatabasePath = (Join-Path $projectRoot "data\catalogo-local.db").Replace("\", "/")
    $env:CATALOG_DATABASE_URL = "sqlite:///$catalogDatabasePath"
    Write-Host "MongoDB local está listo en 127.0.0.1:27017. Atlas permanece configurado en .env."
    Write-Host "El catálogo SQL de esta sesión usa data/catalogo-local.db."
    Write-Host "Iniciando la API y el frontend de BIMetrics..."
    & $python (Join-Path $projectRoot "start.py")
    if ($LASTEXITCODE -ne 0) { throw "BIMetrics terminó con código $LASTEXITCODE." }
} finally {
    if ($hadMongoUri) { $env:MONGO_URI = $previousMongoUri } else { Remove-Item Env:MONGO_URI -ErrorAction SilentlyContinue }
    if ($hadDnsServers) { $env:MONGO_DNS_SERVERS = $previousDnsServers } else { Remove-Item Env:MONGO_DNS_SERVERS -ErrorAction SilentlyContinue }
    if ($hadCatalogUrl) { $env:CATALOG_DATABASE_URL = $previousCatalogUrl } else { Remove-Item Env:CATALOG_DATABASE_URL -ErrorAction SilentlyContinue }
}
