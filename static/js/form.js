function maskCPF(value) {
    return value.replace(/\D/g, "")
        .replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}

function maskPhone(value) {
    value = value.replace(/\D/g, "");
    if (value.length <= 10) return value.replace(/(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3").trim();
    return value.replace(/(\d{2})(\d{5})(\d{0,4})/, "($1) $2-$3").trim();
}

function maskCEP(value) {
    return value.replace(/\D/g, "").replace(/(\d{5})(\d{0,3})/, "$1-$2");
}

async function buscarCEP(cep) {
    const digits = cep.replace(/\D/g, "");
    if (digits.length !== 8) return;
    try {
        const res = await fetch(`https://viacep.com.br/ws/${digits}/json/`);
        const data = await res.json();
        if (data.erro) return;
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ""; };
        set("logradouro", data.logradouro);
        set("bairro", data.bairro);
        set("cidade", data.localidade);
        set("uf", data.uf);
    } catch (_) {}
}

document.addEventListener("DOMContentLoaded", () => {
    const cpf = document.getElementById("cpf");
    const telefone = document.getElementById("telefone");
    const whatsapp = document.getElementById("whatsapp");
    const cep = document.getElementById("cep");
    const receituario = document.getElementById("solicita_receituario");

    if (cpf) cpf.addEventListener("input", e => { e.target.value = maskCPF(e.target.value); });
    if (telefone) telefone.addEventListener("input", e => { e.target.value = maskPhone(e.target.value); });
    if (whatsapp) whatsapp.addEventListener("input", e => { e.target.value = maskPhone(e.target.value); });
    if (cep) {
        cep.addEventListener("input", e => { e.target.value = maskCEP(e.target.value); });
        cep.addEventListener("blur", e => buscarCEP(e.target.value));
    }
});
