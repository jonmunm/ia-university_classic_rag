-- ==============================================================================
-- 1. TABLAS DE DOMINIO (Estados Normalizados)
-- ==============================================================================

CREATE TABLE estado_financiero (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL -- Ej: 'Al Día', 'Moroso'
);

CREATE TABLE estado_carrera (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL -- Ej: 'Activa', 'Suspendida', 'Abandonada', 'En Pérdida', 'Egresada', 'Titulada'
);

CREATE TABLE estado_matricula (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL -- Ej: 'Pagado', 'Pendiente', 'Moroso'
);

CREATE TABLE estado_asignatura (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL -- Ej: 'Inscrita', 'Aprobada', 'Reprobada', 'Renunciada', 'Convalidada'
);

CREATE TABLE estado_practica (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL -- Ej: 'Inscrita', 'Activa', 'Terminada', 'Aprobada', 'Rechazada'
);

-- ==============================================================================
-- 2. ENTIDADES MAESTRAS (Catálogos)
-- ==============================================================================

CREATE TABLE semestre (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) UNIQUE NOT NULL, -- Ej: '2026-1', '2026-2'
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL
);

CREATE TABLE campus (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

CREATE TABLE alumno (
    id SERIAL PRIMARY KEY,
    rut VARCHAR(12) UNIQUE NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    estado_financiero_id INT REFERENCES estado_financiero(id)
);

CREATE TABLE carrera (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    duracion_semestres INT NOT NULL
);

CREATE TABLE asignatura (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL, 
    nombre VARCHAR(150) NOT NULL,
    carrera_id INT NOT NULL REFERENCES carrera(id),
    nivel_semestre INT NOT NULL 
);

-- ==============================================================================
-- 3. INSCRIPCIÓN DE LA CARRERA (El Expediente Académico)
-- ==============================================================================

CREATE TABLE inscripcion_carrera (
    id SERIAL PRIMARY KEY,
    alumno_id INT REFERENCES alumno(id),
    carrera_id INT REFERENCES carrera(id),
    campus_id INT REFERENCES campus(id),
    semestre_ingreso_id INT REFERENCES semestre(id),
    estado_carrera_id INT REFERENCES estado_carrera(id),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (alumno_id, carrera_id) 
);

CREATE TABLE historial_inscripcion_carrera (
    id SERIAL PRIMARY KEY,
    inscripcion_carrera_id INT REFERENCES inscripcion_carrera(id),
    semestre_id INT REFERENCES semestre(id),
    estado_carrera_id INT REFERENCES estado_carrera(id),
    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    motivo TEXT 
);

CREATE TABLE matricula_semestral (
    id SERIAL PRIMARY KEY,
    inscripcion_carrera_id INT REFERENCES inscripcion_carrera(id),
    semestre_id INT REFERENCES semestre(id),
    monto DECIMAL(10,2) NOT NULL,
    estado_matricula_id INT REFERENCES estado_matricula(id),
    UNIQUE (inscripcion_carrera_id, semestre_id)
);

-- ==============================================================================
-- 4. INSCRIPCIÓN DE ASIGNATURAS (La Carga Académica)
-- ==============================================================================

CREATE TABLE inscripcion_asignatura (
    id SERIAL PRIMARY KEY,
    inscripcion_carrera_id INT REFERENCES inscripcion_carrera(id),
    asignatura_id INT REFERENCES asignatura(id),
    semestre_id INT REFERENCES semestre(id), 
    calificacion_presentacion DECIMAL(2,1),
    calificacion_examen DECIMAL(2,1),
    calificacion_final DECIMAL(2,1),
    porcentaje_asistencia INT,
    estado_asignatura_id INT REFERENCES estado_asignatura(id),
    fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (inscripcion_carrera_id, asignatura_id, semestre_id)
);

CREATE TABLE historial_inscripcion_asignatura (
    id SERIAL PRIMARY KEY,
    inscripcion_asignatura_id INT REFERENCES inscripcion_asignatura(id),
    semestre_id INT REFERENCES semestre(id), -- AGREGAR ESTA LÍNEA
    estado_asignatura_id INT REFERENCES estado_asignatura(id),
    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_modifica VARCHAR(50) 
);

-- ==============================================================================
-- 5. PRÁCTICAS PROFESIONALES Y TITULACIÓN
-- ==============================================================================

CREATE TABLE practica_profesional (
    id SERIAL PRIMARY KEY,
    inscripcion_carrera_id INT NOT NULL REFERENCES inscripcion_carrera(id),
    semestre_id INT REFERENCES semestre(id), -- Semestre en el que inscribe la práctica
    centro_practica VARCHAR(200), -- Empresa o institución
    supervisor_empresa VARCHAR(150),
    profesor_guia VARCHAR(150),
    horas_requeridas INT NOT NULL DEFAULT 360,
    calificacion_final DECIMAL(2,1),
    estado_practica_id INT REFERENCES estado_practica(id),
    fecha_inicio DATE,
    fecha_termino DATE,
    fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (inscripcion_carrera_id) -- Asume 1 práctica final por carrera. Si pueden ser múltiples (Ej: Práctica 1 y 2), quita este UNIQUE.
);

CREATE TABLE historial_practica_profesional (
    id SERIAL PRIMARY KEY,
    practica_profesional_id INT REFERENCES practica_profesional(id),
    estado_practica_id INT REFERENCES estado_practica(id),
    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comentarios TEXT -- Útil para registrar por qué se rechazó o aprobó
);