// Impede acesso direto sem login
if (localStorage.getItem("autenticado") !== "true") {
    window.location.href = "login.html";
}

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
        mensagem.textContent = "! Por favor, selecione uma planilha antes de enviar!";
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

        mensagem.textContent = "OK " + (resultado.message || "Upload realizado com sucesso.");
        mensagem.className = "sucesso";
    } catch (erro) {
        mensagem.textContent = " Erro: " + erro.message;
        mensagem.className = "erro";
        console.error("Erro no upload:", erro);
    } finally {
        btnEnviar.disabled = false;
        btnEnviar.textContent = "Enviar Planilha";
    }
});
// ==== MODAL DE USUÁRIOS CRIADOS ====
const btnUsers = document.getElementById("btnUsers");
const modalUsers = document.getElementById("modalUsers");
const fecharModal = document.getElementById("fecharModal");
const filtroUsuario = document.getElementById("filtroUsuario");
const usuariosCorpo = document.getElementById("usuariosCorpo");

btnUsers.addEventListener("click", async () => {
  modalUsers.style.display = "block";
  await carregarUsuarios();
});

fecharModal.addEventListener("click", () => {
  modalUsers.style.display = "none";
});

window.addEventListener("click", (event) => {
  if (event.target === modalUsers) {
    modalUsers.style.display = "none";
  }
});

async function carregarUsuarios() {
  try {
    const resp = await fetch(`${BACKEND_URL}/uploads/usuarios.json`);
    if (!resp.ok) throw new Error("Erro ao buscar usuários");
    const dados = await resp.json();
    preencherTabela(dados.registros);
  } catch (erro) {
    usuariosCorpo.innerHTML = `<tr><td colspan="5">Erro ao carregar: ${erro.message}</td></tr>`;
  }
}

function preencherTabela(lista) {
  if (!lista || lista.length === 0) {
    usuariosCorpo.innerHTML = "<tr><td colspan='5'>Nenhum usuário encontrado</td></tr>";
    return;
  }

  usuariosCorpo.innerHTML = lista.map(u => `
    <tr>
      <td>${u.nome}</td>
      <td>${u.username}</td>
      <td>${u.inicio || '-'}</td>
      <td>${u.fim || '-'}</td>
      <td>${u.operation === "create" ? " Criado" :
           u.operation === "disable" ? " Desativado" :
           " Agendado"}</td>
    </tr>
  `).join("");
}

filtroUsuario.addEventListener("input", () => {
  const termo = filtroUsuario.value.toLowerCase();
  const linhas = usuariosCorpo.getElementsByTagName("tr");

  for (let linha of linhas) {
    const texto = linha.innerText.toLowerCase();
    linha.style.display = texto.includes(termo) ? "" : "none";
  }
});
function logout() {
    localStorage.removeItem("autenticado");
    window.location.href = "login.html";
}
