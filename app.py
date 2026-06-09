import csv
import io
import json
import os
import threading
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Blueprint,
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

from buscar_precos import comparar_precos, comparar_precos_produto, playwright_disponivel
from catalogo_precos import (
    AJUDA_EMISSAO,
    AJUDA_MIDIA_A1,
    AJUDA_MIDIA_A3,
    AJUDA_PREFERENCIAS_INTRO,
    AJUDA_SECAO_A1,
    AJUDA_SECAO_A3,
    AJUDA_VALIDADE,
    AJUDA_ONDE_USAR,
    AJUDA_ONDE_USAR_INTRO,
    AJUDA_WIZARD_INTRO,
    AJUDA_PROFISSAO,
    AJUDA_FINALIDADE,
    AJUDA_EMITE_COMO,
    PERGUNTA_WIZARD,
    CONTEXTO_WIZARD,
    OPCOES_ONDE_USAR,
    AJUDA_VARIOS_COMPUTADORES,
    AJUDA_USO_CELULAR,
    OPCOES_EMISSAO,
    OPCOES_MIDIA_A1,
    OPCOES_MIDIA_A3,
    OPCOES_VALIDADE,
    aplicar_precos_catalogo_vet,
    catalogo_precisa_atualizar,
    filtros_de_vet,
    info_catalogo,
    iniciar_varredura_background,
    init_catalogo,
    parse_onde_usar_form,
    parse_preferencias_form,
)
from certificado import (
    CERTIFICADORAS,
    ETAPAS_CERTIFICADO,
    ETAPAS_RECEITUARIO,
    TIPOS_CERTIFICADO,
    TIPOS_NAO_USAR,
    calcular_valores,
    certificadoras_ativas,
    dados_para_certificadora,
    info_tipo,
    label_certificado,
    texto_pedido_certificadora,
    texto_whatsapp_orientacao,
    url_certificadora,
    ac_credenciada_iti,
    aviso_icp_certificadora,
    rotulo_icp_certificadora,
    url_iti_certificadora,
    ITI_REPOSITORIO,
    ITI_LISTA_AC,
    ITI_VALIDAR,
)
from guia_passos import (
    ETAPAS_USUARIO,
    guia_certificadora,
    guia_implementar_certificado,
    legislacao_por_profissao,
)
from modelo_guia import gerar_html_guia
from pix import gerar_pix_copia_cola, qr_code_base64
from recomendacao import FINALIDADES, PRODUTOS, PROFISSOES, produtos_comparacao, recomendar, _cnpj_informado, produto_id_efetivo, tipo_certificado_efetivo

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-in-production")

_database_url = os.getenv("DATABASE_URL", "").strip()
if _database_url:
    if _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///veterinarios.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
CERTIFICADORA_PADRAO = os.getenv("CERTIFICADORA_PADRAO", "certisign")
PIX_CHAVE = os.getenv("PIX_CHAVE", "99f89727-3fb9-4982-b54e-74dc097a078a")
PIX_NOME = os.getenv("PIX_NOME", "VICTOR NEVES")
PIX_CIDADE = os.getenv("PIX_CIDADE", "SALVADOR")

# Normaliza chave Pix telefone (+55...); e-mail e chave aleatória ficam como estão
_chave = PIX_CHAVE.strip()
if "@" not in _chave and "-" not in _chave and _chave.replace("+", "").replace(" ", "").isdigit():
    digits = "".join(c for c in _chave if c.isdigit())
    if not _chave.startswith("+"):
        PIX_CHAVE = f"+{digits}" if digits.startswith("55") else f"+55{digits}"

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ESTADOS_BR = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


