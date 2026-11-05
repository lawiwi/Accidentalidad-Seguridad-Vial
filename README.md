 ⚙️ Instalación

Clonar el repositorio git clone https://github.com/lawiwi/Accidentalidad-Seguridad-Vial.git y Entrar a la carpeta: cd Accidentalidad-Seguridad-Vial

Crear el entorno virtual Se recomienda utilizar un entorno virtual para mantener aisladas las dependencias del proyecto. python -m venv venv

Entrar a Visual Code Aquí abriremos una terminal

Activar el entorno virtual Usamos el siguiente comando venv\Scripts\activate

Cuando el entorno esté activo, aparecerá (venv) al inicio de la terminal: (venv) C:...\Comunicaciondedatos>

Instalar las dependencias Con el entorno virtual activado: pip install -r requirements.txt Esto instalará automáticamente las librerías necesarias para ejecutar el proyecto.

▶️ Ejecutar la aplicación

Una vez instaladas las dependencias, ejecutar: python app.py

La aplicación estará disponible normalmente en: http://127.0.0.1:5000

También puede accederse desde otros dispositivos de la misma red utilizando la dirección IP mostrada por Flask, por ejemplo: http://192.168.20.154:5000

## Conocimiento evidente

La sección **Conocimiento evidente** de la aplicación reúne las cuatro preguntas de análisis
(composición de vehículos, diferencias territoriales, comportamiento temporal y cruce
multivariado) y permite consultar el informe interactivo de Power BI.

- **Informe publicado en Power BI:** [Abrir el informe interactivo](https://app.powerbi.com/view?r=eyJrIjoiZTc1MTFjOWUtMmJlMy00Mjg0LThiZjQtMTY4NWE3ZGRjMTc0IiwidCI6IjA3ZGE2N2EwLTFmNDMtNGU4Yy05NzdmLTVmODhiNjQ3MGVlNiIsImMiOjR9)
- **Acceso en la aplicación:** al ejecutar `python app.py`, abrir `http://127.0.0.1:5000/Etapa4` y seleccionar **Conocimiento evidente** en el menú.
- **Configuración opcional:** definir la variable de entorno `POWERBI_REPORT_URL` para sustituir la URL del informe usada por la aplicación.

La publicación es de acceso público a través de Power BI. Si el informe no carga integrado en la página, se puede abrir mediante el enlace directo anterior. Los análisis de vehículos cubren enero de 2022 a febrero de 2026 (2026 parcial); el tablero territorial presentadocorresponde a enero–agosto de 2019. Sus unidades de análisis son diferentes y no se deben sumar como si fueran una sola población.

## Análisis multidimensional (Etapa 5)

La sección **Análisis multidimensional** (`/analisis-multidimensional/`) presenta un modelo estrella construido con los datos tratados de vehículos involucrados en accidentes de tránsito (tabla `dbo.Vehiculo` de la base `IntegracionSiniestrosVehiculos`, 406.540 registros, enero de 2022 a febrero de 2026) y cuatro vistas interactivas con drill-down, roll-up, slice, dice y pivot. No usa la fuente de siniestros.

- **Modelo:** `FactVehiculoAccidente` + 7 dimensiones (Tiempo, Ubicación, Tipo de vehículo, Marca, Gravedad, Autoridad de tránsito, Antigüedad). Diagrama: `modelo_multidimensional/diagrama/modelo_estrella.png`.
- **SQL Server:** ejecutar en SSMS `modelo_multidimensional/sql/01` → `02` → `03` → `05` (validaciones) → `04` (consultas). Requiere el `.bak` restaurado con `WITH FILE = 3`; el nombre de la base de origen se ajusta en `@BaseOrigen` (script 01).
- **Réplica para la aplicación:** `modelo_multidimensional/dw/dw_accidentalidad_vial.sqlite` (incluida). Para regenerarla: `python modelo_multidimensional/etl/construir_dw.py` (debe terminar con «Resultado global: OK»).
- **Datos utilizados:** `modelo_multidimensional/origen_tratado/*.csv.gz` (exportación de `dbo.Vehiculo` y sus catálogos desde la base tratada).
- **Consultar SQL Server desde Flask (opcional):** definir `DW_DATABASE_URL=mssql+pyodbc://@SERVIDOR/DW_AccidentalidadVial?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes` e instalar `pyodbc`.
- **Pruebas:** `pip install pytest` y `pytest -q tests/`.
- **Documentación:** `docs/etapa5/` (informe técnico, guía de desarrollo, diccionario del modelo, plan de trabajo y guía de commits).
- **URL de la aplicación publicada:** _(pendiente: pegar aquí la URL de Render)_ `/analisis-multidimensional/`
