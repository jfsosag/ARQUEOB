# AGENTS.md — Instrucciones del proyecto ARQUEOB

Sistema profesional de arqueo, conduces y cuentas por cobrar.
Stack: Flask, PostgreSQL, SQLAlchemy, Flask-Migrate, Bootstrap 5.

---

# EXPERIENCIA MÓVIL (Mobile First)

Quiero que la aplicación tenga una experiencia diferente cuando se visualice desde dispositivos móviles.

No quiero únicamente que los elementos se reduzcan de tamaño; quiero que la interfaz se adapte para ofrecer una mejor experiencia de uso.

## Navegación

En dispositivos móviles, reemplazar el menú superior por una barra de navegación inferior (Bottom Navigation), similar a la que utilizan aplicaciones como WhatsApp, Google Pay o Mercado Pago.

La barra inferior debe contener los accesos principales:

* Inicio
* Cobros
* Cobro Informal
* Conduce
* Arqueo

Debe permanecer fija en la parte inferior de la pantalla y ser cómoda para usar con una sola mano.

En computadoras y tablets se mantendrá el menú superior actual.

---

# REDISEÑO DEL MÓDULO DE COBRO (MÓVIL)

Actualmente la pantalla de cobro se ve muy cargada en teléfonos.

Quiero rediseñar completamente el flujo para dispositivos móviles.

Eliminar elementos innecesarios y simplificar la experiencia.

## Eliminar

Eliminar completamente la sección:

* Usuario seleccionado

No debe mostrarse ni ocupar espacio en la interfaz.

---

## Nuevo flujo (Wizard de 2 pasos)

En móviles, el cobro debe realizarse en dos pasos claramente separados.

### Paso 1: Seleccionar Cliente

Mostrar únicamente:

* Buscador de clientes
* Lista de resultados
* Botón para crear un nuevo cliente (si no existe)

Una vez seleccionado el cliente, pasar automáticamente al siguiente paso.

---

### Paso 2: Registrar el Cobro

Mostrar únicamente las facturas pendientes del cliente seleccionado.

Cada factura deberá visualizarse en una tarjeta (Card) con la siguiente información:

* Número de factura
* Concepto
* Fecha
* Total
* Saldo pendiente

Cada tarjeta debe permitir seleccionarse con un checkbox o interruptor.

Debajo de la lista mostrar:

* Total seleccionado
* Monto a pagar
* Forma de pago

Al seleccionar o deseleccionar facturas, el total debe actualizarse automáticamente.

---

# Forma de pago

Mostrar un selector con las siguientes opciones:

* Efectivo
* Cheque
* Transferencia
* Tarjeta

Los campos adicionales solo aparecerán cuando sean necesarios.

### Cheque

Mostrar únicamente:

* Banco
* Número de cheque

### Transferencia

Mostrar únicamente:

* Banco
* Número de referencia

### Tarjeta

No solicitar información adicional.

### Efectivo

No mostrar campos adicionales.

---

# Cobro Informal

El módulo de Cobro Informal puede conservar prácticamente el diseño actual.

Solo realizar las siguientes modificaciones:

* Eliminar completamente la sección **"Usuario seleccionado"**.
* Mantener el formulario limpio y centrado.
* Adaptar los campos para que ocupen todo el ancho de la pantalla en móviles.
* Botones grandes y fáciles de presionar.
* Formularios organizados en una sola columna.

---

# Diseño para móviles

En pantallas pequeñas:

* Todos los formularios deben mostrarse en una sola columna.
* Las tablas deben reemplazarse por tarjetas (Cards) cuando sea posible.
* Los botones deben ocupar todo el ancho (`btn-lg w-100`).
* Utilizar acordeones para ocultar información secundaria.
* Mantener suficiente espacio entre controles para facilitar su uso con el dedo.
* Evitar cualquier desplazamiento horizontal.

---

# Objetivo

Quiero que la aplicación se sienta como una aplicación móvil nativa. El usuario debe poder completar un cobro con pocos toques y sin navegar entre pantallas saturadas de información.

El flujo debe ser intuitivo, rápido y limpio, priorizando la experiencia en dispositivos móviles sin afectar el funcionamiento en computadoras.

---

