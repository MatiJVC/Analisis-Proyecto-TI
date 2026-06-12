<#
.SYNOPSIS
    Crea/actualiza los roles, usuarios y client en el realm 'sistema-centralizado'
    de Keycloak, dejandolo listo para que el frontend haga login.

.DESCRIPTION
    Idempotente: se puede correr varias veces sin romper nada.
    Necesario porque el container del equipo de identidad arranca con
    --import-realm sin volumen persistente: cualquier reinicio borra los
    cambios hechos por consola.

.EXAMPLE
    .\scripts\bootstrap-keycloak.ps1
    .\scripts\bootstrap-keycloak.ps1 -KeycloakUrl http://localhost:8080
#>

[CmdletBinding()]
param(
    [string]$KeycloakUrl  = "http://localhost:8080",
    [string]$Realm        = "sistema-centralizado",
    [string]$ClientId     = "proyecto-analisis-ti",
    [string]$AdminUser    = "admin",
    [string]$AdminPass    = "admin",
    [string]$RedirectUri  = "http://localhost:3000/*",
    [string]$WebOrigin    = "http://localhost:3000"
)

$ErrorActionPreference = "Stop"

Write-Host "Bootstrap Keycloak: $KeycloakUrl realm=$Realm" -ForegroundColor Cyan

# 1) Token de admin
$body = @{ grant_type="password"; client_id="admin-cli"; username=$AdminUser; password=$AdminPass }
$admToken = (Invoke-RestMethod -Method Post -Uri "$KeycloakUrl/realms/master/protocol/openid-connect/token" -Body $body -ContentType "application/x-www-form-urlencoded").access_token
$h = @{ Authorization = "Bearer $admToken"; "Content-Type" = "application/json" }
$realmUrl = "$KeycloakUrl/admin/realms/$Realm"

# 2) Roles
Write-Host "`n[1/4] Roles..." -ForegroundColor Cyan
$roles = @(
    @{ name="admin";         description="Acceso total al sistema" },
    @{ name="analista";      description="Lectura de todos los dashboards" },
    @{ name="salud";         description="Acceso a /kpis/salud/*" },
    @{ name="subscriptions"; description="Acceso a /kpis/subscriptions/*" },
    @{ name="orders";        description="Acceso a /kpis/orders/*" },
    @{ name="incidents";     description="Acceso a /kpis/incidents/*" },
    @{ name="iot";           description="Acceso a /kpis/iot/*" },
    @{ name="notifications"; description="Acceso a /kpis/notifications/*" },
    @{ name="payments";      description="Acceso a /kpis/payments/* (placeholder)" },
    @{ name="inventory";     description="Acceso a /kpis/inventory/* (placeholder)" },
    @{ name="crm";           description="Acceso a /kpis/crm/* (placeholder)" }
)
foreach ($r in $roles) {
    try {
        Invoke-RestMethod -Method Post -Uri "$realmUrl/roles" -Headers $h -Body ($r | ConvertTo-Json) | Out-Null
        Write-Host ("   + creado: {0}" -f $r.name) -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 409) {
            Write-Host ("   = ya existia: {0}" -f $r.name) -ForegroundColor DarkGray
        } else { throw }
    }
}