class Veterinario(db.Model):
    __tablename__ = "veterinarios"

    id = db.Column(db.Integer, primary_key=True)
    protocolo = db.Column(db.String(20), unique=True, nullable=False)

    # Dados pessoais
    nome_completo = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    rg = db.Column(db.String(20))
    data_nascimento = db.Column(db.Date)
    crmv = db.Column(db.String(20), nullable=False)
    crmv_uf = db.Column(db.String(2), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)

    # Endereço
    cep = db.Column(db.String(10), nullable=False)
    logradouro = db.Column(db.String(200), nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)

    # Serviço contratado
    tipo_certificado = db.Column(db.String(10), nullable=False, default="A1")
    solicita_receituario = db.Column(db.Boolean, default=False)
    codigo_desconto = db.Column(db.String(30))

    # Certificado — fluxo de aquisição
    status_certificado = db.Column(db.String(30), default="cadastrado")
    certificadora = db.Column(db.String(30))
    numero_pedido_certificadora = db.Column(db.String(50))
    data_pedido_certificadora = db.Column(db.DateTime)
    data_emissao = db.Column(db.DateTime)
    data_validade = db.Column(db.Date)

    # Receituário
    status_receituario = db.Column(db.String(30), default="nao_solicitado")

    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Fluxo público (wizard)
    cnpj = db.Column(db.String(18))
    eh_veterinario = db.Column(db.Boolean, default=True)
    emite_como = db.Column(db.String(10), default="pf")
    varios_computadores = db.Column(db.Boolean, default=False)
    produto_recomendado = db.Column(db.String(30))
    motivo_recomendacao = db.Column(db.Text)
    certificadora_recomendada = db.Column(db.String(30))
    precos_json = db.Column(db.Text)
    etapa_usuario = db.Column(db.String(30), default="recomendacao")
    origem = db.Column(db.String(20), default="admin")
    profissao = db.Column(db.String(30), default="outro")
    finalidade = db.Column(db.String(30), default="documentos")
    sistema_receituario = db.Column(db.String(100))
    certificadora_escolhida = db.Column(db.String(30))
    preferencia_midia = db.Column(db.String(20))
    preferencia_emissao = db.Column(db.String(30), default="videoconferencia")
    preferencia_validade_anos = db.Column(db.Integer, default=1)

    @staticmethod
    def gerar_protocolo():
        ultimo = Veterinario.query.order_by(Veterinario.id.desc()).first()
        seq = (ultimo.id + 1) if ultimo else 1
        return f"CERT{datetime.now().strftime('%Y%m%d')}{seq:04d}"

    def endereco_completo(self):
        partes = [
            f"{self.logradouro}, {self.numero}",
            self.complemento,
            self.bairro,
            f"{self.cidade}/{self.uf}",
            f"CEP {self.cep}",
        ]
        return " - ".join(p for p in partes if p)

    def etapa_atual_index(self):
        keys = [e[0] for e in ETAPAS_CERTIFICADO]
        try:
            return keys.index(self.status_certificado)
        except ValueError:
            return 0

    def pode_avancar_etapa(self):
        return self.etapa_atual_index() < len(ETAPAS_CERTIFICADO) - 1

    def proxima_etapa(self):
        idx = self.etapa_atual_index()
        if idx < len(ETAPAS_CERTIFICADO) - 1:
            return ETAPAS_CERTIFICADO[idx + 1][0]
        return None

    def valores_referencia(self):
        return calcular_valores(
            self.tipo_certificado,
            self.certificadora or CERTIFICADORA_PADRAO,
        )

    def produto_info(self):
        pid = self.produto_recomendado or f"e-cpf-{self.tipo_certificado.lower()}"
        return PRODUTOS.get(pid)

    def precos_lista(self):
        if not self.precos_json:
            return []
        try:
            return json.loads(self.precos_json)
        except json.JSONDecodeError:
            return []

    def melhor_preco(self):
        for p in self.precos_lista():
            if p.get("melhor_preco"):
                return p
        return None

    def etapa_usuario_index(self):
        keys = [e[0] for e in ETAPAS_USUARIO]
        try:
            return keys.index(self.etapa_usuario or "recomendacao")
        except ValueError:
            return 0


class PrecoCatalogo(db.Model):
    __tablename__ = "precos_catalogo"

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(120), unique=True, nullable=False, index=True)
    certificadora = db.Column(db.String(30), nullable=False, index=True)
    produto_tipo = db.Column(db.String(20), nullable=False, index=True)
    categoria = db.Column(db.String(2), nullable=False)
    armazenamento = db.Column(db.String(2), nullable=False)
    midia = db.Column(db.String(40))
    emissao = db.Column(db.String(30))
    validade_anos = db.Column(db.Integer, default=1)
    preco = db.Column(db.Float, nullable=False)
    url = db.Column(db.String(500))
    observacao = db.Column(db.Text)
    fonte = db.Column(db.String(30))
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow)


class CatalogoMeta(db.Model):
    __tablename__ = "catalogo_meta"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="vazio")
    iniciado_em = db.Column(db.DateTime)
    concluido_em = db.Column(db.DateTime)
    itens_total = db.Column(db.Integer, default=0)
    erro = db.Column(db.Text)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


def _migrate_db():
    """Adiciona colunas novas em bancos SQLite já existentes."""
    insp = inspect(db.engine)
    if "veterinarios" not in insp.get_table_names():
        return
    existentes = {c["name"] for c in insp.get_columns("veterinarios")}
    novas = {
        "cnpj": "VARCHAR(18)",
        "eh_veterinario": "BOOLEAN DEFAULT 1",
        "emite_como": "VARCHAR(10) DEFAULT 'pf'",
        "varios_computadores": "BOOLEAN DEFAULT 0",
        "produto_recomendado": "VARCHAR(30)",
        "motivo_recomendacao": "TEXT",
        "certificadora_recomendada": "VARCHAR(30)",
        "precos_json": "TEXT",
        "etapa_usuario": "VARCHAR(30) DEFAULT 'recomendacao'",
        "origem": "VARCHAR(20) DEFAULT 'admin'",
        "profissao": "VARCHAR(30) DEFAULT 'outro'",
        "finalidade": "VARCHAR(30) DEFAULT 'documentos'",
        "sistema_receituario": "VARCHAR(100)",
        "certificadora_escolhida": "VARCHAR(30)",
        "preferencia_midia": "VARCHAR(20)",
        "preferencia_emissao": "VARCHAR(30) DEFAULT 'videoconferencia'",
        "preferencia_validade_anos": "INTEGER DEFAULT 1",
    }
    for coluna, typedef in novas.items():
        if coluna not in existentes:
            db.session.execute(text(f"ALTER TABLE veterinarios ADD COLUMN {coluna} {typedef}"))
    db.session.commit()


def _garantir_precos_catalogo(vet, *, forcar_varredura: bool = False) -> list:
    """Consulta catálogo local; dispara varredura em background se estiver desatualizado."""
    precos = aplicar_precos_catalogo_vet(vet, db.session)
    if forcar_varredura or catalogo_precisa_atualizar():
        iniciar_varredura_background(app)
    return precos


def _aplicar_recomendacao(vet, rec):
    produto = rec["produto"]
    vet.produto_recomendado = rec["produto_id"]
    vet.tipo_certificado = rec["tipo_armazenamento"]
    vet.motivo_recomendacao = rec["motivo"]
    if rec.get("observacoes"):
        obs = "\n".join(rec["observacoes"])
        vet.observacoes = f"{vet.observacoes}\n{obs}".strip() if vet.observacoes else obs