# MEJORAS EN EL DASHBOARD Y FLUJO DE REGISTRO DE FACTURAS

## Dashboard — Eliminar botón

Eliminar completamente el botón **"Registrar Cobro"** que aparece en el Dashboard.

Ese acceso ya no es necesario porque el usuario puede ingresar al módulo desde el menú principal o desde los accesos rápidos.

---

## Accesos rápidos en dispositivos móviles

Los accesos rápidos del Dashboard se muestran en una fila con desplazamiento horizontal (Horizontal Scroll) en dispositivos móviles.

En computadoras se mantienen distribuidos en cuadrícula.

Accesos: Cobros, Cobro Informal, Conduce, Arqueo, Nuevo Cliente, Reportes.

---

## Gestión de Facturas desde Clientes

El registro de facturas se realiza **únicamente desde el módulo Clientes**.

No existe un módulo independiente de "Registrar Factura".

### Flujo

1. Ingresar al módulo Clientes.
2. Seleccionar un cliente.
3. En el detalle del cliente, usar el formulario "Registrar Factura".
4. Guardar.

### Ficha del cliente

La ficha del cliente muestra:

* Resumen: Total facturado, Total pagado, Pendiente.
* Tabla de facturas: Número, Fecha, Concepto, Total, Pagado, Pendiente, Estado, Acciones.
* Formulario para agregar nuevas facturas (sin campo de cliente, ya está seleccionado).
* Acciones por factura: Editar (si no está pagada), Eliminar (si no tiene pagos).

---

# NUEVO MÓDULO: REPORTES

Módulo centralizado de consultas, reimpresiones y reportes del sistema. Protegido por permisos.

## Permisos

El acceso al módulo **Reportes** (`reportes`) debe depender de los permisos asignados al usuario.

Si un usuario no tiene permiso:

* No debe visualizar el módulo en el menú.
* No debe aparecer en la navegación móvil.
* No podrá acceder escribiendo la URL directamente (debe responder con un error 403 - Acceso Denegado).

---

## Secciones del módulo

### 1. Reimpresión de Facturas

Consultar todas las facturas registradas.

Filtros:

* Número de factura
* Cliente
* Fecha inicial / Fecha final
* Estado (Pendiente, Parcial, Pagada)

Tabla con: Número, Cliente, Fecha, Concepto, Total, Saldo pendiente, Estado.

Acciones por registro: Ver, Reimprimir PDF, Descargar PDF.

No se genera una nueva factura; únicamente se reimprime el documento original.

---

### 2. Reporte de Cobros

Reporte de todos los cobros realizados (facturas + informales).

Filtros:

* Fecha inicial / Fecha final
* Cliente
* Usuario (solo admins/supervisores)
* Forma de pago
* Tipo de cobro (Factura o Informal)

Tabla con: Fecha, Cliente, Concepto, Forma de pago, Monto cobrado, Usuario, Número de recibo.

Al final: Total cobrado, Cantidad de cobros, Total por forma de pago (Efectivo, Cheque, Transferencia, Tarjeta).

Exportar a PDF y Excel.

---

### 3. Estado de Cuenta de Clientes

Buscar por: Nombre, Teléfono, Cédula/RNC.

Al seleccionar un cliente mostrar:

* Info del cliente (Nombre, Teléfono, Dirección, RNC/Cédula)
* Historial de facturas: Número, Fecha, Concepto, Total, Pagado, Saldo, Estado
* Totales: Total facturado, Total pagado, Balance pendiente

Imprimir / Descargar PDF del estado de cuenta.

---

### 4. Historial de Arqueos de Caja

Filtros: Fecha inicial / Fecha final, Usuario, Estado (Abierto, Cerrado).

Tabla con: Fecha, Hora, Usuario, Total efectivo, Total cheques, Total transferencias, Total tarjetas, Total general.

Acciones: Ver detalle, Reimprimir, Descargar PDF.

---

## Seguridad

* **Admin**: ve todos los registros del sistema.
* **Cajero**: solo ve sus propios cobros, arqueos y facturas.
* **Supervisor**: ve solo los módulos que tenga autorizados.

Los filtros respetan estas restricciones aunque el usuario intente modificar la URL o parámetros.

---

## Exportación

Todos los reportes permiten: Imprimir, PDF, Excel.