# 3) Usuarios + passwords + asignacion de rol
Write-Host "`n[2/4] Usuarios y roles asignados..." -ForegroundColor Cyan
$users = @(
    @{ username="admingrupo9";    email="admin@ucn.cl";          password="admin";        role="admin" },
    @{ username="analista";       email="analista@ucn.cl";       password="Analista123!"; role="analista" },
    @{ username="salud";          email="salud@ucn.cl";          password="Salud123!";    role="salud" },
    @{ username="subscriptions";  email="subscriptions@ucn.cl";  password="Subs123!";     role="subscriptions" },
    @{ username="orders";         email="orders@ucn.cl";         password="Orders123!";   role="orders" },
    @{ username="incidents";      email="incidents@ucn.cl";      password="Inc123!";      role="incidents" },
    @{ username="iot";            email="iot@ucn.cl";            password="Iot123!";      role="iot" },
    @{ username="notificaciones"; email="notificaciones@ucn.cl"; password="Notif123!";    role="notifications" },
    @{ username="pagos";          email="pagos@ucn.cl";          password="Pagos123!";    role="payments" },
    @{ username="inventario";     email="inventario@ucn.cl";     password="Inv123!";      role="inventory" },
    @{ username="crm";            email="crm@ucn.cl";            password="Crm123!";      role="crm" }
)
foreach ($u in $users) {
    $userJson = @{
        username      = $u.username
        email         = $u.email
        enabled       = $true
        emailVerified = $true
        credentials   = @(@{ type="password"; value=$u.password; temporary=$false })
    } | ConvertTo-Json -Depth 5
    try {
        Invoke-RestMethod -Method Post -Uri "$realmUrl/users" -Headers $h -Body $userJson | Out-Null
        Write-Host ("   + usuario creado: {0}" -f $u.username) -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 409) {
            Write-Host ("   = ya existia: {0}" -f $u.username) -ForegroundColor DarkGray
            # Reset password por si esta desactualizada
            $existing = Invoke-RestMethod -Uri "$realmUrl/users?username=$($u.username)&exact=true" -Headers $h
            $resetBody = @{ type="password"; value=$u.password; temporary=$false } | ConvertTo-Json
            Invoke-RestMethod -Method Put -Uri "$realmUrl/users/$($existing[0].id)/reset-password" -Headers $h -Body $resetBody | Out-Null
        } else { throw }
    }

    # Asignar rol
    $userId = (Invoke-RestMethod -Uri "$realmUrl/users?username=$($u.username)&exact=true" -Headers $h)[0].id
    $roleObj = Invoke-RestMethod -Uri "$realmUrl/roles/$($u.role)" -Headers $h
    $body = "[" + (@{ id=$roleObj.id; name=$roleObj.name } | ConvertTo-Json -Compress) + "]"
    try {
        Invoke-RestMethod -Method Post -Uri "$realmUrl/users/$userId/role-mappings/realm" -Headers $h -Body $body | Out-Null
        Write-Host ("       rol -> [{0}]" -f $u.role) -ForegroundColor Green
    } catch {
        # Si el rol ya esta asignado, Keycloak igual responde 204; si falla por otra cosa lo propagamos
        if ($_.Exception.Response.StatusCode.value__ -ne 409) { throw }
    }
}

# 4) Client publico para el frontend
Write-Host "`n[3/4] Client '$ClientId'..." -ForegroundColor Cyan
$existing = Invoke-RestMethod -Uri "$realmUrl/clients?clientId=$ClientId" -Headers $h
if ($existing.Count -gt 0) {
    $client = $existing[0]
    $client.publicClient            = $true
    $client.standardFlowEnabled     = $true
    $client.directAccessGrantsEnabled = $true
    $client.redirectUris            = @($RedirectUri)
    $client.webOrigins              = @($WebOrigin)
    Invoke-RestMethod -Method Put -Uri "$realmUrl/clients/$($client.id)" -Headers $h -Body ($client | ConvertTo-Json -Depth 10) | Out-Null
    Write-Host "   = client '$ClientId' actualizado (redirect/origins ajustados)" -ForegroundColor DarkGray
} else {
    # Si quedo el client viejo 'proyecto-test', lo renombramos en vez de crear uno nuevo
    $old = Invoke-RestMethod -Uri "$realmUrl/clients?clientId=proyecto-test" -Headers $h
    if ($old.Count -gt 0) {
        $client = $old[0]
        $client.clientId                  = $ClientId
        $client.publicClient              = $true
        $client.standardFlowEnabled       = $true
        $client.directAccessGrantsEnabled = $true
        $client.redirectUris              = @($RedirectUri)
        $client.webOrigins                = @($WebOrigin)
        Invoke-RestMethod -Method Put -Uri "$realmUrl/clients/$($client.id)" -Headers $h -Body ($client | ConvertTo-Json -Depth 10) | Out-Null
        Write-Host "   ~ client 'proyecto-test' renombrado a '$ClientId'" -ForegroundColor Yellow
    } else {
        $newClient = @{
            clientId                  = $ClientId
            enabled                   = $true
            publicClient              = $true
            standardFlowEnabled       = $true
            directAccessGrantsEnabled = $true
            redirectUris              = @($RedirectUri)
            webOrigins                = @($WebOrigin)
        } | ConvertTo-Json -Depth 5
        Invoke-RestMethod -Method Post -Uri "$realmUrl/clients" -Headers $h -Body $newClient | Out-Null
        Write-Host "   + client '$ClientId' creado desde cero" -ForegroundColor Green
    }
}

# 5) Resumen final
Write-Host "`n[4/4] Estado final..." -ForegroundColor Cyan
$users2 = Invoke-RestMethod -Uri "$realmUrl/users?max=100" -Headers $h
foreach ($u in $users2 | Sort-Object username) {
    $rs = Invoke-RestMethod -Uri "$realmUrl/users/$($u.id)/role-mappings/realm" -Headers $h
    $names = ($rs | Where-Object { $_.name -notmatch "default-roles" } | Select-Object -ExpandProperty name) -join ", "
    Write-Host ("   {0,-18} -> [{1}]" -f $u.username, $names)
}

Write-Host "`nBootstrap completado. El frontend deberia poder hacer login." -ForegroundColor Green
