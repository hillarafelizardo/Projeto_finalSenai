import os
import uuid
import json
import subprocess
import tempfile
from datetime import datetime, date
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)

# Configurações
# pasta backend
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
AD_JOBS_DIR = BASE_DIR / "ad-jobs"
AD_SCRIPTS_DIR = BASE_DIR / "ad-scripts"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AD_JOBS_DIR, exist_ok=True)
os.makedirs(AD_SCRIPTS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"xls", "xlsx"}
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB limite de upload

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def limpa_numeros(s: str) -> str:
    return ''.join(filter(str.isdigit, str(s)))

def cpf_valido(cpf: str) -> bool:
    """
    Validação do CPF com cálculo dos dígitos verificadores.
    Retorna True se válido.
    """
    cpf = limpa_numeros(cpf)
    if len(cpf) != 11:
        return False
    # rejeita sequências repetidas
    if cpf == cpf[0] * 11:
        return False
    def calc_digitos(nums: str) -> int:
        soma = sum(int(n) * p for n, p in zip(nums, range(len(nums)+1, 1, -1)))
        resto = (soma * 10) % 11
        return resto if resto < 10 else 0
    d1 = calc_digitos(cpf[:9])
    d2 = calc_digitos(cpf[:9] + str(d1))
    return cpf.endswith(f"{d1}{d2}")

def parse_date_safe(value):
    """Tenta converter para datetime.date; se vazio retorna None."""
    if pd.isna(value) or value in ("", None):
        return None
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


# frontend está um nível acima da pasta backend
FRONTEND_FOLDER = BASE_DIR.parent / "frontend"
@app.route('/')
def home():
    return send_from_directory(FRONTEND_FOLDER, "index.html")

@app.route('/frontend/<path:filename>')
def frontend_files(filename):
    return send_from_directory(FRONTEND_FOLDER, filename)


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'arquivo' not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400
        file = request.files['arquivo']
        if file.filename == '':
            return jsonify({"error": "Nome de arquivo inválido"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "Formato de arquivo inválido. Use .xls ou .xlsx"}), 400

        # Salva em arquivo temporário para evitar conflitos de nomes
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4()}-{filename}"
        filepath = UPLOAD_FOLDER / unique_name
        file.save(filepath)

        # Leitura da planilha (tenta engine apropriado)
        ext = filepath.suffix.lower().lstrip('.')
        read_kwargs = {}
        if ext == 'xlsx':
            read_kwargs['engine'] = 'openpyxl'  # exige openpyxl instalado
        try:
            df = pd.read_excel(filepath, **read_kwargs)
        except Exception as e:
            return jsonify({"error": "Falha ao ler planilha: " + str(e)}), 400

        # Verifica colunas mínimas
        required = {"Nome", "CPF"}
        if not required.issubset(set(df.columns)):
            return jsonify({"error": f"Planilha deve conter colunas {sorted(list(required))}"}), 400

        registros = []
        for idx, row in df.iterrows():
            cpf_raw = row.get('CPF', '')
            cpf = limpa_numeros(cpf_raw)

    # === Desativando validação de CPF para teste ===
    # if not cpf_valido(cpf):
    #     print(f"Ignorado CPF inválido na linha {idx+1}: {cpf_raw}")
    #     continue


            nome = str(row.get('Nome', '')).strip()
            inicio = parse_date_safe(row.get('Inicio', None))
            fim = parse_date_safe(row.get('Fim', None))

            # Decide operação: create (se sem fim), disable (se possuir fim passado ou presente)
            operation = "create"
            if fim is not None:
                # Se a data fim já passou ou é hoje consideramos disable
                if fim <= date.today():
                    operation = "disable"
                else:
                    # se fim futura, talvez agendar; aqui marcamos como 'scheduled_disable'
                    operation = "scheduled_disable"
            # username como CPF (ou ajuste necessário)
            username = cpf

            registros.append({
                "nome": nome,
                "cpf": cpf,
                "inicio": inicio.isoformat() if inicio else "",
                "fim": fim.isoformat() if fim else "",
                "operation": operation,
                "username": username
            })

        if not registros:
            return jsonify({"error": "Nenhum registro válido encontrado na planilha"}), 400

        job_id = str(uuid.uuid4())
        json_path = UPLOAD_FOLDER / f"usuarios-{job_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"job_id": job_id, "registros": registros}, f, indent=2, ensure_ascii=False)

        # Path do script PowerShell 
        ps_script = AD_SCRIPTS_DIR / "process-job.ps1"
        if not ps_script.exists():
            print(f"[AVISO] Script PowerShell não encontrado ({ps_script}). Simulando execução...") 
            fake_output = f"Simulação: {len(registros)} usuários processados com sucesso."
            return jsonify({
                "message": "Upload processado com sucesso (modo simulado)",
                "job_id": job_id,
                "json": str(json_path),
                "ps_stdout": fake_output
                })
    


        # Executa PowerShell de forma segura; captura output
        try:
            result = subprocess.run(
                ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(ps_script), "-FilePath", str(json_path)],
                capture_output=True,
                text=True,
                timeout=120  # ajuste conforme necessário
            )
        except subprocess.TimeoutExpired as e:
            return jsonify({"error": "Timeout ao executar script PowerShell", "details": str(e)}), 500

        # Checa retorno
        if result.returncode != 0:
            # inclui stdout/stderr para debugging (não expor detalhes sensíveis em produção)
            return jsonify({
                "error": "Falha ao executar script PowerShell",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500

        # Sucesso
        return jsonify({
            "message": "Upload processado com sucesso",
            "job_id": job_id,
            "json": str(json_path),
            "ps_stdout": result.stdout.strip()
        })
    except Exception as e:
        # Evite expor stacktrace em produção; aqui retornamos mensagem simples
        return jsonify({"error": "Erro interno", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5500, debug=True)