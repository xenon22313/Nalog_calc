// Generic calculator client: collects form values, posts them to /api/calc/<slug>
// and fills elements marked with data-result="<key>".
(function () {
  "use strict";

  const DEBOUNCE_MS = 400;
  const moneyFormat = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const numberFormat = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 });

  function collect(form) {
    const data = {};
    for (const el of form.elements) {
      if (!el.name) continue;
      if (el.type === "checkbox") {
        data[el.name] = el.checked;
        continue;
      }
      const value = el.value.replace(/[\s\u00a0]/g, "").replace(",", ".");
      if (value !== "") data[el.name] = value;
    }
    return data;
  }

  function format(value, kind) {
    if (value === null || value === undefined) return "—";
    if (kind === "money") return moneyFormat.format(value) + "\u00a0₽";
    if (kind === "percent") return numberFormat.format(value) + "%";
    return String(value);
  }

  function clearErrors(form) {
    form.querySelector(".calc-error").hidden = true;
    for (const el of form.querySelectorAll(".is-invalid")) el.classList.remove("is-invalid");
  }

  function showError(form, message, fields) {
    const box = form.querySelector(".calc-error");
    box.textContent = message;
    box.hidden = false;
    for (const [name, text] of Object.entries(fields || {})) {
      const input = form.elements[name];
      if (!input) continue;
      input.classList.add("is-invalid");
      const feedback = input.parentElement.querySelector(".invalid-feedback");
      if (feedback) feedback.textContent = text;
    }
  }

  function render(results, data) {
    for (const el of results.querySelectorAll("[data-result]")) {
      el.textContent = format(data[el.dataset.result], el.dataset.format);
    }
    for (const el of results.querySelectorAll("[data-show-if]")) {
      el.hidden = !data[el.dataset.showIf];
    }
    results.hidden = false;
  }

  function setup(form) {
    const results = document.getElementById(form.dataset.results);
    const autoToggle = form.querySelector("[data-auto-toggle]");
    let controller = null;
    let timer = null;

    async function calculate() {
      if (controller) controller.abort();
      controller = new AbortController();
      clearErrors(form);
      results.classList.add("is-loading");

      try {
        const response = await fetch("/api/calc/" + form.dataset.slug, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(collect(form)),
          signal: controller.signal,
        });
        const body = await response.json().catch(() => ({}));

        if (response.ok) {
          render(results, body.result);
          return;
        }
        results.hidden = true;
        if (response.status === 429) {
          showError(form, "Слишком много запросов. Подождите минуту и попробуйте снова.");
        } else {
          showError(form, body.error || "Не удалось выполнить расчёт.", body.fields);
        }
      } catch (err) {
        if (err.name === "AbortError") return;
        results.hidden = true;
        showError(form, "Сервер недоступен. Проверьте подключение к интернету и попробуйте ещё раз.");
      } finally {
        results.classList.remove("is-loading");
      }
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      clearTimeout(timer);
      calculate();
    });

    form.addEventListener("input", (event) => {
      if (event.target === autoToggle || !autoToggle || !autoToggle.checked) return;
      clearTimeout(timer);
      timer = setTimeout(calculate, DEBOUNCE_MS);
    });
  }

  document.querySelectorAll("form.calc-form").forEach(setup);
})();
