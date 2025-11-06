// Captura os elementos do DOM
const form = document.getElementById("form-upload");
const mensagem = document.getElementById("mensagem");
const btnEnviar = document.getElementById("btnEnviar");

// URL do backend: troque localhost pelo IP do servidor se necessário
// Ex.: const BACKEND_URL = "http://192.168.0.10:5000";
const BACKEND_URL = "http://192.168.10.10:5000"; // deixar localhost para testes na mesma máquina

form.addEventListener("submit", async (e) => {
    e.preventDefault(); // Evita reload

    const arquivo = document.getElementById("arquivo").files[0];

    if (!arquivo) {
        mensagem.textContent = "⚠️ Por favor, selecione uma planilha antes de enviar.";
        mensagem.className = "erro";
        return;
    }

    // Desabilita botão enquanto envia
    btnEnviar.disabled = true;
    btnEnviar.textContent = "Enviando...";
    mensagem.textContent = "";
    mensagem.className = "";

    const formData = new FormData();
    formData.append("arquivo", arquivo); // nome = "arquivo" -> deve coincidir com Flask

    try {
        const resposta = await fetch(`${BACKEND_URL}/upload`, {
            method: "POST",
            body: formData
        });

        // Se o servidor retornar JSON, parseamos; caso não, mostramos status
        const texto = await resposta.text();
        let resultado;
        try { resultado = JSON.parse(texto); } catch { resultado = { mensagem: texto }; }

        if (!resposta.ok) {
            throw new Error(resultado.mensagem || `Status ${resposta.status}`);
        }

        mensagem.textContent = "✅ " + (resultado.message || "Upload realizado com sucesso.");
        mensagem.className = "sucesso";
    } catch (erro) {
        mensagem.textContent = "❌ Erro: " + erro.message;
        mensagem.className = "erro";
        console.error("Erro no upload:", erro);
    } finally {
        btnEnviar.disabled = false;
        btnEnviar.textContent = "Enviar Planilha";
    }
});