def _buscar_e_salvar_precos(vet, produto_id, usar_cache=True):
    if not playwright_disponivel():
        return []
    resultados = comparar_precos_produto(produto_id, usar_cache=usar_cache)
    vet.precos_json = json.dumps(resultados, ensure_ascii=False)
    melhor = next((r for r in resultados if r.get("melhor_preco")), None)
    if melhor:
        vet.certificadora_recomendada = melhor["certificadora"]
        vet.certificadora = melhor["certificadora"]
    return resultados


_scrape_lock = threading.Lock()
_scrape_jobs: dict[str, dict] = {}


def _redirect_jornada_precos(protocolo: str) -> str:
    """URL relativa — seguro em thread de background (sem request Flask ativo)."""
    return f"/p/{protocolo.upper()}?precos_ok=1"


def _run_scrape_precos_async(protocolo: str, produto_id: str) -> None:
    """Busca preços em thread — evita timeout de proxy/Safari em requisição longa."""
    key = protocolo.upper()
    with app.app_context():
        try:
            vet = Veterinario.query.filter_by(protocolo=key).first()
            if not vet:
                raise ValueError("Protocolo não encontrado.")
            _buscar_e_salvar_precos(vet, produto_id, usar_cache=False)
            db.session.commit()
            redirect = _redirect_jornada_precos(protocolo)
            with _scrape_lock:
                _scrape_jobs[key] = {"status": "done", "ok": True, "redirect": redirect}
        except Exception as exc:
            db.session.rollback()
            with _scrape_lock:
                _scrape_jobs[key] = {
                    "status": "error",
                    "ok": False,
                    "erro": str(exc)[:200],
                }


def _iniciar_scrape_precos(protocolo: str, produto_id: str) -> dict:
    key = protocolo.upper()
    vet = Veterinario.query.filter_by(protocolo=key).first()
    if vet:
        vet.precos_json = None
        db.session.commit()
    with _scrape_lock:
        job = _scrape_jobs.get(key)
        if job and job.get("status") == "running":
            return {"ok": False, "pending": True, "started": False}
        _scrape_jobs[key] = {"status": "running"}
    thread = threading.Thread(
        target=_run_scrape_precos_async,
        args=(protocolo, produto_id),
        daemon=True,
    )
    thread.start()
    return {"ok": False, "pending": True, "started": True}


def _status_scrape_precos(protocolo: str) -> dict:
    key = protocolo.upper()
    with _scrape_lock:
        job = _scrape_jobs.get(key)
    if job:
        if job.get("status") == "done":
            return {"ok": True, "redirect": job["redirect"]}
        if job.get("status") == "error":
            return {"ok": False, "erro": job.get("erro", "Erro ao buscar preços.")}
        return {"ok": False, "pending": True}
    vet = Veterinario.query.filter_by(protocolo=key).first()
    if vet and vet.precos_json:
        return {
            "ok": True,
            "redirect": _redirect_jornada_precos(protocolo),
        }
    return {"ok": False, "pending": True}


with app.app_context():
    db.create_all()
    _migrate_db()
    init_catalogo(db, PrecoCatalogo, CatalogoMeta)
    from catalogo_precos import importar_catalogo_seed

    importar_catalogo_seed()
    if os.getenv("CATALOGO_VARREDURA_INICIO", "1") == "1":
        if PrecoCatalogo.query.count() == 0 or catalogo_precisa_atualizar():
            iniciar_varredura_background(app)


def _ctx_preferencias() -> dict:
    return {
        "opcoes_emissao": OPCOES_EMISSAO,
        "opcoes_midia_a1": OPCOES_MIDIA_A1,
        "opcoes_midia_a3": OPCOES_MIDIA_A3,
        "opcoes_validade": OPCOES_VALIDADE,
        "ajuda_preferencias_intro": AJUDA_PREFERENCIAS_INTRO,
        "ajuda_emissao": AJUDA_EMISSAO,
        "ajuda_midia_a1": AJUDA_MIDIA_A1,
        "ajuda_midia_a3": AJUDA_MIDIA_A3,
        "ajuda_validade": AJUDA_VALIDADE,
        "ajuda_secao_a1": AJUDA_SECAO_A1,
        "ajuda_secao_a3": AJUDA_SECAO_A3,
        "ajuda_onde_usar": AJUDA_ONDE_USAR,
        "ajuda_onde_usar_intro": AJUDA_ONDE_USAR_INTRO,
        "ajuda_wizard_intro": AJUDA_WIZARD_INTRO,
        "ajuda_profissao": AJUDA_PROFISSAO,
        "ajuda_finalidade": AJUDA_FINALIDADE,
        "ajuda_emite_como": AJUDA_EMITE_COMO,
        "pergunta_wizard": PERGUNTA_WIZARD,
        "contexto_wizard": CONTEXTO_WIZARD,
        "opcoes_onde_usar": OPCOES_ONDE_USAR,
        "ajuda_varios_computadores": AJUDA_VARIOS_COMPUTADORES,
        "ajuda_uso_celular": AJUDA_USO_CELULAR,
    }


@app.context_processor
def inject_icp_helpers():
    return {
        "ac_credenciada_iti": ac_credenciada_iti,
        "aviso_icp_certificadora": aviso_icp_certificadora,
        "rotulo_icp_certificadora": rotulo_icp_certificadora,
        "url_iti_certificadora": url_iti_certificadora,
        "url_certificadora": url_certificadora,
        "iti_repositorio": ITI_REPOSITORIO,
        "iti_lista_ac": ITI_LISTA_AC,
        "iti_validar": ITI_VALIDAR,
        **_ctx_preferencias(),
    }


