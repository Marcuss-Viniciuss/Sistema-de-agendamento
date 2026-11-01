// Endereço da API FastAPI (muda aqui se a porta ou o host forem outros)
const API_URL = "http://127.0.0.1:8000";
const CHAVE_TOKEN = "agenda_token";

// Estado da aplicação
let token = lerToken();
let utilizador = null;
let agendamentos = [];
let filtroAtivo = "todos";

const $ = (id) => document.getElementById(id);

// ---------- Token (localStorage) ----------

function lerToken() {
  try { return localStorage.getItem(CHAVE_TOKEN); } catch (e) { return null; }
}
function guardarToken(valor) {
  token = valor;
  try {
    if (valor) localStorage.setItem(CHAVE_TOKEN, valor);
    else localStorage.removeItem(CHAVE_TOKEN);
  } catch (e) { /* localStorage indisponível: a sessão dura até fechar o separador */ }
}

// ---------- Chamadas à API ----------

// Todas as chamadas passam por aqui, por isso o token vai sempre no cabeçalho
async function api(caminho, opcoes = {}) {
  const cabecalhos = { "Content-Type": "application/json" };
  if (token) cabecalhos["Authorization"] = "Bearer " + token;

  let resposta;
  try {
    resposta = await fetch(API_URL + caminho, { ...opcoes, headers: cabecalhos });
  } catch (e) {
    throw new Error("Não consegui ligar à API. Confirma que o servidor está a correr na porta 8000.");
  }

  if (resposta.status === 204) return null;
  const corpo = await resposta.json().catch(() => ({}));

  if (!resposta.ok) {
    // Sessão inválida fora do ecrã de login: volta ao login
    if (resposta.status === 401 && utilizador) terminarSessao("A sessão expirou. Inicia sessão outra vez.");
    const erro = new Error(textoDoErro(resposta.status, corpo));
    erro.estado = resposta.status;
    throw erro;
  }
  return corpo;
}

function textoDoErro(estado, corpo) {
  // "Not Found" é o 404 genérico do FastAPI: a rota não existe no servidor que respondeu.
  // Quase sempre é um servidor antigo ainda a correr (as nossas rotas têm mensagens próprias).
  if (estado === 404 && corpo.detail === "Not Found") {
    return "A API em " + API_URL + " não reconhece este endereço. Provavelmente há um servidor antigo a correr: pára todos os processos do uvicorn e arranca de novo.";
  }
  if (typeof corpo.detail === "string") return corpo.detail;   // mensagens escritas na API
  if (estado === 422) return "Verifica os campos: algum está vazio ou inválido.";
  return "Algo correu mal no servidor. Tenta outra vez.";
}

// ---------- Ecrãs e mensagens ----------

function mostrarEcra(nome) {
  $("ecra-login").hidden = nome !== "login";
  $("ecra-app").hidden = nome !== "app";
}

function aviso(texto, tipo) {
  const div = document.createElement("div");
  div.className = "aviso " + tipo;
  div.textContent = texto;
  $("avisos").appendChild(div);
  setTimeout(() => div.remove(), 5000);
}

function mostrarErro(elemento, texto) {
  elemento.textContent = texto;
  elemento.hidden = !texto;
}

// ---------- Sessão ----------

function iniciarSessao(dados) {
  guardarToken(dados.access_token);
  utilizador = dados.utilizador;
  const admin = utilizador.role === "admin";

  document.body.classList.toggle("eh-admin", admin);
  $("nome-utilizador").textContent = utilizador.nome;
  $("papel-utilizador").textContent = admin ? "Administrador" : "Cliente";
  $("titulo-pagina").textContent = admin ? "Agenda da barbearia" : "As minhas marcações";
  $("subtitulo-pagina").textContent = admin
    ? "Vista global de todos os clientes da barbearia."
    : "Marca o teu próximo corte e acompanha as tuas marcações.";
  $("campo-cliente").hidden = !admin;

  mostrarEcra("app");
  carregar();
}

function terminarSessao(mensagem) {
  guardarToken(null);
  utilizador = null;
  agendamentos = [];
  mostrarEcra("login");
  if (mensagem) mostrarErro($("erro-login"), mensagem);
}

// Ao abrir a página: se já há token, tenta retomar a sessão
async function arrancar() {
  if (!token) return mostrarEcra("login");
  try {
    const eu = await api("/auth/me");
    iniciarSessao({ access_token: token, utilizador: eu });
  } catch (e) {
    terminarSessao(token ? e.message : "");
  }
}

// ---------- Login e registo ----------

