(function () {
    const form = document.getElementById("wizard-form");
    if (!form) return;

    const cfg = window.CERTIGUIA_WIZARD || {};
    const panels = Array.from(form.querySelectorAll(".wizard-panel"));
    const btnPrev = document.getElementById("wizard-prev");
    const btnNext = document.getElementById("wizard-next");
    const btnSubmit = document.getElementById("wizard-submit");
    const progressBar = document.getElementById("wizard-progress-bar");
    const stepLabel = document.getElementById("wizard-step-label");
    const variosHidden = document.getElementById("varios_computadores_hidden");
    const cnpjWrap = document.getElementById("cnpj-wizard-wrap");
    const cnpjInput = document.getElementById("cnpj_input");
    const cnpjHidden = document.getElementById("cnpj");

    let stepIndex = 0;

    function ondeUsar() {
        return form.querySelector('input[name="onde_usar"]:checked')?.value || "pc_unico";
    }

    function emiteComo() {
        return form.querySelector('input[name="emite_como"]:checked')?.value || "pf";
    }

    function panelAtivo() {
        return panels.filter((p) => p.style.display !== "none")[stepIndex];
    }

    function paineisVisiveis() {
        return panels.filter((p) => {
            const skip = p.dataset.skipUnless;
            if (!skip) return true;
            const [campo, valor] = skip.split(":");
            if (campo === "onde") return ondeUsar() === valor;
            return true;
        });
    }

    function syncMidiaOculta() {
        const onde = ondeUsar();
        const varios = onde === "varios_pc";
        if (variosHidden) variosHidden.value = varios ? "sim" : "nao";

        let midia = form.querySelector('input[name="preferencia_midia"]:checked')?.value;
        if (onde === "celular") {
            midia = midia || "nuvem";
        } else if (onde === "pc_unico") {
            midia = "arquivo";
        } else if (onde === "varios_pc") {
            midia = "token";
        }

        let hidden = form.querySelector('input[type="hidden"][name="preferencia_midia"]');
        if (hidden) hidden.remove();

        if (onde !== "celular") {
            hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = "preferencia_midia";
            form.appendChild(hidden);
            hidden.value = midia;
        }
    }

    function syncCnpj() {
        const precisa = emiteComo() === "pj" || emiteComo() === "ambos";
        if (cnpjWrap) cnpjWrap.hidden = !precisa;
        if (cnpjInput) cnpjInput.required = precisa;
        if (!precisa && cnpjHidden) cnpjHidden.value = "";
        else if (cnpjHidden && cnpjInput) cnpjHidden.value = cnpjInput.value;
    }

    function maskCNPJ(value) {
        return value
            .replace(/\D/g, "")
            .replace(/^(\d{2})(\d)/, "$1.$2")
            .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
            .replace(/\.(\d{3})(\d)/, ".$1/$2")
            .replace(/(\d{4})(\d)/, "$1-$2")
            .slice(0, 18);
    }

    function validarPainel(panel) {
        const sel = panel.dataset.required;
        if (!sel) return form.checkValidity();

        const alvo = panel.querySelector(sel);
        if (!alvo) return true;

        if (alvo.type === "radio") {
            const nome = alvo.name;
            return !!panel.querySelector(`input[name="${nome}"]:checked`);
        }
        return alvo.checkValidity();
    }

    function atualizarUI() {
        const visiveis = paineisVisiveis();
        if (stepIndex >= visiveis.length) stepIndex = visiveis.length - 1;
        if (stepIndex < 0) stepIndex = 0;

        panels.forEach((p) => {
            p.classList.remove("active");
            p.style.display = "none";
        });

        visiveis.forEach((p, i) => {
            if (i === stepIndex) {
                p.style.display = "";
                p.classList.add("active");
            }
        });

        const total = visiveis.length;
        const pct = total <= 1 ? 100 : ((stepIndex + 1) / total) * 100;
        if (progressBar) progressBar.style.width = pct + "%";
        if (stepLabel) stepLabel.textContent = `Passo ${stepIndex + 1} de ${total}`;

        const ultimo = stepIndex === total - 1;
        if (btnPrev) btnPrev.disabled = stepIndex === 0;
        if (btnNext) btnNext.hidden = ultimo;
        if (btnSubmit) btnSubmit.hidden = !ultimo;

        syncMidiaOculta();
        syncCnpj();

        document.querySelectorAll(".wizard-opcao").forEach((el) => {
            el.classList.toggle("is-selected", !!el.querySelector("input:checked"));
        });
    }

    function avancar() {
        const visiveis = paineisVisiveis();
        const panel = visiveis[stepIndex];
        if (!validarPainel(panel)) {
            form.reportValidity();
            return;
        }
        if (panel?.dataset.step === "titular" && !validarTitularCnpj()) {
            return;
        }
        if (stepIndex < visiveis.length - 1) {
            stepIndex += 1;
            atualizarUI();
            panelAtivo()?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    function validarTitularCnpj() {
        const precisa = emiteComo() === "pj" || emiteComo() === "ambos";
        if (!precisa) return true;
        const digits = (cnpjInput?.value || "").replace(/\D/g, "");
        if (digits.length === 14) {
            if (cnpjHidden) cnpjHidden.value = cnpjInput.value;
            return true;
        }
        cnpjInput?.focus();
        return false;
    }

    function voltar() {
        if (stepIndex > 0) {
            stepIndex -= 1;
            atualizarUI();
            panelAtivo()?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    form.querySelectorAll('input[name="onde_usar"]').forEach((r) => {
        r.addEventListener("change", () => {
            const visiveisAntes = paineisVisiveis().length;
            atualizarUI();
            const visiveisDepois = paineisVisiveis().length;
            if (visiveisAntes !== visiveisDepois && ondeUsar() !== "celular") {
                /* permanece no passo atual */
            }
        });
    });

    form.querySelectorAll('input[name="emite_como"]').forEach((r) => {
        r.addEventListener("change", syncCnpj);
    });

    form.querySelectorAll(".wizard-opcao input").forEach((inp) => {
        inp.addEventListener("change", () => {
            document.querySelectorAll(".wizard-opcao").forEach((el) => {
                el.classList.toggle("is-selected", !!el.querySelector("input:checked"));
            });
        });
    });

    if (cnpjInput) {
        cnpjInput.addEventListener("input", (e) => {
            e.target.value = maskCNPJ(e.target.value);
            if (cnpjHidden) cnpjHidden.value = e.target.value;
        });
    }

    if (btnNext) btnNext.addEventListener("click", avancar);
    if (btnPrev) btnPrev.addEventListener("click", voltar);

    form.addEventListener("submit", () => {
        syncMidiaOculta();
        syncCnpj();
        if (btnSubmit) {
            btnSubmit.disabled = true;
            btnSubmit.textContent = "Montando sua recomendação…";
        }
    });

    /* Esconder painéis não visíveis no fluxo */
    panels.forEach((p) => {
        if (p.dataset.skipUnless) p.style.display = "none";
    });
    panels[0].style.display = "";

    syncCnpj();
    atualizarUI();
})();