# ── Site público ──────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify(status="ok", playwright=playwright_disponivel())


@app.route("/")
def index():
    return render_template("public/index.html")


@app.route("/comecar", methods=["GET", "POST"])
def comecar():
    if request.method == "POST":
        nome = request.form.get("nome_completo", "").strip()
        email = request.form.get("email", "").strip().lower()
        whatsapp = request.form.get("whatsapp", "").strip()
        cpf = request.form.get("cpf", "").strip()

        if not all([nome, email, whatsapp, cpf]):
            flash("Preencha nome, e-mail, WhatsApp e CPF.", "error")
            return render_template(
                "public/comecar.html",
                estados=ESTADOS_BR,
                profissoes=PROFISSOES,
                finalidades=FINALIDADES,
                **_ctx_preferencias(),
            )

        eh_vet = request.form.get("eh_veterinario") == "sim"
        profissao = request.form.get("profissao", "outro").strip()
        if profissao not in PROFISSOES:
            profissao = "veterinario" if eh_vet else "outro"
        finalidade = request.form.get("finalidade", "documentos")
        if finalidade not in FINALIDADES:
            finalidade = "documentos"
        emite_como = request.form.get("emite_como", "pf")
        if emite_como not in ("pf", "pj", "ambos"):
            emite_como = "pf"
        cnpj = request.form.get("cnpj", "").strip() or None
        if emite_como in ("pj", "ambos") and not _cnpj_informado(cnpj):
            flash(
                "Informe o CNPJ da clínica/empresa ou marque «Como pessoa física (CPF)» "
                "se você não emite pelo CNPJ.",
                "error",
            )
            return render_template(
                "public/comecar.html",
                estados=ESTADOS_BR,
                profissoes=PROFISSOES,
                finalidades=FINALIDADES,
                **_ctx_preferencias(),
            )
        onde = parse_onde_usar_form(request.form)
        varios_pc = onde["varios_computadores"]
        tipo_arm_prev = "A3" if varios_pc else "A1"
        prefs = parse_preferencias_form(request.form, tipo_arm=tipo_arm_prev)
        if onde.get("preferencia_midia"):
            prefs["preferencia_midia"] = onde["preferencia_midia"]
        elif onde.get("usa_celular") and prefs["preferencia_midia"] not in ("nuvem", "mobileid"):
            prefs["preferencia_midia"] = "nuvem"
        registro = request.form.get("registro_profissional", "").strip() or request.form.get("crmv", "").strip() or "—"
        registro_uf = request.form.get("registro_uf", "").strip().upper() or request.form.get("crmv_uf", "").strip().upper() or "NA"
        sistema = request.form.get("sistema_receituario", "").strip() or None

        rec = recomendar(
            profissao=profissao,
            emite_como=emite_como,
            varios_computadores=varios_pc,
            finalidade=finalidade,
            cnpj=cnpj,
            preferencia_midia=prefs["preferencia_midia"],
        )

        vet = Veterinario(
            protocolo=Veterinario.gerar_protocolo(),
            nome_completo=nome,
            cpf=cpf,
            crmv=registro,
            crmv_uf=registro_uf,
            email=email,
            telefone=whatsapp,
            whatsapp=whatsapp,
            cep="—",
            logradouro="—",
            numero="—",
            bairro="—",
            cidade="—",
            uf=registro_uf if registro_uf != "NA" else "BA",
            cnpj=cnpj,
            eh_veterinario=(profissao == "veterinario"),
            profissao=profissao,
            finalidade=finalidade,
            sistema_receituario=sistema,
            emite_como=emite_como,
            varios_computadores=varios_pc,
            preferencia_midia=prefs["preferencia_midia"],
            preferencia_emissao=prefs["preferencia_emissao"],
            preferencia_validade_anos=prefs["preferencia_validade_anos"],
            origem="publico",
            status_certificado="cadastrado",
            etapa_usuario="precos",
        )
        _aplicar_recomendacao(vet, rec)
        db.session.add(vet)
        db.session.commit()

        _garantir_precos_catalogo(vet)
        return redirect(url_for("jornada", protocolo=vet.protocolo, precos_ok=1))

    return render_template(
        "public/comecar.html",
        estados=ESTADOS_BR,
        profissoes=PROFISSOES,
        finalidades=FINALIDADES,
        **_ctx_preferencias(),
    )


