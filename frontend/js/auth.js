"use strict";

const form = document.querySelector("#auth-form");
const message = document.querySelector("#form-message");
const submit = form.querySelector("[type=submit]");
const originalLabel = submit.innerHTML;

function showMessage(text, success = false) {
  message.textContent = text;
  message.classList.add("visible");
  message.classList.toggle("success", success);
}

document.querySelector(".toggle-password").addEventListener("click", (event) => {
  const input = document.querySelector("#password");
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  event.currentTarget.textContent = show ? "Ocultar" : "Ver";
  event.currentTarget.setAttribute("aria-label", show ? "Ocultar contraseña" : "Mostrar contraseña");
});

fetch("/api/auth/sesion").then((response) => {
  if (response.ok) window.location.replace("/dashboard");
}).catch(() => {});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.classList.remove("visible", "success");
  if (!form.reportValidity()) return;

  const values = Object.fromEntries(new FormData(form).entries());
  values.autoriza_datos = Boolean(form.querySelector('[name="autoriza_datos"]')?.checked);
  if (form.dataset.mode === "register" && values.password.length < 10) {
    showMessage("La contraseña debe tener al menos 10 caracteres.");
    return;
  }

  submit.disabled = true;
  submit.textContent = form.dataset.mode === "register" ? "Creando cuenta…" : "Ingresando…";
  try {
    const endpoint = form.dataset.mode === "register" ? "/api/auth/registro" : "/api/auth/login";
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "No se pudo completar la solicitud.");
    window.location.assign("/dashboard");
  } catch (error) {
    showMessage(error.message || "No se pudo conectar con el servidor.");
    submit.disabled = false;
    submit.innerHTML = originalLabel;
  }
});
