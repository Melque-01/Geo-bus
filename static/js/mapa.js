// Geo Buss — mapa, marcação A/B e placa de tempos.

const CENTRO = [-6.0678, -49.9022]; // Parauapebas
const ZOOM = 14;

const PERFIS_RESERVA = {
    carro: { rotulo: "Carro", velocidade_kmh: 30 },
    moto: { rotulo: "Moto", velocidade_kmh: 35 },
    bicicleta: { rotulo: "Bicicleta", velocidade_kmh: 15 },
    pe: { rotulo: "A pé", velocidade_kmh: 4.8 },
};

const estado = {
    origem: null,
    destino: null,
    marcadores: {},
    linha: null,
    perfis: PERFIS_RESERVA,
    distanciaKm: null,
    tempos: null,
    calculando: false,
};

const el = {
    coordOrigem: document.getElementById("coord-origem"),
    coordDestino: document.getElementById("coord-destino"),
    botaoRota: document.getElementById("btn-rota"),
    botaoInverter: document.getElementById("btn-inverter"),
    botaoLimpar: document.getElementById("btn-limpar"),
    botaoLocal: document.getElementById("btn-local"),
    status: document.getElementById("status"),
    resultado: document.getElementById("resultado"),
    distancia: document.getElementById("distancia"),
    registro: document.getElementById("registro"),
    placa: document.getElementById("placa"),
    historico: document.getElementById("historico"),
};

const mapa = L.map("mapa", { zoomControl: true }).setView(CENTRO, ZOOM);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(mapa);

L.control.scale({ imperial: false, position: "bottomright" }).addTo(mapa);

/* ---------- utilidades ---------- */

function coordenadaTexto(ponto) {
    return `${ponto.lat.toFixed(5)}, ${ponto.lon.toFixed(5)}`;
}

function minutos(valor) {
    if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
    const arredondado = Math.round(valor * 10) / 10;
    return `${arredondado.toFixed(1).replace(".", ",")} min`;
}

function textoVelocidade(valor) {
    const arredondado = Math.round(valor * 10) / 10;
    return `${String(arredondado).replace(".", ",")} km/h`;
}

function avisar(texto, tipo = "") {
    el.status.textContent = texto;
    if (tipo) {
        el.status.dataset.tipo = tipo;
    } else {
        delete el.status.dataset.tipo;
    }
}

/* ---------- marcadores ---------- */