@app.route("/p/<protocolo>")
def jornada(protocolo):
    vet = Veterinario.query.filter_by(protocolo=protocolo.upper()).first_or_404()
    produto = vet.produto_info()
    profissao = vet.profissao or ("veterinario" if vet.eh_veterinario else "outro")
    rec_secundario = None
    rec_observacoes = []
    produtos_cmp = PRODUTOS
    if vet.produto_recomendado:
        rec = recomendar(
            profissao=profissao,
            emite_como=vet.emite_como or "pf",
            varios_computadores=bool(vet.varios_computadores),
            finalidade=vet.finalidade or "documentos",
            cnpj=vet.cnpj,
            preferencia_midia=getattr(vet, "preferencia_midia", None),
        )
        rec_secundario = rec.get("secundario")
        rec_observacoes = rec.get("observacoes") or []
        sec_id = rec["secundario"]["id"] if rec.get("secundario") else None
        produtos_cmp = produtos_comparacao(
            rec["produto_id"],
            emite_como=vet.emite_como or "pf",
            secundario_id=sec_id,
            tem_cnpj=_cnpj_informado(vet.cnpj),
        )

    cert_escolhida = bool(vet.certificadora_escolhida)
    cert_key = vet.certificadora_escolhida if cert_escolhida else None
    tipo_arm = tipo_certificado_efetivo(vet)
    if vet.tipo_certificado != tipo_arm:
        vet.tipo_certificado = tipo_arm
        db.session.commit()
    guia = None
    cert_info = {}
    impl_passos = []
    if cert_escolhida:
        guia = guia_certificadora(cert_key, tipo_arm, produto.categoria if produto else "pf")
        cert_info = CERTIFICADORAS.get(cert_key, {})
        impl_passos = guia_implementar_certificado(
            profissao, tipo_arm, vet.sistema_receituario or ""
        )
    leg = legislacao_por_profissao(profissao)
    precos = vet.precos_lista()
    produto_atual = produto_id_efetivo(vet)
    precos_produto_id = precos[0].get("produto_id") if precos else None
    precos_desatualizados = bool(precos and precos_produto_id and precos_produto_id != produto_atual)
    if precos_desatualizados or not precos:
        precos = _garantir_precos_catalogo(vet)
    melhor = vet.melhor_preco() if precos else None
    filtro_precos = filtros_de_vet(vet)
    catalogo = info_catalogo()

    return render_template(
        "public/jornada.html",
        vet=vet,
        produto=produto,
        produtos=produtos_cmp,
        produto_atual=produto_atual,
        rec_observacoes=rec_observacoes,
        precos_desatualizados=precos_desatualizados,
        profissao=profissao,
        profissao_info=PROFISSOES.get(profissao, PROFISSOES["outro"]),
        rec_secundario=rec_secundario,
        precos=precos,
        melhor=melhor,
        guia=guia,
        legislacao=leg,
        impl_passos=impl_passos,
        cert_key=cert_key,
        cert_escolhida=cert_escolhida,
        cert_info=cert_info,
        tipo_arm=tipo_arm,
        etapas=ETAPAS_USUARIO,
        certificadoras=certificadoras_ativas(),
        playwright_ok=playwright_disponivel(),
        precos_ok=request.args.get("precos_ok") == "1",
        filtro_precos=filtro_precos,
        catalogo=catalogo,
    )


@app.route("/p/<protocolo>/preferencias", methods=["POST"])
def atualizar_preferencias_publico(protocolo):
    vet = Veterinario.query.filter_by(protocolo=protocolo.upper()).first_or_404()
    tipo_arm = tipo_certificado_efetivo(vet)
    prefs = parse_preferencias_form(request.form, tipo_arm=tipo_arm)
    vet.preferencia_midia = prefs["preferencia_midia"]
    vet.preferencia_emissao = prefs["preferencia_emissao"]
    vet.preferencia_validade_anos = prefs["preferencia_validade_anos"]
    vet.precos_json = None
    db.session.commit()
    _garantir_precos_catalogo(vet)
    flash("Preferências atualizadas. Preços recalculados.", "success")
    return redirect(url_for("jornada", protocolo=protocolo, precos_ok=1))


@app.route("/p/<protocolo>/certificadora", methods=["POST"])
def escolher_certificadora(protocolo):
    vet = Veterinario.query.filter_by(protocolo=protocolo.upper()).first_or_404()
    nova = request.form.get("certificadora", "").strip()
    if nova in certificadoras_ativas():
        vet.certificadora_escolhida = nova
        vet.certificadora = nova
        if vet.etapa_usuario in ("recomendacao", "precos", None, ""):
            vet.etapa_usuario = "compra"
        db.session.commit()
        flash(
            f"Certificadora definida: {CERTIFICADORAS[nova]['nome']}. "
            "Veja abaixo o passo a passo personalizado.",
            "success",
        )
    return redirect(url_for("jornada", protocolo=protocolo))


@app.route("/p/<protocolo>/guia-implementacao")
def download_guia(protocolo):
    vet = Veterinario.query.filter_by(protocolo=protocolo.upper()).first_or_404()
    if not vet.certificadora_escolhida:
        flash("Escolha uma certificadora antes de baixar o guia personalizado.", "warning")
        return redirect(url_for("jornada", protocolo=protocolo))
    cert_key = vet.certificadora_escolhida
    cert_nome = CERTIFICADORAS.get(cert_key, {}).get("nome", cert_key)
    html = gerar_html_guia(vet, vet.produto_info(), cert_nome)
    return send_file(
        io.BytesIO(html.encode("utf-8")),
        mimetype="text/html; charset=utf-8",
        as_attachment=True,
        download_name=f"guia_implementacao_{vet.protocolo}.html",
    )


@app.route("/p/<protocolo>/produto", methods=["POST"])
def alterar_produto_publico(protocolo):
    vet = Veterinario.query.filter_by(protocolo=protocolo.upper()).first_or_404()
    pid = request.form.get("produto_id", "").strip()
    if pid not in PRODUTOS:
        flash("Tipo de certificado inválido.", "error")
        return redirect(url_for("jornada", protocolo=protocolo))

    produto = PRODUTOS[pid]
    vet.produto_recomendado = pid
    vet.tipo_certificado = produto["tipo_armazenamento"]
    from catalogo_precos import ajustar_preferencias_vet

    ajustar_preferencias_vet(vet)
    vet.precos_json = None
    db.session.commit()
    _garantir_precos_catalogo(vet)
    return redirect(url_for("jornada", protocolo=protocolo, precos_ok=1))


