# Caminho fixo do arquivo JSON
$FilePath = "C:\Projeto_finalSenai\backend\uploads\usuarios.json"

if (-not (Test-Path $FilePath)) {
    Write-Error "Arquivo usuarios.json não encontrado em $FilePath"
    exit 1
}

# Função para log
function Write-Log {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Write-Host "[$timestamp] $Message"
}

Write-Log "Iniciando processamento do arquivo JSON: $FilePath"

# Importa módulo AD
try {
    Import-Module ActiveDirectory -ErrorAction Stop
    Write-Log "Módulo ActiveDirectory importado com sucesso."
} catch {
    Write-Error "Falha ao importar módulo ActiveDirectory: $_"
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

    try {
        $filter = "SamAccountName -eq `"$usuario`""
        $existe = Get-ADUser -Filter $filter -ErrorAction SilentlyContinue
    } catch {
        Write-Error "Erro ao consultar usuário ${usuario}: $_"
        continue
    }

    if ($fim -and $hoje -ge $fim) {
        if ($existe) {
            Write-Log "Excluindo conta (data final atingida)..."
            try {
                Remove-ADUser -Identity $usuario -Confirm:$false
                Write-Log "Conta excluída com sucesso!"
            } catch {
                Write-Error "Erro ao excluir usuário ${usuario}: $_"
            }
        } else {
            Write-Log "Usuário não encontrado no AD para exclusão."
        }
        continue
    }

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
            Write-Error "Erro ao criar usuário ${usuario}: $_"
        }
    } elseif ($existe) {
        Write-Log "Usuário já existe. Nenhuma ação necessária."
    } else {
        Write-Log "Usuário ainda não deve ser criado (antes da data de início)."
    }
}

Write-Log "Processamento concluído."
exit 0
