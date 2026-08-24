⚙️ Instalación
1. Clonar el repositorio
git clone https://github.com/lawiwi/Accidentalidad-Seguridad-Vial.git

y Entrar a la carpeta:
cd Accidentalidad-Seguridad-Vial


2. Crear el entorno virtual
Se recomienda utilizar un entorno virtual para mantener aisladas las dependencias del proyecto.
python -m venv venv

3. Entrar a Visual Code
Aquí abriremos una terminal

4. Activar el entorno virtual
Usamos el siguiente comando
venv\Scripts\activate

Cuando el entorno esté activo, aparecerá (venv) al inicio de la terminal:
(venv) C:\...\Comunicaciondedatos>

5. Instalar las dependencias
Con el entorno virtual activado:
pip install -r requirements.txt

Esto instalará automáticamente las librerías necesarias para ejecutar el proyecto.

▶️ Ejecutar la aplicación

Una vez instaladas las dependencias, ejecutar:
python app.py

La aplicación estará disponible normalmente en:
http://127.0.0.1:5000

También puede accederse desde otros dispositivos de la misma red utilizando la dirección IP mostrada por Flask, por ejemplo:
http://192.168.20.154:5000