@app.route("/p/<protocolo>/atualizar-precos")
def atualizar_precos_publico(protocolo):
    vet = Veterinario.query.filter_by(protocolo=protocolo.upper()).first_or_404()
    if not vet.produto_recomendado:
        flash("Produto não definido.", "error")
        return redirect(url_for("jornada", protocolo=protocolo))

    ajax = request.args.get("ajax")
    if ajax == "status":
        cat = info_catalogo()
        precos = vet.precos_lista()
        tem_ok = any(p.get("ok") for p in precos)
        if tem_ok and not cat.get("varredura_em_andamento"):
            return jsonify(ok=True, redirect=_redirect_jornada_precos(protocolo))
        if cat.get("varredura_em_andamento"):
            return jsonify(ok=False, pending=True, catalogo=cat)
        _garantir_precos_catalogo(vet, forcar_varredura=True)
        precos = vet.precos_lista()
        if any(p.get("ok") for p in precos):
            return jsonify(ok=True, redirect=_redirect_jornada_precos(protocolo))
        return jsonify(ok=False, pending=True, catalogo=info_catalogo())

    if ajax == "1":
        _garantir_precos_catalogo(vet, forcar_varredura=True)
        return jsonify(ok=False, pending=True, started=True)

    precos = _garantir_precos_catalogo(vet, forcar_varredura=request.args.get("forcar") == "1")
    if any(p.get("ok") for p in precos):
        flash("Preços atualizados a partir do catálogo.", "success")
    elif info_catalogo().get("varredura_em_andamento"):
        flash("Catálogo em atualização. Os valores aparecerão em alguns minutos.", "warning")
    else:
        flash("Nenhum preço encontrado para esta combinação. Varredura iniciada.", "warning")
    return redirect(url_for("jornada", protocolo=protocolo, precos_ok=1))


@app.route("/p/<protocolo>/etapa", methods=["POST"])
def atualizar_etapa_publico(protocolo):
    vet = Veterinario.query.filter_by(protocolo=protocolo.upper()).first_or_404()
    nova = request.form.get("etapa_usuario", vet.etapa_usuario)
    keys = [e[0] for e in ETAPAS_USUARIO]
    if nova in keys:
        if not vet.certificadora_escolhida and keys.index(nova) > keys.index("precos"):
            flash("Escolha uma certificadora antes de avançar para as próximas etapas.", "warning")
        else:
            vet.etapa_usuario = nova
            db.session.commit()
            flash("Progresso atualizado.", "success")
    return redirect(url_for("jornada", protocolo=protocolo))


@app.route("/p/<protocolo>/doar", methods=["GET", "POST"])
def doar(protocolo):
    vet = Veterinario.query.filter_by(protocolo=protocolo.upper()).first_or_404()
    valor = None
    payload = None
    qr_b64 = None

    if not PIX_CHAVE:
        flash("Pix de doação ainda não configurado no servidor.", "warning")

    if request.method == "POST" and PIX_CHAVE:
        raw = request.form.get("valor", "").strip().replace(",", ".")
        try:
            valor = float(raw) if raw else None
        except ValueError:
            valor = None
        if valor is not None and valor <= 0:
            valor = None

        payload = gerar_pix_copia_cola(
            PIX_CHAVE,
            PIX_NOME,
            PIX_CIDADE,
            valor=valor,
            txid=f"DOACAO{vet.protocolo}",
        )
        qr_b64 = qr_code_base64(payload)

    return render_template(
        "public/doar.html",
        vet=vet,
        pix_chave=PIX_CHAVE,
        pix_nome=PIX_NOME,
        valor=valor,
        payload=payload,
        qr_b64=qr_b64,
    )


# ── Auth admin ────────────────────────────────────────────────────────────────


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin"):
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        if request.form.get("senha") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin.dashboard"))
        flash("Senha incorreta.", "error")
    return render_template("login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin.login"))


# ── Dashboard ─────────────────────────────────────────────────────────────────


@admin_bp.route("/guia")
@admin_required
def guia():
    return render_template(
        "guia.html",
        certificadoras=certificadoras_ativas(),
        tipos_certificado=TIPOS_CERTIFICADO,
        tipos_nao_usar=TIPOS_NAO_USAR,
    )


@admin_bp.route("/catalogo")
@admin_required
def catalogo_admin():
    cat = info_catalogo()
    amostra = (
        PrecoCatalogo.query.order_by(PrecoCatalogo.atualizado_em.desc())
        .limit(50)
        .all()
    )
    return render_template(
        "catalogo.html",
        catalogo=cat,
        amostra=amostra,
        certificadoras=certificadoras_ativas(),
    )


@admin_bp.route("/catalogo/varredura", methods=["POST"])
@admin_required
def catalogo_varredura_admin():
    if iniciar_varredura_background(app):
        flash("Varredura de preços iniciada em background.", "success")
    else:
        flash("Já existe uma varredura em andamento.", "warning")
    return redirect(url_for("admin.catalogo_admin"))


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    total = Veterinario.query.count()
    em_processo = Veterinario.query.filter(
        Veterinario.status_certificado.in_([
            "orientado", "pedido_certificadora", "validacao", "certificado_emitido", "instalado"
        ])
    ).count()
    concluidos = Veterinario.query.filter_by(status_certificado="concluido").count()
    recentes = Veterinario.query.order_by(Veterinario.criado_em.desc()).limit(10).all()
    pendentes_acao = Veterinario.query.filter_by(status_certificado="cadastrado").order_by(Veterinario.criado_em).all()

    return render_template(
        "dashboard.html",
        total=total,
        em_processo=em_processo,
        concluidos=concluidos,
        recentes=recentes,
        pendentes_acao=pendentes_acao,
        etapas=ETAPAS_CERTIFICADO,
    )


# ── Cadastro interno ──────────────────────────────────────────────────────────