Documentos con diseño corporativo: logo, nombre empresa, fecha/hora, usuario, número de páginas, totales identificados.

---

# MEJORA DEL MÓDULO DE COBROS: PAGOS PARCIALES Y ASIGNACIÓN AUTOMÁTICA

Modificar la lógica de aplicación de pagos para que funcione como un sistema profesional de cuentas por cobrar.

No quiero que el usuario tenga que indicar manualmente cuánto pagar en cada factura. El sistema debe distribuir el pago automáticamente.

---

## Forma de pago de las facturas

Cada factura debe poder pagarse de dos maneras:

* Pago completo.
* Pago parcial.

Cada factura deberá almacenar: Total, Total pagado, Saldo pendiente, Estado.

Estados: Pendiente, Parcial, Pagada.

---

## Asignación automática del pago (FIFO)

Cuando un cliente tenga varias facturas pendientes, el sistema debe aplicar el dinero automáticamente, comenzando por la factura más antigua y continuando en orden cronológico hasta llegar a las más recientes (FIFO - First In, First Out).

No quiero que el usuario tenga que decidir cuánto dinero asignar a cada factura. El sistema debe hacerlo automáticamente.

---

### Ejemplo 1

Facturas pendientes: 1001 (RD$ 5,000), 1002 (RD$ 3,000), 1003 (RD$ 2,000).

Cliente paga RD$ 6,000.

Resultado: 1001 → Pagada (RD$ 5,000), 1002 → Parcial (RD$ 1,000), 1003 → Sin cambios.

### Ejemplo 2

Facturas: 1001 (RD$ 2,000), 1002 (RD$ 4,000), 1003 (RD$ 8,000).

Cliente paga RD$ 20,000.

Resultado: Todas pagadas. Excedente RD$ 6,000.

El sistema debe advertir el excedente y permitir al usuario decidir:

* Registrar como saldo a favor (crédito).
* Devolver el dinero.
* Cancelar para corregir el monto.

### Ejemplo 3

Facturas: 1001 (RD$ 5,000), 1002 (RD$ 7,000), 1003 (RD$ 4,000).

Cliente paga RD$ 5,000.

Resultado: 1001 → Pagada, 1002 y 1003 → Sin cambios.

---

## Orden de aplicación

Siempre: 1. Factura más antigua → 2. Segunda más antigua → 3. Tercera más antigua.

Nunca aplicar primero a las facturas más recientes.

---

## Historial del pago

Guardar exactamente cómo se distribuyó el pago. Ejemplo:

Recibo #1254: RD$ 10,000 → 1001 (RD$ 5,000), 1002 (RD$ 3,000), 1003 (RD$ 2,000).

Siempre debe poder reconstruirse el historial.

---

## Interfaz

Al seleccionar un cliente mostrar:

* Total pendiente del cliente.
* Cantidad de facturas pendientes.
* Fecha de la factura más antigua.
* Campo **"Monto recibido"**.
* Forma de pago.

No quiero que el usuario tenga que escribir cuánto corresponde a cada factura. El sistema se encarga de distribuir el pago automáticamente.

---

# ADAPTACIÓN DEL MÓDULO DE REPORTES PARA DISPOSITIVOS MÓVILES

El módulo Reportes debe tener interfaz completamente adaptada para dispositivos móviles. No solo reducir tablas; una experiencia optimizada para pantallas pequeñas.

---

## Vista principal

En móviles, la pantalla principal de Reportes muestra tarjetas (Cards) con las opciones:

* 📄 Reimpresión de Facturas
* 🧾 Reimpresión de Recibos de Cobro
* 💰 Reporte de Cobros
* 👥 Estado de Cuenta de Clientes
* 💵 Historial de Arqueos

Cada opción como tarjeta grande, fácil de presionar, en una sola columna.

En computadoras se mantienen las tablas tradicionales.

---

## Filtros adaptados para móviles

En teléfonos, los filtros no se muestran todos a la vez.

Utilizar un botón **"Filtros"** que abra un Offcanvas o Modal con los filtros disponibles.

Al presionar **Aplicar**, se actualiza la información.

---

## Resultados

En computadoras: tablas.

En móviles: tarjetas (Cards).

Ejemplo:

