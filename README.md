# Scripta Scientia Editorial API

MVP para consultar el estado editorial de Scripta Scientia desde OJS 3.4.

## Endpoints iniciales

- `GET /health`
- `GET /ojs/health`
- `GET /dashboard`
- `GET /submissions`
- `GET /submissions/queue`
- `GET /submissions/review`
- `GET /submissions/editing`
- `GET /submissions/published`
- `GET /submissions/{id}`
- `GET /submissions/{id}/files`

## Variables de entorno

Crear en Render:

```text
OJS_BASE_URL=https://scriptascientia.com/sasc/api/v1
OJS_API_TOKEN=tu_llave_api_nueva_de_ojs
EDITORIAL_API_KEY=una_clave_larga_para_proteger_esta_api
REQUEST_TIMEOUT_SECONDS=30
```

## Prueba local

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

## Prueba con API key

```bash
curl -H "X-API-Key: TU_EDITORIAL_API_KEY" https://TU-APP.onrender.com/dashboard
```

## Notas de seguridad

- No subir `.env` a GitHub.
- Revocar la API Key de OJS que haya quedado visible en pantalla.
- Usar `EDITORIAL_API_KEY` para impedir acceso público a la API editorial.