@admin_bp.route("/cadastrar", methods=["GET", "POST"])
@admin_required
def cadastrar():
    if request.method == "POST":
        tipo = request.form.get("tipo_certificado", "A1")
        inclui_receituario = request.form.get("solicita_receituario") == "on"
        codigo = request.form.get("codigo_desconto", "").strip() or None

        vet = Veterinario(
            protocolo=Veterinario.gerar_protocolo(),
            nome_completo=request.form["nome_completo"].strip(),
            cpf=request.form["cpf"].strip(),
            rg=request.form.get("rg", "").strip() or None,
            data_nascimento=parse_date(request.form.get("data_nascimento")),
            crmv=request.form["crmv"].strip(),
            crmv_uf=request.form["crmv_uf"].upper(),
            email=request.form["email"].strip().lower(),
            telefone=request.form["telefone"].strip(),
            whatsapp=request.form.get("whatsapp", request.form["telefone"]).strip(),
            cep=request.form["cep"].strip(),
            logradouro=request.form["logradouro"].strip(),
            numero=request.form["numero"].strip(),
            complemento=request.form.get("complemento", "").strip() or None,
            bairro=request.form["bairro"].strip(),
            cidade=request.form["cidade"].strip(),
            uf=request.form["uf"].upper(),
            tipo_certificado=tipo,
            solicita_receituario=inclui_receituario,
            codigo_desconto=codigo,
            certificadora=request.form.get("certificadora", CERTIFICADORA_PADRAO),
            observacoes=request.form.get("observacoes", "").strip() or None,
            status_certificado="cadastrado",
            status_receituario="pesquisando" if inclui_receituario else "nao_solicitado",
        )

        db.session.add(vet)
        db.session.commit()
        flash(f"Veterinário {vet.nome_completo} cadastrado — protocolo {vet.protocolo}", "success")
        return redirect(url_for("admin.detalhe", id=vet.id))

    return render_template(
        "cadastrar.html",
        estados=ESTADOS_BR,
        certificadoras=certificadoras_ativas(),
        certificadora_padrao=CERTIFICADORA_PADRAO,
        tipos_certificado=TIPOS_CERTIFICADO,
        tipos_nao_usar=TIPOS_NAO_USAR,
    )


# ── Lista e detalhe ───────────────────────────────────────────────────────────

@admin_bp.route("/veterinarios")
@admin_required
def lista():
    status_filtro = request.args.get("status", "")
    busca = request.args.get("q", "").strip()

    query = Veterinario.query
    if status_filtro:
        query = query.filter_by(status_certificado=status_filtro)
    if busca:
        query = query.filter(
            db.or_(
                Veterinario.nome_completo.ilike(f"%{busca}%"),
                Veterinario.protocolo.ilike(f"%{busca}%"),
                Veterinario.crmv.ilike(f"%{busca}%"),
                Veterinario.cpf.ilike(f"%{busca}%"),
            )
        )

    veterinarios = query.order_by(Veterinario.criado_em.desc()).all()
    return render_template(
        "lista.html",
        veterinarios=veterinarios,
        etapas=ETAPAS_CERTIFICADO,
        status_filtro=status_filtro,
        busca=busca,
    )


@admin_bp.route("/veterinario/<int:id>")
@admin_required
def detalhe(id):
    vet = Veterinario.query.get_or_404(id)
    vals = vet.valores_referencia()
    tipo_info = info_tipo(vet.tipo_certificado)
    return render_template(
        "detalhe.html",
        vet=vet,
        etapas=ETAPAS_CERTIFICADO,
        etapas_receituario=ETAPAS_RECEITUARIO,
        certificadoras=certificadoras_ativas(),
        tipos_certificado=TIPOS_CERTIFICADO,
        tipos_nao_usar=TIPOS_NAO_USAR,
        tipo_info=tipo_info,
        valores=vals,
        dados_cert=dados_para_certificadora(vet),
        texto_pedido=texto_pedido_certificadora(vet),
        url_cert=url_certificadora(vet.certificadora or CERTIFICADORA_PADRAO, vet.tipo_certificado),
        playwright_ok=playwright_disponivel(),
    )


@admin_bp.route("/veterinario/<int:id>/comparar-precos")
@admin_required
def comparar_precos_vet(id):
    vet = Veterinario.query.get_or_404(id)
    produto_id = request.args.get("produto") or produto_id_efetivo(vet)
    if produto_id not in PRODUTOS:
        produto_id = produto_id_efetivo(vet)

    atualizar = request.args.get("atualizar") == "1"
    produto = PRODUTOS[produto_id]

    if not playwright_disponivel():
        flash("Playwright não instalado. Rode: pip install playwright && playwright install chromium", "error")
        return redirect(url_for("admin.detalhe", id=id))

    flash(f"Buscando preços de {produto['nome']} nos sites… pode levar até 3 minutos.", "success")
    resultados = comparar_precos(produto_id, usar_cache=not atualizar)
    melhor = next((r for r in resultados if r.get("melhor_preco")), None)

    return render_template(
        "comparar_precos.html",
        vet=vet,
        produto_id=produto_id,
        produto=produto,
        produtos=PRODUTOS,
        resultados=resultados,
        melhor=melhor,
    )


# ── Ações ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/veterinario/<int:id>/certificadora", methods=["POST"])
@admin_required
def alterar_certificadora(id):
    vet = Veterinario.query.get_or_404(id)
    nova = request.form.get("certificadora", "").strip()
    if nova in certificadoras_ativas():
        vet.certificadora = nova
        db.session.commit()
        nome = CERTIFICADORAS[nova]["nome"]
        flash(f"Certificadora alterada para {nome}.", "success")
    else:
        flash("Certificadora inválida.", "error")
    return redirect(url_for("admin.detalhe", id=id))