```
Factura #1025
Cliente: Juan Pérez
Fecha: 18/07/2026
Estado: Pendiente
Saldo: RD$ 3,500
[👁 Ver]  [🖨 Reimprimir]
```

---

## Reimpresión de Recibos de Cobro

Nueva sección dentro de Reportes.

Almacena todos los recibos generados: Cobros por Facturas y Cobros Informales.

Nunca se genera un recibo desde cero; el sistema conserva una copia de cada recibo emitido para reimprimirlo exactamente igual.

### Búsqueda de recibos

Filtros: Número de recibo, Cliente, Fecha inicial, Fecha final, Usuario, Tipo de cobro (Factura o Informal).

### Información del listado

Número de recibo, Fecha, Cliente, Tipo de cobro, Monto, Usuario, Forma de pago.

### Acciones

Ver detalle, Reimprimir, Descargar PDF.

La opción Reimprimir utiliza el mismo PDF generado al momento del cobro. No crea un documento nuevo con datos recalculados.

---

## Permisos

Todos los reportes respetan los permisos:

* **Admin**: ve todo.
* **Cajero**: solo ve sus propios recibos, arqueos y cobros.

---

# REDISEÑO COMPLETO DEL MÓDULO DE ARQUEO DE CAJA

Quiero rediseñar completamente el módulo de **Arqueo de Caja** para aprovechar mucho mejor el espacio disponible, especialmente en computadoras. El objetivo es reducir al mínimo el desplazamiento vertical (scroll) y tener toda la información importante visible en una sola pantalla.

---

## Distribución de la pantalla

Quiero dividir el contenido en **dos columnas principales**.

### Columna izquierda

Debe contener:

### 1. Desglose de efectivo por denominaciones

Mantener el desglose de billetes y monedas.

Mostrar:

* Cantidad
* Total por denominación

Actualizar automáticamente el total de efectivo.

---

### 2. Formas de pago distintas al efectivo

Debajo del desglose de efectivo colocar:

* Tarjetas
* Transferencias
* Cheques
* Vales
* Otros medios de pago

Cada registro debe tener:

* Concepto (opcional)
* Monto
* Botón **Agregar**

Al presionar **Agregar**, el registro debe agregarse inmediatamente a una tabla inferior y actualizar automáticamente los totales del arqueo.

No quiero que el botón solo limpie el formulario; debe insertar el registro en el arqueo.

---

### Columna derecha

Debe contener toda la información relacionada con las facturas.

---

## Resumen superior

En la parte superior de la columna derecha colocar un panel de resumen que se actualice automáticamente cada vez que el usuario registre una factura, un vale o una forma de pago.

Este panel debe mostrar:

### Totales por forma de pago

* Total en efectivo
* Total en tarjetas
* Total en transferencias
* Total en cheques
* Total en vales
* Total en otros medios de pago

---

### Totales de ventas

* Total vendido
* Total al contado
* Total a crédito

---

### Cantidades

* Cantidad de facturas al contado
* Cantidad de facturas a crédito
* Cantidad de vales
* Cantidad de registros no efectivos

Todo debe actualizarse en tiempo real sin necesidad de guardar el arqueo.

---

## Facturas al contado

La sección **Facturas al Contado** representa un resumen de las ventas del día y no un registro individual. No se agregan a la tabla de detalle mediante el botón **Agregar**. Esta información permanece fija en el formulario principal del arqueo.

### Nueva estructura

La sección se divide en tres bloques independientes:

#### 1. Sin Comprobante

* Monto Total
* Secuencia Inicial (Desde)
* Secuencia Final (Hasta)

Ejemplo: Monto RD$ 18,500.00 | Desde SC0000125 | Hasta SC0000148

#### 2. Con Comprobante

* Monto Total
* Secuencia Inicial (Desde)
* Secuencia Final (Hasta)

Ejemplo: Monto RD$ 45,800.00 | Desde B0200001250 | Hasta B0200001278

#### 3. Recibos de Ingreso

* Monto Total
* Secuencia Inicial (Desde)
* Secuencia Final (Hasta)

Ejemplo: Monto RD$ 9,200.00 | Desde RI0000580 | Hasta RI0000589

### Comportamiento