function alternarSeparador(entrar) {
  $("form-login").hidden = !entrar;
  $("form-registo").hidden = entrar;
  $("tab-entrar").classList.toggle("ativo", entrar);
  $("tab-registo").classList.toggle("ativo", !entrar);
  $("tab-entrar").setAttribute("aria-selected", entrar);
  $("tab-registo").setAttribute("aria-selected", !entrar);
  mostrarErro($("erro-login"), "");
}
$("tab-entrar").addEventListener("click", () => alternarSeparador(true));
$("tab-registo").addEventListener("click", () => alternarSeparador(false));

async function enviarAuth(caminho, corpo) {
  mostrarErro($("erro-login"), "");
  try {
    iniciarSessao(await api(caminho, { method: "POST", body: JSON.stringify(corpo) }));
    $("form-login").reset();
    $("form-registo").reset();
  } catch (e) {
    mostrarErro($("erro-login"), e.message);
  }
}

$("form-login").addEventListener("submit", (ev) => {
  ev.preventDefault();
  enviarAuth("/auth/login", { email: $("login-email").value, password: $("login-password").value });
});

$("form-registo").addEventListener("submit", (ev) => {
  ev.preventDefault();
  if ($("reg-password").value.length < 8) {
    return mostrarErro($("erro-login"), "A palavra-passe precisa de pelo menos 8 caracteres.");
  }
  enviarAuth("/auth/registo", {
    nome: $("reg-nome").value,
    email: $("reg-email").value,
    password: $("reg-password").value,
  });
});

$("btn-sair").addEventListener("click", () => terminarSessao(""));

// ---------- Dados e tabela ----------

async function carregar() {
  try {
    agendamentos = await api("/agendamentos");
    desenhar();
  } catch (e) {
    aviso(e.message, "erro");
  }
}

function hojeISO() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}

function desenhar() {
  const hoje = hojeISO();
  const total = (fn) => agendamentos.filter(fn).length;

  $("stat-hoje").textContent = total((a) => a.inicio.startsWith(hoje));
  $("stat-pendentes").textContent = total((a) => a.estado === "pendente");
  $("stat-concluidos").textContent = total((a) => a.estado === "concluido");

  const visiveis = agendamentos.filter((a) => {
    if (filtroAtivo === "hoje") return a.inicio.startsWith(hoje);
    if (filtroAtivo === "pendente" || filtroAtivo === "concluido") return a.estado === filtroAtivo;
    return true;
  });

  const corpo = $("corpo-tabela");
  corpo.innerHTML = "";
  visiveis.forEach((a) => corpo.appendChild(criarLinha(a)));

  const vazio = $("vazio");
  vazio.hidden = visiveis.length > 0;
  if (agendamentos.length === 0) {
    vazio.textContent = "Ainda não há marcações. Usa o botão «Novo agendamento» para criar a primeira.";
  } else {
    vazio.textContent = "Nenhuma marcação corresponde a este filtro.";
  }
}

function celula(texto, classe) {
  const td = document.createElement("td");
  td.textContent = texto;
  if (classe) td.className = classe;
  return td;
}

function criarLinha(a) {
  const tr = document.createElement("tr");
  const data = new Date(a.inicio).toLocaleDateString("pt-PT", { day: "numeric", month: "short", year: "numeric" });

  tr.append(celula(data), celula(a.inicio.slice(11, 16), "hora"), celula(a.cliente, "so-admin"), celula(a.servico));

  const tdEstado = document.createElement("td");
  const etiqueta = document.createElement("span");
  etiqueta.className = "estado " + a.estado;
  etiqueta.textContent = a.estado === "concluido" ? "Concluído" : "Pendente";
  tdEstado.appendChild(etiqueta);
  tr.appendChild(tdEstado);

  // Ações: só o administrador as vê (e o servidor também as exige)
  const tdAcoes = document.createElement("td");
  tdAcoes.className = "so-admin col-acoes";
  const concluir = botaoAcao(a.estado === "concluido" ? "Reabrir" : "Concluir", "secundario", () =>
    mudarEstado(a.id, a.estado === "concluido" ? "pendente" : "concluido"));
  const apagar = botaoAcao("Cancelar", "perigo", () => apagarAgendamento(a));
  tdAcoes.append(concluir, apagar);
  tr.appendChild(tdAcoes);

  return tr;
}

function botaoAcao(texto, tipo, aoClicar) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "btn pequeno " + tipo;
  b.textContent = texto;
  b.addEventListener("click", aoClicar);
  return b;
}

async function mudarEstado(id, estado) {
  try {
    await api("/agendamentos/" + id, { method: "PATCH", body: JSON.stringify({ estado }) });
    aviso(estado === "concluido" ? "Marcação concluída." : "Marcação reaberta.", "sucesso");
    carregar();
  } catch (e) {
    aviso(e.message, "erro");
  }
}

