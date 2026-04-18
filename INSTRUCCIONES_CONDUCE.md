# Sistema de Arqueo de Caja y Conduce de Envío

## Nuevas Funcionalidades Implementadas

### ✅ Turno Agregado
- Se agregó el turno de cierre a las **3:00 PM** en el selector de turnos

### ✅ Interfaz con Pestañas
- **Pestaña 1**: Arqueo de Caja (funcionalidad original)
- **Pestaña 2**: Conduce de Envío (nueva funcionalidad)

### ✅ Módulo de Conduce de Envío

#### Campos del Formulario:
1. **Información de la Empresa** (pre-llenada):
   - Nombre: HECTOR JUSTINADO LOPEZ
   - Teléfono: 809-575-4401
   - RNC: 13-0894-2
   - Dirección: CALLE 2 NO.5 LOS CIRUELITOS, SANTIAGO R.D

2. **Información del Envío**:
   - Fecha (automática)
   - Cliente
   - Número de bultos
   - Dirección del cliente
   - Número de factura
   - Descripción del contenido
   - Observaciones (pre-llenada)

#### Formato del PDF:
- **Dos copias por página** (original y copia)
- Formato exacto según la imagen proporcionada
- Incluye:
  - Encabezado con información de la empresa
  - Título "CONDUCE DE ENVIO"
  - Todos los campos del cliente
  - Descripción del contenido
  - Observaciones estándar
  - Espacios para firmas (RECIBIDO POR / ENTREGADO POR)

## Instrucciones de Uso

### Para usar el Conduce de Envío:

1. **Abrir la aplicación**: http://127.0.0.1:5000
2. **Hacer clic en la pestaña "Conduce de Envío"**
3. **Completar los campos requeridos**:
   - Cliente (obligatorio)
   - Dirección del cliente (obligatorio)
   - Descripción del contenido (obligatorio)
   - Número de bultos (opcional)
   - Número de factura (opcional)
4. **Hacer clic en "Generar Conduce"**
5. **El PDF se descargará automáticamente** con dos copias del conduce

### Campos Pre-llenados:
- **Información de la empresa**: Ya está configurada
- **Fecha**: Se establece automáticamente a la fecha actual
- **Observaciones**: Texto estándar pre-llenado

### Botones Disponibles:
- **Generar Conduce**: Crea y descarga el PDF
- **Limpiar Formulario**: Limpia solo los campos del cliente, mantiene la info de la empresa

## Ejecución de la Aplicación

```bash
# Activar entorno virtual (si no está activado)
.venv\Scripts\python.exe app.py

# La aplicación estará disponible en:
http://127.0.0.1:5000
```

## Características del PDF Generado

- **Formato A4**
- **Dos conduces idénticos por página**
- **Diseño profesional** que coincide exactamente con el formato solicitado
- **Información completa** de empresa y cliente
- **Espacios para firmas** claramente definidos
- **Descarga automática** con nombre descriptivo

El sistema mantiene toda la funcionalidad original del arqueo de caja y agrega el nuevo módulo de conduce de envío de manera integrada.