Estos tres bloques forman parte del encabezado del arqueo.

* No se agregan a la tabla de detalle.
* No tienen botón **Agregar**.
* No crean registros individuales.
* Su información se guarda directamente como parte del arqueo de caja.

### Resumen

Los montos de estos tres bloques actualizan automáticamente el panel de resumen. El sistema calcula:

* Total vendido al contado.
* Total de ventas sin comprobante.
* Total de ventas con comprobante.
* Total de recibos de ingreso.

Estos valores se suman al total general del arqueo y se reflejan en tiempo real.

---

## Facturas a crédito

Realizar exactamente el mismo cambio.

Agregar:

* Desde
* Hasta

Luego:

* Cantidad
* Total

Botón:

Agregar

Al guardar, debe insertarse en la tabla del arqueo y actualizar automáticamente todos los totales.

---

## Tabla de detalle

La tabla de detalle del arqueo se utiliza únicamente para registrar operaciones que puedan repetirse varias veces durante el día:

* Vales.
* Cheques.
* Transferencias.
* Pagos con tarjeta.
* Otros medios de pago.
* Facturas a crédito (si el flujo del negocio lo requiere).

Las **Facturas al Contado** no aparecen en esta tabla porque representan un resumen consolidado de las ventas del día.

---

## Optimización del espacio

No quiero tanto espacio vacío.

Reducir:

* Márgenes.
* Espaciados.
* Altura de tarjetas.
* Padding excesivo.

El objetivo es que en un monitor estándar casi todo el arqueo sea visible sin tener que desplazarse constantemente.

---

## Eliminar título

Eliminar completamente el encabezado que dice:

**"Arqueo de Caja"**

Ese espacio debe aprovecharse para mostrar más información útil.

---

## Botones superiores

Mover el botón **Generar PDF** a la parte superior derecha de la pantalla para que siempre esté visible.

Agregar un nuevo botón:

**Cargar Arqueo**

---

## Cargar Arqueo

Este botón permitirá consultar arqueos anteriores.

Al presionarlo debe abrir una ventana con filtros:

* Fecha inicial
* Fecha final
* Usuario (según permisos)

Mostrar una lista de arqueos.

Al seleccionar uno:

* Cargar toda la información del arqueo en pantalla.
* Mostrar exactamente cómo fue generado originalmente.

---

### Importante

Cuando se cargue un arqueo anterior:

* Todos los campos deben quedar en modo **solo lectura**.
* No debe ser posible modificar ninguna información.
* No debe ser posible guardar cambios sobre un arqueo ya cerrado.
* Solo se permitirá:

  * Consultarlo.
  * Reimprimirlo.
  * Descargar nuevamente el PDF.

---

## Diseño

Quiero un diseño similar al de un sistema POS profesional.

Las dos columnas deben ocupar prácticamente todo el ancho de la pantalla.

Los paneles de resumen deben ser compactos.

Las tablas deben tener poca altura de fila.

Los formularios deben estar alineados horizontalmente para aprovechar mejor el espacio.

El objetivo es que el usuario pueda visualizar casi todo el arqueo sin necesidad de hacer scroll.

---

## Comportamiento en dispositivos móviles

En teléfonos y tablets el diseño debe reorganizarse automáticamente en una sola columna, manteniendo el mismo orden lógico y una buena experiencia de uso.

---

## Objetivo

Quiero que el módulo de **Arqueo de Caja** tenga un diseño mucho más eficiente y profesional. La información crítica debe estar visible en tiempo real, los registros deben agregarse inmediatamente con el botón **Agregar**, el resumen debe actualizarse automáticamente y el usuario debe poder consultar arqueos anteriores en modo de solo lectura. Además, el espacio debe optimizarse al máximo para reducir el desplazamiento y mejorar la productividad durante el cierre de caja.

---

# REDISEÑO DEL REPORTE PDF DEL ARQUEO DE CAJA

Quiero rediseñar completamente el formato del PDF generado por el Arqueo de Caja para que sea más profesional, organizado y fácil de auditar.

El reporte debe seguir el siguiente orden:

---

## 1. Encabezado

En la parte superior debe aparecer:

* Logo de la empresa
* Nombre de la empresa
* Título **ARQUEO DE CAJA**
* Fecha
* Hora
* Usuario que realizó el arqueo

