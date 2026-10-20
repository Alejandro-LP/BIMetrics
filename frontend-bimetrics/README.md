# BIMetrics Frontend

SPA de BIMetrics construida con React, Vite, Tailwind CSS, Framer Motion y lucide-react.

## Estructura de `src`

- `app/`: router y composición global.
- `components/brand/`: logo reutilizable de BIMetrics.
- `components/layout/`: layouts público y autenticado.
- `components/ui/`: elementos visuales compartidos, como GlassCard.
- `features/auth/`: login, registro y estado de sesión.
- `features/dashboard/`: métricas, proyectos, presupuestos, catálogo y actividad BIM.
- `features/profile/`: gestión del perfil.
- `features/public/`: landing, contacto y contenido legal.
- `services/`: cliente HTTP para la API Flask.
- `styles/`: Tailwind y estilos globales.

## Desarrollo

Desde esta carpeta, ejecuta `npm install` una vez y luego `npm run dev`. La API Flask se inicia aparte desde `backend/` y escucha en `http://localhost:5000`. En desarrollo, el navegador llama a `/api` y Vite reenvía esas peticiones a Flask.

Para desarrollo, cambia `VITE_API_PROXY_TARGET` si Flask usa otro host o puerto. Para compilar y desplegar, define `VITE_API_URL` con la URL completa del API, incluido `/api` (por ejemplo `https://api.bimetrics.co/api`). Configura `CORS_ORIGIN` en Flask con el origen web desplegado.
