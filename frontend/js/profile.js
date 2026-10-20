"use strict";

const form = document.querySelector("#profile-form");
const message = document.querySelector("#profile-message");
const submit = form.querySelector("[type=submit]");
const roleNames = { arquitecto: "Arquitecto", ingeniero: "Ingeniero", cliente: "Cliente" };

function notify(text, success = false) {
  message.textContent = text;
  message.classList.add("visible");
  message.classList.toggle("success", success);
}

async function loadProfile() {
  const response = await fetch("/api/auth/sesion");
  if (response.status === 401) return window.location.replace("/login");
  if (!response.ok) throw new Error("No se pudo cargar el perfil.");
  const user = await response.json();
  form.elements.nombre_completo.value = user.nombre_completo;
  form.elements.email.value = user.email;
  document.querySelector("#profile-role").textContent = `TIPO DE CUENTA · ${roleNames[user.rol] || user.rol.toUpperCase()}`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.classList.remove("visible", "success");
  if (!form.reportValidity()) return;
  const data = Object.fromEntries(new FormData(form).entries());
  const confirmation = document.querySelector("#confirm-password").value;
  if (data.new_password && data.new_password !== confirmation) {
    notify("Las nuevas contraseñas no coinciden.");
    return;
  }
  submit.disabled = true;
  submit.textContent = "Guardando…";
  try {
    const response = await fetch("/api/auth/perfil", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "No se pudieron guardar los cambios.");
    form.elements.current_password.value = "";
    form.elements.new_password.value = "";
    document.querySelector("#confirm-password").value = "";
    notify("Tus datos se actualizaron correctamente.", true);
  } catch (error) {
    notify(error.message || "No se pudo conectar con el servidor.");
  } finally {
    submit.disabled = false;
    submit.innerHTML = "Guardar cambios <span>→</span>";
  }
});

loadProfile().catch((error) => notify(error.message));