---

## 2. Resumen General

Debajo del encabezado colocar un cuadro resumen con los principales indicadores del cierre.

Debe mostrar:

### Ventas

* Venta Total
* Total Ventas al Contado
* Total Ventas a Crédito

### Ingresos por forma de pago

* Total recibido en Efectivo
* Total recibido en Tarjetas
* Total recibido en Transferencias
* Total recibido en Cheques
* Total recibido en Vales
* Total recibido por Otros medios de pago

### Totales

* Total de ingresos en efectivo
* Total de ingresos no efectivos
* Total general del arqueo

Este resumen debe aparecer al inicio del reporte para que el usuario pueda conocer el resultado del cierre sin necesidad de revisar todas las páginas.

---

## 3. Desglose del efectivo

Mostrar el detalle completo del efectivo contado.

Ejemplo:

| Denominación | Cantidad |      Total |
| ------------ | -------: | ---------: |
| RD$ 2,000    |        5 | RD$ 10,000 |
| RD$ 1,000    |        8 |  RD$ 8,000 |
| RD$ 500      |       10 |  RD$ 5,000 |
| RD$ 200      |       12 |  RD$ 2,400 |
| RD$ 100      |       20 |  RD$ 2,000 |
| RD$ 50       |       15 |    RD$ 750 |
| RD$ 25       |        8 |    RD$ 200 |
| RD$ 10       |       10 |    RD$ 100 |
| RD$ 5        |        5 |     RD$ 25 |
| RD$ 1        |       30 |     RD$ 30 |

Al final mostrar:

**Total Efectivo**

---

## 4. Formas de pago distintas al efectivo

Mostrar todas las operaciones registradas durante el arqueo.

Agruparlas por tipo.

### Tarjetas

Tabla:

* Concepto (si aplica)
* Monto

Al final: Total Tarjetas

### Transferencias

Tabla:

* Banco
* Número de referencia
* Monto

Al final: Total Transferencias

### Cheques

Tabla:

* Banco
* Número de cheque
* Monto

Al final: Total Cheques

### Vales

Tabla:

* Concepto
* Monto

Al final: Total Vales

### Otros Medios de Pago

Tabla:

* Concepto
* Monto

Al final: Total Otros Medios

---

## 5. Facturas al contado

Mostrar los tres bloques del arqueo exactamente como fueron registrados.

### Sin Comprobante

* Monto Total
* Factura Inicial
* Factura Final

### Con Comprobante

* Monto Total
* Factura Inicial
* Factura Final

### Recibos de Ingreso

* Monto Total
* Factura Inicial
* Factura Final

### IMPORTANTE

Los campos **Factura Inicial** y **Factura Final** deben almacenar y mostrar el **número interno de la factura** utilizado por la empresa.

**No quiero que se muestre el NCF.**

Debe mostrarse únicamente la numeración consecutiva de las facturas.

Ejemplo:

Factura Inicial: 1520

Factura Final: 1568

No: B02000001568

---

## 6. Facturas a Crédito

Al final del reporte mostrar todas las facturas a crédito registradas durante el arqueo.

Tabla:

* Número de factura
* Cliente
* Concepto
* Total

Al final mostrar:

* Cantidad de facturas a crédito
* Total facturado a crédito

---

## 7. Pie del reporte

Al final del documento mostrar:

* Total General del Arqueo
* Fecha y hora de impresión
* Usuario que imprimió el reporte

Agregar un espacio para las firmas:

**Preparado por** _______________

**Revisado por** _______________

**Autorizado por** _______________

---

## Diseño del PDF

Diseño limpio y profesional:

* Tablas bien alineadas.
* Totales resaltados.
* Separadores claros entre secciones.
* Márgenes optimizados para aprovechar el papel.
* Compatible con impresión en tamaño Carta y A4.
* Se debe mostrar claramente si el arqueo está **CUADRADO**, si **SOBRA** dinero o si **FALTA** dinero, con indicador visual (color verde para cuadrado, amarillo para sobra, rojo para falta) y el monto exacto de la diferencia.

