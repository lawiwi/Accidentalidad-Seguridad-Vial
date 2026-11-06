"""
Sección «Análisis multidimensional» (Etapa 5) del proyecto Seguridad Vial Sabana Centro.

Se integra a la aplicación existente como un Blueprint, sin alterar las rutas de las
etapas anteriores. En app.py solo se agregan dos líneas:

    from multidimensional import bp_multidimensional
    app.register_blueprint(bp_multidimensional)
"""
from .routes import bp_multidimensional  # noqa: F401