async function apagarAgendamento(a) {
  if (!confirm("Cancelar a marcação de " + a.cliente + " às " + a.inicio.slice(11, 16) + "?")) return;
  try {
    await api("/agendamentos/" + a.id, { method: "DELETE" });
    aviso("Marcação cancelada.", "sucesso");
    carregar();
  } catch (e) {
    aviso(e.message, "erro");
  }
}

document.querySelectorAll(".filtro").forEach((botao) => {
  botao.addEventListener("click", () => {
    filtroAtivo = botao.dataset.filtro;
    document.querySelectorAll(".filtro").forEach((b) => b.classList.toggle("ativo", b === botao));
    desenhar();
  });
});

// ---------- Modal: novo agendamento ----------

let slotEscolhido = null;   // hora escolhida, ex: "14:30"
let pedidoSlots = 0;        // numera os pedidos, para ignorar respostas antigas se a data mudar depressa

function limparSlots(mensagem) {
  slotEscolhido = null;
  $("slots").innerHTML = "";
  $("slots-estado").textContent = mensagem;
  atualizarBotao();
}

// Pede à API as horas livres de um dia e desenha um botão por hora
async function carregarSlots(data) {
  if (!data) return limparSlots("Escolhe uma data para ver as horas livres.");

  const pedido = ++pedidoSlots;
  limparSlots("A carregar horários…");
  try {
    const dia = await api("/horarios-disponiveis?data=" + data);
    if (pedido !== pedidoSlots) return;   // entretanto escolheu outra data

    if (!dia.aberto) return limparSlots("Fechado ao fim de semana. Escolhe um dia útil (segunda a sexta).");
    if (dia.horarios.length === 0) return limparSlots("Não há horas livres neste dia. Tenta outra data.");

    $("slots-estado").textContent = "Horas livres (blocos de " + dia.duracao_minutos + " min):";
    dia.horarios.forEach((hora) => {
      const botao = document.createElement("button");
      botao.type = "button";
      botao.className = "slot";
      botao.textContent = hora;
      botao.setAttribute("aria-pressed", "false");
      botao.addEventListener("click", () => {
        slotEscolhido = hora;
        document.querySelectorAll(".slot").forEach((b) => {
          b.classList.toggle("selecionado", b === botao);
          b.setAttribute("aria-pressed", b === botao);
        });
        atualizarBotao();
      });
      $("slots").appendChild(botao);
    });
  } catch (e) {
    if (pedido === pedidoSlots) limparSlots(e.message);
  }
}

// O botão "Guardar" só fica ativo com serviço, data e hora escolhidos
// (e o nome do cliente, quando é o administrador a marcar)
function atualizarBotao() {
  const admin = utilizador && utilizador.role === "admin";
  const completo = $("ag-servico").value && $("ag-data").value && slotEscolhido
    && (!admin || $("ag-cliente").value.trim());
  $("btn-guardar").disabled = !completo;
}
["ag-servico", "ag-data", "ag-cliente"].forEach((id) => {
  $(id).addEventListener("input", atualizarBotao);
  $(id).addEventListener("change", atualizarBotao);
});

$("ag-data").addEventListener("change", () => carregarSlots($("ag-data").value));

$("btn-novo").addEventListener("click", () => {
  mostrarErro($("erro-modal"), "");
  $("form-agendamento").reset();
  $("ag-data").min = hojeISO();   // não deixa escolher dias passados
  limparSlots("Escolhe uma data para ver as horas livres.");
  $("modal").showModal();
});
$("btn-fechar").addEventListener("click", () => $("modal").close());

$("form-agendamento").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const admin = utilizador.role === "admin";
  const data = $("ag-data").value;
  const servico = $("ag-servico").value.trim();

  if (!servico || !data || (admin && !$("ag-cliente").value.trim())) {
    return mostrarErro($("erro-modal"), "Preenche todos os campos antes de guardar.");
  }
  if (!slotEscolhido) {
    return mostrarErro($("erro-modal"), "Escolhe uma das horas livres.");
  }

  const corpo = { servico, inicio: data + "T" + slotEscolhido };
  if (admin) corpo.cliente = $("ag-cliente").value.trim();

  $("btn-guardar").disabled = true;
  try {
    await api("/agendamentos", { method: "POST", body: JSON.stringify(corpo) });
    $("modal").close();
    aviso("Agendamento guardado.", "sucesso");
    carregar();
  } catch (e) {
    mostrarErro($("erro-modal"), e.message);
    // 409: outra pessoa ficou com essa hora entretanto, por isso atualiza as horas livres
    if (e.estado === 409) carregarSlots(data);
  } finally {
    atualizarBotao();
  }
});

arrancar();