El objetivo es que el reporte sea útil para auditorías y revisiones contables, mostrando de forma clara el resumen general, el detalle del efectivo, las formas de pago, los rangos de facturas utilizados y las facturas a crédito del cierre, utilizando siempre los **números internos de factura** en los campos **Factura Inicial** y **Factura Final**, nunca el NCF.

---

# DISEÑO PROFESIONAL DEL REPORTE DE ARQUEO DE CAJA

El reporte PDF del Arqueo de Caja debe tener un diseño completamente profesional, con apariencia similar a los reportes utilizados por sistemas ERP y software empresariales como SAP Business One, Odoo, QuickBooks o Dynamics 365.

No es un PDF simple con tablas básicas. Debe tener un diseño corporativo, elegante, limpio y fácil de leer.

---

## Identidad corporativa

En el encabezado incluir:

* Logo de la empresa.
* Nombre de la empresa en un tamaño destacado.
* Dirección (opcional).
* Teléfono.
* Correo electrónico (si está configurado).
* Título **ARQUEO DE CAJA**.
* Número del arqueo.
* Fecha.
* Hora.
* Usuario que realizó el cierre.

Todo perfectamente alineado.

---

## Tarjetas de resumen

Debajo del encabezado colocar un panel tipo Dashboard con indicadores resaltados.

Cada indicador debe mostrarse dentro de una tarjeta con un borde suave y un diseño elegante.

Ejemplo:

🟩 Venta Total — RD$ 350,250.00

🟦 Efectivo — RD$ 185,000.00

🟨 No Efectivo — RD$ 165,250.00

🟪 Crédito — RD$ 42,500.00

🟥 Diferencia — RD$ 0.00

Estas tarjetas deben ser el primer elemento visible del reporte.

---

## Indicador de cuadre

En las tarjetas de resumen, mostrar claramente el estado del cuadre:

* **CUADRADO** (verde) — cuando efectivo + no efectivo = facturado. Diferencia = RD$ 0.00
* **SOBRA** (amarillo) — cuando hay dinero de más. Mostrar: "Sobra RD$ X,XXX.XX"
* **FALTA** (rojo) — cuando falta dinero. Mostrar: "Falta RD$ X,XXX.XX"

Este indicador debe ser lo más visible del reporte para que el cajero y el auditor identifiquen inmediatamente el estado del cierre.

---

## Organización por secciones

Cada bloque del reporte debe tener un encabezado claramente diferenciado con fondo suave y tipografía en negrita.

---

## Tablas

Todas las tablas deben tener:

* Encabezados con fondo gris claro o color corporativo.
* Filas alternadas (efecto zebra) para facilitar la lectura.
* Totales resaltados.
* Alineación correcta de números y textos.
* Bordes discretos y uniformes.

---

## Totales

Todos los totales deben aparecer resaltados con negrita, mayor tamaño de fuente o un recuadro diferenciado.

---

## Distribución

El reporte debe aprovechar muy bien el espacio del papel.

Evitar espacios vacíos innecesarios.

Las secciones deben estar perfectamente alineadas.

No deben haber páginas con grandes espacios en blanco.

---

## Pie de página

En todas las páginas mostrar:

* Nombre del sistema.
* Fecha y hora de impresión.
* Usuario que imprimió el reporte.
* Número de página (ej: Página 1 de 3).

---

## Firmas

Al finalizar el documento agregar un área para firmas con tres columnas perfectamente alineadas:

**Preparado por** _______________

**Revisado por** _______________

**Autorizado por** _______________

---

## Calidad visual

El reporte debe tener una apariencia de software empresarial moderno.

Debe transmitir organización, profesionalismo y confianza.

Cuidar especialmente:

* Tipografía consistente.
* Alineación de todos los elementos.
* Espaciado uniforme.
* Colores sobrios y elegantes.
* Excelente legibilidad tanto en pantalla como impreso.

---

## Objetivo

Todos los reportes del sistema (Arqueo de Caja, Facturas, Recibos, Estados de Cuenta y Reportes de Cobros) deben compartir la misma línea gráfica y un diseño corporativo uniforme. Deben parecer documentos oficiales de una empresa, con una presentación limpia, moderna y de alta calidad, aptos para auditorías, contabilidad y entrega a clientes o entidades financieras. El resultado final debe transmitir la imagen de un software empresarial profesional, robusto y confiable.
