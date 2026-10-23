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