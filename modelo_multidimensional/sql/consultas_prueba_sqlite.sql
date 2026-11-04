-- =====================================================================================
-- consultas_prueba_sqlite.sql · Pruebas rápidas sobre la réplica SQLite que usa Flask
-- Ejecutar desde la raíz del repositorio:  python modelo_multidimensional/etl/probar_consultas.py
-- (o abrir el archivo .sqlite con DB Browser for SQLite y ejecutar cada consulta)
-- El valor esperado está en el comentario de cada consulta.
-- =====================================================================================

-- T1 Total de vehículos (esperado 406540)
SELECT SUM(CantidadVehiculos) AS total FROM FactVehiculoAccidente;

-- T2 Vehículos por año (2022=114478, 2023=111609, 2024=120342, 2025=57867, 2026=2244)
SELECT t.Anio, SUM(f.CantidadVehiculos) FROM FactVehiculoAccidente f JOIN DimTiempo t ON t.SK_Tiempo = f.SK_Tiempo GROUP BY t.Anio ORDER BY t.Anio;

-- T3 Vehículos en accidentes con muertos (esperado 20659) y % (5,08)
SELECT SUM(VehiculoAccidenteConMuertos), ROUND(100.0 * SUM(VehiculoAccidenteConMuertos) / SUM(CantidadVehiculos), 2) FROM FactVehiculoAccidente;

-- T4 Huérfanos (esperado 0)
SELECT COUNT(*) FROM FactVehiculoAccidente f LEFT JOIN DimUbicacion u ON u.SK_Ubicacion = f.SK_Ubicacion WHERE u.SK_Ubicacion IS NULL;

-- T5 Hechos en marca desconocida (esperado 44)
SELECT COUNT(*) FROM FactVehiculoAccidente WHERE SK_Marca = -1;

-- T6 % con muertos de vehículos de carga (esperado 21,1)
SELECT ROUND(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos), 2) FROM FactVehiculoAccidente f JOIN DimTipoVehiculo d ON d.SK_TipoVehiculo = f.SK_TipoVehiculo WHERE d.CategoriaVehiculo = 'Vehículo de carga';

-- T7 Julio de 2024 por la Secretaría de Tránsito de Medellín (esperado 22667)
SELECT SUM(f.CantidadVehiculos) FROM FactVehiculoAccidente f JOIN DimTiempo t ON t.SK_Tiempo = f.SK_Tiempo JOIN DimAutoridadTransito a ON a.SK_Autoridad = f.SK_Autoridad WHERE t.AnioMes = '2024-07' AND a.Autoridad = 'STRIA DE TTOYTTE MEDELLIN';

-- T8 Participación de las 10 marcas principales (esperado 73,83)
SELECT ROUND(100.0 * SUM(CASE WHEN m.GrupoMarca = '10 marcas principales' THEN f.CantidadVehiculos ELSE 0 END) / SUM(f.CantidadVehiculos), 2) FROM FactVehiculoAccidente f JOIN DimMarca m ON m.SK_Marca = f.SK_Marca;