function icone(letra, classe) {
    return L.divIcon({
        className: "",
        html: `<span class="pin ${classe}"><b>${letra}</b></span>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
    });
}

function desenharMarcador(nome, ponto) {
    removerMarcador(nome);

    const marcador = L.marker([ponto.lat, ponto.lon], {
        icon: icone(nome === "origem" ? "A" : "B", nome === "origem" ? "pin--a" : "pin--b"),
        draggable: true,
        keyboard: true,
        title: nome === "origem" ? "Ponto A" : "Ponto B",
        alt: nome === "origem" ? "Ponto A" : "Ponto B",
    }).addTo(mapa);

    marcador.bindTooltip(coordenadaTexto(ponto), {
        className: "ponto-tooltip",
        direction: "top",
        offset: [0, -10],
    });

    marcador.on("dragend", (evento) => {
        const { lat, lng } = evento.target.getLatLng();
        const novo = { lat: Number(lat.toFixed(6)), lon: Number(lng.toFixed(6)) };
        estado[nome] = novo;
        evento.target.setTooltipContent(coordenadaTexto(novo));
        atualizarPontos();
        if (estado.origem && estado.destino) calcularRota();
    });

    estado.marcadores[nome] = marcador;
}

function removerMarcador(nome) {
    if (estado.marcadores[nome]) {
        mapa.removeLayer(estado.marcadores[nome]);
        delete estado.marcadores[nome];
    }
}

function removerLinha() {
    if (estado.linha) {
        mapa.removeLayer(estado.linha);
        estado.linha = null;
    }
}

/* ---------- estado da interface ---------- */

function atualizarPontos() {
    const temA = Boolean(estado.origem);
    const temB = Boolean(estado.destino);

    el.coordOrigem.textContent = temA ? coordenadaTexto(estado.origem) : "toque no mapa";
    el.coordDestino.textContent = temB ? coordenadaTexto(estado.destino) : "toque no mapa";
    el.coordOrigem.classList.toggle("marcado", temA);
    el.coordDestino.classList.toggle("marcado", temB);

    el.botaoRota.disabled = !(temA && temB) || estado.calculando;
    el.botaoInverter.disabled = !(temA || temB);
}

function definirPonto(ponto) {
    if (!estado.origem || (estado.origem && estado.destino)) {
        estado.origem = ponto;
        estado.destino = null;
        desenharMarcador("origem", ponto);
        removerMarcador("destino");
        removerLinha();
        esconderResultado();
        avisar("");
    } else {
        estado.destino = ponto;
        desenharMarcador("destino", ponto);
    }
    atualizarPontos();
}

function esconderResultado() {
    el.resultado.hidden = true;
    estado.distanciaKm = null;
    estado.tempos = null;
}

function limparTudo() {
    estado.origem = null;
    estado.destino = null;
    removerMarcador("origem");
    removerMarcador("destino");
    removerLinha();
    esconderResultado();
    avisar("");
    atualizarPontos();
    mapa.setView(CENTRO, ZOOM);
}

function inverterPontos() {
    if (!estado.origem) return;
    const { origem, destino } = estado;
    estado.origem = destino;
    estado.destino = origem;

    if (estado.origem) desenharMarcador("origem", estado.origem);
    else removerMarcador("origem");

    if (estado.destino) desenharMarcador("destino", estado.destino);
    else removerMarcador("destino");

    removerLinha();
    atualizarPontos();
    if (estado.origem && estado.destino) calcularRota();
}

/* ---------- placa de tempos ---------- */

function criarLinha(chave, perfil, tempoMin, rapida) {
    const linha = document.createElement("li");
    linha.className = "linha-placa" + (rapida ? " rapida" : "");
    linha.dataset.perfil = chave;

    const topo = document.createElement("div");
    topo.className = "linha-topo";

    const grupo = document.createElement("span");
    grupo.className = "modo-grupo";

    const modo = document.createElement("span");
    modo.className = "modo";
    modo.textContent = perfil.rotulo;
    grupo.append(modo);

    if (rapida) {
        const selo = document.createElement("span");
        selo.className = "selo-rapida";
        selo.textContent = "mais rápido";
        grupo.append(selo);
    }

    const tempo = document.createElement("span");
    tempo.className = "tempo";
    tempo.textContent = minutos(tempoMin);

    topo.append(grupo, tempo);

    const rotulo = document.createElement("label");
    rotulo.className = "velocidade";

    const controle = document.createElement("input");
    controle.type = "range";
    controle.min = "3";
    controle.max = "80";
    controle.step = "0.1";
    controle.value = String(perfil.velocidade_kmh);
    controle.setAttribute("aria-label", `Velocidade média — ${perfil.rotulo}`);

    const valor = document.createElement("span");
    valor.className = "kmh";
    valor.textContent = textoVelocidade(perfil.velocidade_kmh);

    rotulo.append(controle, valor);

    controle.addEventListener("input", () => {
        const velocidade = Number(controle.value);
        valor.textContent = textoVelocidade(velocidade);
        estado.perfis[chave].velocidade_kmh = velocidade;
        redesenharTempos();
    });

    linha.append(topo, rotulo);

    return linha;
}

function redesenharTempos() {
    const perfis = Object.entries(estado.perfis);
    const calculados = perfis.map(([chave, perfil]) => {
        const km = estado.distanciaKm;
        const tempo = km === null ? null : (km / perfil.velocidade_kmh) * 60;
        return { chave, perfil, tempo };
    });

    const temposValidos = calculados.filter((item) => item.tempo !== null);
    const menor = temposValidos.length ? Math.min(...temposValidos.map((i) => i.tempo)) : null;

    el.placa.textContent = "";
    calculados.forEach(({ chave, perfil, tempo }, indice) => {
        const linha = criarLinha(chave, perfil, tempo, tempo !== null && tempo === menor);
        linha.style.animationDelay = `${indice * 45}ms`;
        el.placa.append(linha);
    });
}

/* ---------- chamadas de API ---------- */

async function carregarPerfis() {
    try {
        const resposta = await fetch("/api/perfis");
        if (!resposta.ok) return;
        const dados = await resposta.json();
        if (dados && Object.keys(dados).length) {
            estado.perfis = dados;
            redesenharTempos();
        }
    } catch {
        // mantém os perfis de reserva
    }
}

async function calcularRota() {
    if (!estado.origem || !estado.destino || estado.calculando) return;

    estado.calculando = true;
    atualizarPontos();
    avisar("calculando rota…");

    try {
        const resposta = await fetch("/api/rota", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ origem: estado.origem, destino: estado.destino }),
        });
        const dados = await resposta.json();

        if (!resposta.ok || !dados.ok) {
            throw new Error(dados.erro || "não foi possível calcular a rota");
        }

        estado.distanciaKm = dados.distancia_km;
        estado.tempos = dados.tempos;

        el.distancia.textContent = `${dados.distancia_km.toFixed(2).replace(".", ",")} km`;
        el.registro.textContent = dados.salvo ? `#${dados.id}` : "não salva";
        el.resultado.hidden = false;

        desenharGeometria(dados.geometria);
        sincronizarVelocidades(dados.tempos);
        redesenharTempos();

        if (dados.salvo) {
            avisar(`rota salva como #${dados.id}`, "ok");
        } else {
            avisar(dados.aviso || "rota calculada, mas não salva", "erro");
        }

        carregarHistorico();
    } catch (erro) {
        avisar(erro.message, "erro");
    } finally {
        estado.calculando = false;
        atualizarPontos();
    }
}

function sincronizarVelocidades(tempos) {
    if (!tempos) return;
    for (const [chave, item] of Object.entries(tempos)) {
        if (estado.perfis[chave]) {
            estado.perfis[chave].velocidade_kmh = item.velocidade_kmh;
        }
    }
}

function desenharGeometria(geometria) {
    removerLinha();
    if (!geometria || !geometria.coordinates) return;

    const pontos = geometria.coordinates.map(([lon, lat]) => [lat, lon]);
    estado.linha = L.polyline(pontos, {
        color: "#f6a821",
        weight: 6,
        opacity: 0.9,
        lineCap: "round",
    }).addTo(mapa);

    mapa.fitBounds(estado.linha.getBounds(), { padding: [48, 48] });
}

async function carregarHistorico() {
    try {
        const resposta = await fetch("/api/historico?limite=6");
        if (!resposta.ok) return;
        const dados = await resposta.json();
        if (!dados.rotas) return;

        el.historico.textContent = "";

        if (!dados.rotas.length) {
            el.historico.innerHTML = '<li class="vazio">Nenhuma rota ainda.</li>';
            return;
        }

        for (const rota of dados.rotas) {
            const item = document.createElement("li");
            const botao = document.createElement("button");
            botao.type = "button";
            botao.dataset.id = rota.id;

            const km = document.createElement("span");
            km.textContent = `${(rota.distancia_m / 1000).toFixed(2).replace(".", ",")} km`;

            const meta = document.createElement("span");
            meta.className = "hist-meta";
            const data = new Date(rota.criado_em);
            meta.textContent = `#${rota.id} · ${data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;

            botao.append(km, meta);
            botao.addEventListener("click", () => abrirRotaSalva(rota.id));
            item.append(botao);
            el.historico.append(item);
        }
    } catch {
        // histórico é opcional
    }
}

async function abrirRotaSalva(id) {
    avisar(`abrindo rota #${id}…`);
    try {
        const resposta = await fetch(`/api/rota?id=${id}`);
        const dados = await resposta.json();
        if (!resposta.ok) throw new Error(dados.erro || "rota não encontrada");

        const ponto = (geo) => ({
            lat: Number(geo.coordinates[1].toFixed(6)),
            lon: Number(geo.coordinates[0].toFixed(6)),
        });

        estado.origem = ponto(dados.origem);
        estado.destino = ponto(dados.destino);
        desenharMarcador("origem", estado.origem);
        desenharMarcador("destino", estado.destino);
        atualizarPontos();

        estado.distanciaKm = dados.distancia_m / 1000;
        estado.tempos = dados.tempos;
        el.distancia.textContent = `${estado.distanciaKm.toFixed(2).replace(".", ",")} km`;
        el.registro.textContent = `#${dados.id}`;
        el.resultado.hidden = false;

        desenharGeometria(dados.geometria);
        sincronizarVelocidades(dados.tempos);
        redesenharTempos();
        avisar(`rota #${dados.id} carregada`, "ok");
    } catch (erro) {
        avisar(erro.message, "erro");
    }
}

/* ---------- eventos ---------- */

mapa.on("click", (evento) => {
    definirPonto({
        lat: Number(evento.latlng.lat.toFixed(6)),
        lon: Number(evento.latlng.lng.toFixed(6)),
    });
});

el.botaoRota.addEventListener("click", calcularRota);
el.botaoLimpar.addEventListener("click", limparTudo);
el.botaoInverter.addEventListener("click", inverterPontos);

el.botaoLocal.addEventListener("click", () => {
    if (!navigator.geolocation) {
        avisar("este navegador não informa a localização", "erro");
        return;
    }

    avisar("obtendo localização…");
    navigator.geolocation.getCurrentPosition(
        (posicao) => {
            const ponto = {
                lat: Number(posicao.coords.latitude.toFixed(6)),
                lon: Number(posicao.coords.longitude.toFixed(6)),
            };
            estado.origem = ponto;
            estado.destino = null;
            desenharMarcador("origem", ponto);
            removerMarcador("destino");
            removerLinha();
            esconderResultado();
            atualizarPontos();
            mapa.setView([ponto.lat, ponto.lon], 16);
            avisar("ponto A definido pela localização atual", "ok");
        },
        () => avisar("não foi possível obter a localização", "erro"),
        { enableHighAccuracy: true, timeout: 10000 },
    );
});

/* ---------- início ---------- */

function lerHash() {
    // link direto: /#a=-6.0678,-49.9022&b=-6.0655,-49.8930
    const bruto = window.location.hash.replace(/^#/, "");
    if (!bruto) return;

    const partes = new URLSearchParams(bruto);
    const converter = (valor) => {
        if (!valor) return null;
        const [lat, lon] = valor.split(",").map(Number);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
        return { lat, lon };
    };

    const a = converter(partes.get("a"));
    const b = converter(partes.get("b"));

    if (a) {
        estado.origem = a;
        desenharMarcador("origem", a);
    }
    if (b) {
        estado.destino = b;
        desenharMarcador("destino", b);
    }

    atualizarPontos();
    if (a && b) calcularRota();
}

atualizarPontos();
redesenharTempos();
carregarPerfis();
carregarHistorico();
lerHash();
