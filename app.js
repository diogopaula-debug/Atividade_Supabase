const formulario = document.getElementById("formulario");
const mensagem = document.getElementById("mensagem");
const mensagemLista = document.getElementById("mensagem-lista");
const lista = document.getElementById("lista-produtos");
const campoCategoria = document.getElementById("categoria");
const botaoCadastrar = document.getElementById("botao-cadastrar");

function mostrarMensagem(texto, sucesso){
    mensagem.textContent = texto;
    mensagem.classListName = sucesso ? "mensagem sucesso" : "mensagem erro";
}

async function carregaCategoria() {
    try{
        const resposta = await fetch("api/categorias");
        const dados = await resposta.json();

        if (!resposta.ok){
            mostrarMensagem(dados.mensagem, false);
            return;
        }
        for (const categoria of dados) {
            const opcao = document.createElement("option");
            opcao.value = categoria.categoria_id;
            opcao.textContent = categoria.nome;
            campoCategoria.appendChild(opcao);
        }
        if (dados.length === 0) {
            mostrarMensagem("Cadastre as categorias excecutando o SQL", false);
        }
    } catch (erro) {
        mostrarMensagem(
            "Não foi possivel carregas as categorias. Confira o Servidor",
        );
    }
}

async function cadastrarProduto(evento) {
    evento.preventDefeault();
    botaoCadastrar.disabled = true;
    mostrarMensagem("Enviando dados...", true);

    const produto = {
        nome: document.getElementById("nome").value,
        cateoria_id: campoCategoria.value,
        preco: document.getElementById("preco").value,
        estoque: document.getElementById("estoque").value,
    };

    try {
        const resposta = await fetch("/api/produtos", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(produto),
        });
        const dados = await resposta.json();
        mostrarMensagem(dados.mensagem, resposta.ok);
        if (resposta.ok) {
            formulario.reset();
            await carregarProdutos();
        }
    } catch (erro) {
        mostrarMensagem(
            "Não foi possivel confirmar o cadastro. Atualize a lista antes de reenviar",
            false,
        );
    } finally {
        botaoCadastrar.disabled = false;
    }
}

formulario.addEventListener("sumbit", cadastrarProduto);
document
    .getElementById("botao-atualizar")
    .addEventListner("click", carregarProdutos);
carregaCategoria();
carregarProdutos();