@admin_bp.route("/veterinario/<int:id>/orientar", methods=["POST"])
@admin_required
def orientar(id):
    vet = Veterinario.query.get_or_404(id)
    vet.status_certificado = "orientado"
    db.session.commit()
    flash("Marcado como orientado.", "success")
    return redirect(url_for("admin.detalhe", id=id))


@admin_bp.route("/veterinario/<int:id>/solicitar-certificado", methods=["POST"])
@admin_required
def solicitar_certificado(id):
    """Registra pedido na certificadora e avança etapa."""
    vet = Veterinario.query.get_or_404(id)
    vet.certificadora = request.form.get("certificadora", vet.certificadora or CERTIFICADORA_PADRAO)
    vet.numero_pedido_certificadora = request.form.get("numero_pedido", "").strip() or None
    vet.data_pedido_certificadora = datetime.utcnow()
    vet.status_certificado = "pedido_certificadora"
    db.session.commit()
    flash("Pedido registrado na certificadora.", "success")
    return redirect(url_for("admin.detalhe", id=id))


@admin_bp.route("/veterinario/<int:id>/avancar-etapa", methods=["POST"])
@admin_required
def avancar_etapa(id):
    vet = Veterinario.query.get_or_404(id)
    proxima = vet.proxima_etapa()
    if proxima:
        vet.status_certificado = proxima
        if proxima == "certificado_emitido":
            vet.data_emissao = datetime.utcnow()
        db.session.commit()
        flash(f"Etapa avançada para: {proxima}", "success")
    return redirect(url_for("admin.detalhe", id=id))


@admin_bp.route("/veterinario/<int:id>/atualizar", methods=["POST"])
@admin_required
def atualizar(id):
    vet = Veterinario.query.get_or_404(id)
    vet.status_certificado = request.form.get("status_certificado", vet.status_certificado)
    vet.status_receituario = request.form.get("status_receituario", vet.status_receituario)
    vet.numero_pedido_certificadora = request.form.get("numero_pedido_certificadora") or vet.numero_pedido_certificadora
    vet.certificadora = request.form.get("certificadora") or vet.certificadora
    vet.codigo_desconto = request.form.get("codigo_desconto") or vet.codigo_desconto
    vet.data_validade = parse_date(request.form.get("data_validade"))
    vet.observacoes = request.form.get("observacoes", vet.observacoes)
    db.session.commit()
    flash("Dados atualizados.", "success")
    return redirect(url_for("admin.detalhe", id=id))


@admin_bp.route("/api/veterinario/<int:id>/dados-certificadora")
@admin_required
def api_dados_certificadora(id):
    vet = Veterinario.query.get_or_404(id)
    return jsonify({
        "texto": texto_pedido_certificadora(vet),
        "dados": dados_para_certificadora(vet),
        "url": url_certificadora(vet.certificadora or CERTIFICADORA_PADRAO, vet.tipo_certificado),
    })


@admin_bp.route("/veterinario/<int:id>/whatsapp-orientacao")
@admin_required
def whatsapp_orientacao(id):
    import urllib.parse
    vet = Veterinario.query.get_or_404(id)
    tel = "".join(c for c in vet.whatsapp if c.isdigit())
    if not tel.startswith("55"):
        tel = "55" + tel
    msg = texto_whatsapp_orientacao(vet)
    return redirect(f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}")


# ── Exportação ────────────────────────────────────────────────────────────────

@admin_bp.route("/exportar")
@admin_required
def exportar():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Protocolo", "Nome", "CPF", "RG", "CRMV", "E-mail", "WhatsApp",
        "Cidade", "UF", "Tipo Cert.", "Certificadora", "Nº Pedido",
        "Status Cert.", "Status Receituário", "Código Desconto", "Observações", "Cadastro",
    ])
    for v in Veterinario.query.order_by(Veterinario.criado_em.desc()).all():
        writer.writerow([
            v.protocolo, v.nome_completo, v.cpf, v.rg or "", f"{v.crmv}-{v.crmv_uf}",
            v.email, v.whatsapp, v.cidade, v.uf, v.tipo_certificado,
            v.certificadora or "", v.numero_pedido_certificadora or "",
            v.status_certificado, v.status_receituario,
            v.codigo_desconto or "", v.observacoes or "", v.criado_em.strftime("%d/%m/%Y %H:%M"),
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"clientes_{datetime.now().strftime('%Y%m%d')}.csv",
    )


app.register_blueprint(admin_bp)


# ── Redirecionamentos legados (URLs antigas do admin) ─────────────────────────

@app.route("/login")
def legacy_login():
    return redirect(url_for("admin.login"))


@app.route("/logout")
def legacy_logout():
    return redirect(url_for("admin.logout"))


@app.route("/dashboard")
def legacy_dashboard():
    return redirect(url_for("admin.dashboard"))


@app.route("/guia")
def legacy_guia():
    return redirect(url_for("admin.guia"))


@app.route("/cadastrar")
def legacy_cadastrar():
    return redirect(url_for("admin.cadastrar"))


@app.route("/veterinarios")
def legacy_lista():
    return redirect(url_for("admin.lista"))


@app.route("/exportar")
def legacy_exportar():
    return redirect(url_for("admin.exportar"))


@app.route("/veterinario/<int:id>")
def legacy_detalhe(id):
    return redirect(url_for("admin.detalhe", id=id))


@app.route("/veterinario/<int:id>/comparar-precos")
def legacy_comparar(id):
    return redirect(url_for("admin.comparar_precos_vet", id=id))


if __name__ == "__main__":
    # use_reloader=False evita reinício no meio de buscas Playwright (que quebravam o POST /comecar)
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
