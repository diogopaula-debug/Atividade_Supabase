
import os
from decimal import Decimal, InvalidOperation

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("")


def acessar_supabase(metodo, tabela, parametros=None, dados=None):

    resposta = requests.request(
        metodo,
        f"{SUPABASE_URL}/rest/v1/{tabela}",
        headers={
            "apikey": SUPABASE_SECRET_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        params=parametros,
        json=dados,
        timeout=10,
    )

    resposta.raise_for_status()
    return resposta.json()


@app.before_request
def conferir_configuracao():

    if request.path.startswith("/api/") or request.path in ["/clientes", "/produtos"] or request.path.startswith("/carrinho"):

        if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
            return jsonify(
                mensagem="Configure a URL e a chave do Supabase"
            ), 503


@app.get("/")
def inicio():
    return render_template("index.html")


@app.get("/api/categorias")
def listar_categorias():

    categorias = acessar_supabase(
        "GET", "categorias",
        {"select": "categoria_id,nome", "order": "nome.asc"}
    )

    return jsonify(categorias)


# Listando produtos
@app.get("/api/produtos")
def listar_produtos():

    produtos = acessar_supabase(
        "GET", "produtos",
        {
            "select": "produto_id,nome,preco,estoque,categorias(nome)",
            "order": "produto_id.desc"
        },
    )

    return jsonify(produtos)


# Rota para o HTML carregar os produtos
@app.get("/produtos")
def produtos_loja():

    produtos = listar_produtos().get_json()

    for produto in produtos:
        produto["id"] = produto["produto_id"]

    return jsonify(produtos)


# Rota para cadastrar produtos
@app.post("/api/produtos")
def cadastrar_produto():

    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify(mensagem="Envie um objeto JSON válido."), 400

    campos = ["nome", "preco", "estoque", "categoria_id"]

    for campo in campos:
        if not isinstance(dados.get(campo), str):
            return jsonify(
                mensagem=f"O campo {campo} deve ser preenchido com texto"
            ), 400

    nome = dados["nome"].strip()
    texto_preco = dados["preco"].strip().replace(",", ".")
    texto_estoque = dados["estoque"].strip()
    texto_categoria = dados["categoria_id"].strip()

    if len(nome) < 3 or len(nome) > 80:
        return jsonify(
            mensagem="O nome deve ter de 3 a 80 caracteres"
        ), 400

    try:
        preco = Decimal(texto_preco)
        estoque = int(texto_estoque)
        categoria_id = int(texto_categoria)

    except (InvalidOperation, ValueError):
        return jsonify(
            mensagem="Informe preço numérico, estoque inteiro e categoria válida"
        ), 400

    if not preco.is_finite() or preco <= 0 or preco > Decimal("999999.99"):
        return jsonify(
            mensagem="O preço deve estar entre R$ 0,01 e R$ 999999,99"
        ), 400

    if preco != preco.quantize(Decimal("0.01")):
        return jsonify(
            mensagem="O preço deve ter no máximo duas casas decimais"
        ), 400

    if estoque < 0 or estoque > 1000000:
        return jsonify(
            mensagem="O estoque deve estar entre 0 e 1000000 unidades"
        ), 400

    if categoria_id <= 0:
        return jsonify(mensagem="Selecione uma categoria válida"), 400

    categorias = acessar_supabase(
        "GET", "categorias",
        {
            "select": "categoria_id",
            "categoria_id": f"eq.{categoria_id}"
        },
    )

    if not categorias:
        return jsonify(
            mensagem="A categoria informada não existe"
        ), 400

    acessar_supabase(
        "POST", "produtos",
        dados={
            "nome": nome,
            "preco": str(preco),
            "estoque": estoque,
            "categoria_id": categoria_id,
        }
    )

    return jsonify(mensagem="Produto cadastrado com sucesso"), 201


@app.post("/clientes")
def cadastrar_cliente():

    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify(mensagem="Envie os dados em JSON válido"), 400

    nome = str(dados.get("nome") or "").strip()
    email = str(dados.get("email") or "").strip()
    telefone = str(dados.get("telefone") or "").strip()

    if not nome:
        return jsonify(mensagem="O nome é obrigatório"), 400

    if not email or "@" not in email:
        return jsonify(mensagem="Informe um e-mail válido"), 400

    cliente = acessar_supabase(
        "POST", "clientes",
        dados={
            "nome": nome,
            "email": email,
            "telefone": telefone or None
        }
    )

    return jsonify(
        mensagem="Cliente cadastrado com sucesso!",
        cliente=cliente[0]
    ), 201


@app.get("/clientes")
def listar_clientes():

    clientes = acessar_supabase(
        "GET", "clientes",
        {
            "select": "cliente_id,nome,email,telefone",
            "order": "nome.asc"
        }
    )

    for cliente in clientes:
        cliente["id"] = cliente["cliente_id"]

    return jsonify(clientes)


@app.post("/carrinho")
def adicionar_carrinho():

    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify(mensagem="Dados inválidos"), 400

    try:
        cliente_id = int(dados.get("cliente_id"))
        produto_id = int(dados.get("produto_id"))
        quantidade = int(dados.get("quantidade"))

    except (TypeError, ValueError):
        return jsonify(mensagem="Informe cliente, produto e quantidade válidos"), 400

    if cliente_id <= 0 or produto_id <= 0:
        return jsonify(mensagem="Selecione um cliente e produto válidos"), 400

    if quantidade <= 0:
        return jsonify(mensagem="A quantidade deve ser maior que zero"), 400

    clientes = acessar_supabase(
        "GET", "clientes",
        {
            "select": "cliente_id",
            "cliente_id": f"eq.{cliente_id}"
        }
    )

    if not clientes:
        return jsonify(mensagem="Cliente não encontrado"), 404

    produtos = acessar_supabase(
        "GET", "produtos",
        {
            "select": "produto_id",
            "produto_id": f"eq.{produto_id}"
        }
    )

    if not produtos:
        return jsonify(mensagem="Produto não encontrado"), 404

    duplicado = acessar_supabase(
        "GET", "carrinho",
        {
            "select": "carrinho_id",
            "cliente_id": f"eq.{cliente_id}",
            "produto_id": f"eq.{produto_id}"
        }
    )

    if duplicado:
        return jsonify(
            mensagem="Este produto já está no carrinho deste cliente!"
        ), 409

    item = acessar_supabase(
        "POST", "carrinho",
        dados={
            "cliente_id": cliente_id,
            "produto_id": produto_id,
            "quantidade": quantidade
        }
    )

    return jsonify(
        mensagem="Produto adicionado ao carrinho!",
        item=item[0]
    ), 201


@app.get("/carrinho/<int:cliente_id>")
def listar_carrinho(cliente_id):

    itens = acessar_supabase(
        "GET", "carrinho",
        {
            "select": "carrinho_id,cliente_id,produto_id,quantidade,produtos(nome,preco)",
            "cliente_id": f"eq.{cliente_id}",
            "order": "carrinho_id.asc"
        }
    )

    resultado = []

    for item in itens:

        produto = item.get("produtos") or {}

        if isinstance(produto, list):
            produto = produto[0] if produto else {}

        preco = Decimal(str(produto.get("preco", "0")))
        quantidade = int(item["quantidade"])

        resultado.append({
            "id": item["carrinho_id"],
            "nome": produto.get("nome", "Produto"),
            "quantidade": quantidade,
            "preco": float(preco),
            "subtotal": float(preco * quantidade)
        })

    return jsonify(resultado)


@app.delete("/carrinho/<int:carrinho_id>")
def remover_carrinho(carrinho_id):

    itens = acessar_supabase(
        "DELETE", "carrinho",
        {
            "carrinho_id": f"eq.{carrinho_id}",
            "select": "carrinho_id"
        }
    )

    if not itens:
        return jsonify(mensagem="Item não encontrado"), 404

    return jsonify(mensagem="Produto removido com sucesso!")


@app.errorhandler(requests.exceptions.RequestException)
def tratar_erro_supabase(erro):

    app.logger.warning(
        "Falha no acesso ao Supabase: %s",
        type(erro).__name__
    )

    if isinstance(erro, requests.exceptions.HTTPError):

        try:
            detalhe = erro.response.json()
        except ValueError:
            detalhe = {}

        codigo = detalhe.get("code") if isinstance(detalhe, dict) else None

        if codigo == "23505":
            return jsonify(
                mensagem="Este registro já existe no banco de dados"
            ), 409

        if codigo == "23503":
            return jsonify(
                mensagem="Um dos registros relacionados não está disponível"
            ), 409

        if codigo == "23514":
            return jsonify(
                mensagem="Os dados não atendem às regras do banco"
            ), 400

    return jsonify(
        mensagem="Não foi possível acessar o banco. Tente novamente"
    ), 503


@app.errorhandler(500)
def tratar_erro_inesperado(erro):

    return jsonify(
        mensagem="Ocorreu uma falha interna."
    ), 500


if __name__ == "__main__":

    app.run(host="127.0.0.1", port=5000, debug=False)
