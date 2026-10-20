"use strict";
const form = document.querySelector("#contact-form");
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const data = new FormData(form);
  const subject = encodeURIComponent("Solicitud desde ObraPresupuesto");
  const body = encodeURIComponent(`Nombre: ${data.get("nombre") || "No indicado"}\nCorreo: ${data.get("email")}\n\n${data.get("mensaje")}\n\nAutorizo el tratamiento de estos datos para atender esta solicitud.`);
  window.location.href = `mailto:joral2112@hotmail.com?subject=${subject}&body=${body}`;
  const status = document.querySelector("#contact-message-status");
  status.textContent = "Se abrió tu aplicación de correo con el mensaje preparado. Revísalo y envíalo para completar la solicitud.";
  status.classList.add("visible", "success");
});
