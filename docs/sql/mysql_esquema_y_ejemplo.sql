-- ============================================================
-- Plataforma de presupuestos de obra - Edificación, Colombia
-- Esquema según el ERD + catálogo de insumos + ejemplo
-- ============================================================
-- NOTAS DE FUENTES (citar en la documentación):
--  * Precios de materiales: valores promedio de referencia de mercado
--    (valores ilustrativos; validar por región y fecha, antes de IVA).
--  * Actualización de costos: ICOCED del DANE (índice oficial).
--  * Rendimientos / composición: contrastar con CYPE Generador de
--    Precios (Colombia). Las cantidades del ejemplo son ILUSTRATIVAS.
--  * Líneas marcadas "ESTIMADO" no vienen de una fuente verificada:
--    confírmalas antes de entregar.
-- ============================================================

CREATE DATABASE IF NOT EXISTS presupuestos_db CHARACTER SET utf8mb4;
USE presupuestos_db;

CREATE TABLE USUARIOS (
  id_usuario INT AUTO_INCREMENT PRIMARY KEY,
  nombre_completo VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  rol VARCHAR(50) NOT NULL
);

CREATE TABLE CREDENCIALES (
  id_usuario INT PRIMARY KEY,
  password_hash VARCHAR(255) NOT NULL,
  FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario) ON DELETE CASCADE
);

CREATE TABLE PROYECTOS (
  id_proyecto INT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT NOT NULL,
  nombre_obra VARCHAR(150) NOT NULL,
  cliente VARCHAR(150),
  FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
);

CREATE TABLE PRESUPUESTOS (
  id_presupuesto INT AUTO_INCREMENT PRIMARY KEY,
  id_proyecto INT NOT NULL,
  fecha_calculo DATE NOT NULL,
  costo_total DECIMAL(14,2) DEFAULT 0,
  FOREIGN KEY (id_proyecto) REFERENCES PROYECTOS(id_proyecto)
);

CREATE TABLE INSUMOS (
  id_insumo INT AUTO_INCREMENT PRIMARY KEY,
  nombre_insumo VARCHAR(150) NOT NULL UNIQUE,
  unidad_medida VARCHAR(30) NOT NULL,
  costo_unitario DECIMAL(14,2) NOT NULL
);

CREATE TABLE DETALLE_PRESUPUESTO (
  id_detalle INT AUTO_INCREMENT PRIMARY KEY,
  id_presupuesto INT NOT NULL,
  id_insumo INT NOT NULL,
  cantidad DECIMAL(14,3) NOT NULL,
  costo_unitario_aplicado DECIMAL(14,2) NOT NULL,
  FOREIGN KEY (id_presupuesto) REFERENCES PRESUPUESTOS(id_presupuesto),
  FOREIGN KEY (id_insumo) REFERENCES INSUMOS(id_insumo)
);

-- ------------------------------------------------------------
-- Catálogo de insumos (COP, antes de IVA)
-- ------------------------------------------------------------
INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) VALUES
('Cemento Portland gris tipo I', 'bulto 50 kg', 38900),
('Cemento blanco', 'bulto 50 kg', 41000),
('Acero corrugado 1/2" (varilla 6 m)', 'unidad', 46500),
('Acero corrugado 3/8" (varilla 6 m)', 'unidad', 30000),
('Arena de río lavada', 'm3', 95000),
('Grava / piedra triturada 3/4"', 'm3', 122000),
('Concreto premezclado 3000 PSI', 'm3', 485000),
('Alambre negro calibre 18', 'kg', 7800),
('Ladrillo tolete común', 'millar', 1280000),
('Bloque No. 4 (10x20x30)', 'unidad', 2450),
('Bloque No. 5', 'unidad', 3500),
('Tubería PVC presión 1/2" (tubo 6 m)', 'unidad', 24500),
('Pintura vinilo tipo 1', 'galón', 43000),
('Pintura esmalte', 'galón', 80000),
('Cerámica básica', 'm2', 32000),
('Oficial de construcción (jornal)', 'jornal', 115000),  -- valor de demostración; validar según región y fecha
('Ayudante de obra (jornal)', 'jornal', 75000);          -- ESTIMADO: verificar

-- ------------------------------------------------------------
-- Ejemplo: Viga entre zapatas, 10 m lineales, sección 0,30 x 0,30 m
-- (cantidades ILUSTRATIVAS: contrastar con CYPE)
-- ------------------------------------------------------------
INSERT INTO USUARIOS (nombre_completo, email, rol)
VALUES ('Arquitecto de prueba', 'arquitecto@ejemplo.com', 'arquitecto');

INSERT INTO PROYECTOS (id_usuario, nombre_obra, cliente)
VALUES (1, 'Vivienda unifamiliar - Proyecto de demostración', 'Cliente de ejemplo');

INSERT INTO PRESUPUESTOS (id_proyecto, fecha_calculo)
VALUES (1, CURDATE());

INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado)
SELECT 1, id_insumo, 0.95, costo_unitario FROM INSUMOS
WHERE nombre_insumo = 'Concreto premezclado 3000 PSI';       -- 0,9 m3 + 5% desperdicio

INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado)
SELECT 1, id_insumo, 8, costo_unitario FROM INSUMOS
WHERE nombre_insumo = 'Acero corrugado 1/2" (varilla 6 m)';  -- 4 barras longitudinales + traslapos

INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado)
SELECT 1, id_insumo, 10, costo_unitario FROM INSUMOS
WHERE nombre_insumo = 'Acero corrugado 3/8" (varilla 6 m)';  -- estribos cada 0,20 m

INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado)
SELECT 1, id_insumo, 3, costo_unitario FROM INSUMOS
WHERE nombre_insumo = 'Alambre negro calibre 18';

INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado)
SELECT 1, id_insumo, 2, costo_unitario FROM INSUMOS
WHERE nombre_insumo = 'Oficial de construcción (jornal)';

INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado)
SELECT 1, id_insumo, 3, costo_unitario FROM INSUMOS
WHERE nombre_insumo = 'Ayudante de obra (jornal)';

-- Cálculo del costo total (lo que hará el endpoint /calcular en Flask)
UPDATE PRESUPUESTOS p
SET costo_total = (
  SELECT SUM(d.cantidad * d.costo_unitario_aplicado)
  FROM DETALLE_PRESUPUESTO d
  WHERE d.id_presupuesto = p.id_presupuesto
)
WHERE p.id_presupuesto = 1;

-- Verificación: debe dar 1.611.150
SELECT id_presupuesto, costo_total FROM PRESUPUESTOS;
