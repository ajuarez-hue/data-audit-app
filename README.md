# Data Audit App · Equilibrium

Plataforma de auditoría y limpieza de bases de datos de campo.  
Compatible con **SurveyCTO**, **KoBoToolbox** y **ODK Collect**.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
streamlit run app.py
```

La app se abrirá en `http://localhost:8501`.

## Archivos necesarios

| Archivo | Descripción | Obligatorio |
|---------|-------------|-------------|
| `app.py` | Script principal | ✅ |
| `logo_equilibrium.png` | Logo en el sidebar | ❌ (la app funciona sin él) |

> Las bases de datos e instrumentos se cargan desde la interfaz — **no incluir archivos de datos en el repositorio**.

## Módulos

- **Revisión de Encuesta** — auditoría del instrumento XLSForm (estructura, choices, programación)
- **Auditoría de Base de Datos** — missings, outliers, duplicados, Motor de Corrección

## Versión

`v3.3.0` · Equilibrium Business · Data · Communities
