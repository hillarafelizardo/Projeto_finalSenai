param (
    [string]$FilePath
)

if (-not $FilePath) {
    $folder = "C:\backend\uploads"
    # Pega o arquivo mais recente que comece com 'usuarios' e termine com '.json'
    $jsonFile = Get-ChildItem -Path $folder -Filter "usuarios*.json" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $jsonFile) {
        Write-Error "Nenhum arquivo de usuários encontrado em $folder"
        exit 1
    }

    $FilePath = $jsonFile.FullName
    Write-Host "📂 Usando arquivo mais recente: $FilePath"
}


function Write-Log {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Write-Host "[$timestamp] $Message"
}

Write-Log "Iniciando processamento do arquivo JSON: $FilePath"

if (-not (Test-Path $FilePath)) {
    Write-Error "Arquivo JSON não encontrado: $FilePath"
    exit 1
}

# Importa módulo AD
try {
    Import-Module ActiveDirectory -ErrorAction Stop
    Write-Log "Módulo ActiveDirectory importado com sucesso."
} catch {
    Write-Error "Falha ao importar módulo ActiveDirectory."
    exit 1
}

# Lê JSON
try {
    $data = Get-Content -Path $FilePath -Raw | ConvertFrom-Json
    $usuarios = $data.registros
    Write-Log "Total de registros: $($usuarios.Count)"
} catch {
    Write-Error "Erro ao ler arquivo JSON: $_"
    exit 1
}

$hoje = Get-Date

foreach ($u in $usuarios) {
    $nome = $u.nome
    $usuario = $u.username
    $inicio = if ($u.inicio) { [datetime]$u.inicio } else { $hoje }
    $fim = if ($u.fim) { [datetime]$u.fim } else { $null }

    Write-Log "---------------------------------------------"
    Write-Log "Usuário: $nome ($usuario)"
    Write-Log "Data início: $inicio | Data final: $fim"

    $existe = Get-ADUser -Filter "SamAccountName -eq '$usuario'" -ErrorAction SilentlyContinue

    # DELETE automático se data final atingida
    if ($fim -and $hoje -ge $fim) {
        if ($existe) {
            Write-Log "Excluindo conta (data final atingida)..."
            try {
                Remove-ADUser -Identity $usuario -Confirm:$false
                Write-Log "Conta excluída com sucesso!"
            } catch {
                Write-Error "Erro ao excluir usuário $usuario: $_"
            }
        } else {
            Write-Log "Usuário não encontrado no AD para exclusão."
        }
        continue
    }

    # CREATE automático na data de início
    if ($hoje -ge $inicio -and -not $existe) {
        Write-Log "Criando conta no AD..."
        try {
            New-ADUser `
                -Name $nome `
                -SamAccountName $usuario `
                -UserPrincipalName "$usuario@senai.local" `
                -AccountPassword (ConvertTo-SecureString "Senha@134" -AsPlainText -Force) `
                -Enabled $true `
                -ChangePasswordAtLogon $false `
                -Path "OU=OUusers,DC=senai,DC=local"
            Write-Log "Conta criada com sucesso!"
        } catch {
            Write-Error "Erro ao criar usuário $usuario: $_"
        }
    } elseif ($existe) {
        Write-Log "Usuário já existe. Nenhuma ação necessária."
    } else {
        Write-Log "Usuário ainda não deve ser criado (antes da data de início)."
    }
}

Write-Log "Processamento concluído."
exit 0