# Políticas y Reglas Académicas y Mapeo SQL (Capa Semántica RAG)

Este documento contiene las reglas de negocio de la institución y sus correspondientes directrices de traducción a SQL, diseñadas específicamente para proveer contexto a un modelo de lenguaje (LLM) en una arquitectura Text-to-SQL.

---

## Estructura Base de Relaciones (Join Paths Obligatorios)
Para extraer información descriptiva de los estudiantes y sus programas, utiliza SIEMPRE el siguiente camino base, asegurándote de declarar todas las tablas involucradas:

<!-- AJUSTE 1: Hacer opcional el JOIN a 'campus' para no forzar cruces innecesarios -->
* **Para datos del estudiante y su carrera:** `alumno a` -> `JOIN inscripcion_carrera ic ON a.id = ic.alumno_id` -> `JOIN carrera c ON ic.carrera_id = c.id` *(Nota: Une `JOIN campus ca ON ic.campus_id = ca.id` ÚNICAMENTE si la consulta menciona o solicita explícitamente el campus)*.

<!-- AJUSTE 2: Regla general de presencia en un semestre vs cohorte de ingreso y filtro por año completo -->
> 💡 **MAPEO SQL PARA LLM (PRESENCIA SEMESTRAL, AÑOS COMPLETOS VS INGRESO):**
> * **`ic.semestre_ingreso_id` es SOLO la cohorte de entrada (primer año):** PROHIBIDO hacer `JOIN semestre s ON ic.semestre_ingreso_id = s.id` para filtrar qué alumnos estaban cursando, activos o morosos en un semestre específico (ej. `'2019-1'`). Solo úsalo si el usuario pide explícitamente *"alumnos que ingresaron en..."* o pide proyectar el semestre de ingreso en el `SELECT`.
> * **Presencia efectiva en un semestre:** Siempre que se pida el estado o lista de alumnos en un semestre dado (sin consultar asignaturas específicas), DEBES unir `JOIN matricula_semestral ms ON ic.id = ms.inscripcion_carrera_id` y `JOIN semestre s ON ms.semestre_id = s.id`.
> * ✅ **CONSULTAS POR AÑO COMPLETO (NO SON AMBIGUAS):** Si el usuario filtra por un año calendario completo (ej. *"durante el año 2021"*, *"en 2021"*) sin especificar semestre (`2021-1` o `2021-2`), **NUNCA marques la consulta como ambigua ni devuelvas error**. Debes considerar el año completo uniendo con la tabla `semestre s` y filtrando por su rango de fechas: `s.fecha_inicio >= '2021-01-01' AND s.fecha_fin <= '2021-12-31'`.

## Definiciones

### Tipos de Estudiantes
* **Alumno nuevo:** Estudiante que matricula una carrera por primera vez en la institución, sin historial previo en dicho programa.
* **Alumno antiguo:** Estudiante que renueva matrícula en un programa en el que ya posee historial.

<!-- AJUSTE 3: Blindar el cruce entre asignatura y matrícula en alumnos antiguos para evitar Fan-Out -->
> 💡 **MAPEO SQL PARA LLM (Definiciones de Antigüedad):**
> * Para identificar si un alumno es NUEVO o ANTIGUO, la comparación temporal **SIEMPRE** se hace cruzando el ingreso con la matrícula del semestre consultado.
> * **NUEVO:** `inscripcion_carrera.semestre_ingreso_id = matricula_semestral.semestre_id`
> * ✅ **REGLA DE ANTIGÜEDAD (ALUMNO ANTIGUO):** Para saber si un alumno es antiguo, DEBES hacer JOIN a `matricula_semestral` y aplicar SIEMPRE la condición `ic.semestre_ingreso_id < matricula_semestral.semestre_id`.
> * ⚠️ **REGLA OBLIGATORIA AL CRUZAR CON ASIGNATURAS (`inscripcion_asignatura ia`):** Cuando la consulta evalúe "alumnos antiguos" que cursaron o reprobaron una asignatura en un semestre específico (ej. `'2020-1'`), DEBES amarrar tanto la asignatura como la matrícula al mismo semestre para evitar productos cartesianos:
>   ```sql
>   JOIN inscripcion_asignatura ia ON ic.id = ia.inscripcion_carrera_id
>   JOIN matricula_semestral ms ON ic.id = ms.inscripcion_carrera_id AND ia.semestre_id = ms.semestre_id
>   JOIN semestre s ON ms.semestre_id = s.id
>   WHERE ic.semestre_ingreso_id < ms.semestre_id
>   ```
> * 🚫 **ESTRICTAMENTE PROHIBIDO:** Usar la tabla `inscripcion_asignatura` por sí sola (o con `NOT EXISTS`) para definir si un alumno es nuevo o antiguo. Esto provocará conteos duplicados (Fan-Out). Usa exclusivamente la tabla `matricula_semestral` como se indicó arriba.

### Estados Globales del Alumno (Persona)
* **Al Día:** Estudiante que no presenta deudas financieras con la institución.
* **Moroso:** Estudiante que presenta atrasos en sus obligaciones financieras (cuotas de arancel o matrícula) por sobre los plazos estipulados en su contrato. Afecta transversalmente a todas sus carreras.

### Estados de la Carrera del Alumno (Expediente Académico)
*Esta categoría define la situación académica de un alumno respecto a un programa de estudio específico.*

* **Carrera Activa (Regular):** El estudiante posee matrícula vigente en la carrera y se encuentra cursando asignaturas o en proceso de titulación.
* **Carrera Suspendida:** El estudiante ha tramitado una interrupción temporal formal en esta carrera, dentro de los plazos máximos permitidos.
* **Carrera Abandonada:** El estudiante ha dejado de cursar la carrera formal o informalmente, deteniendo sus obligaciones financieras asociadas a este programa.
* **Carrera en Pérdida:** Término o pérdida definitiva de la carrera por incumplimiento de normativas (exceder tiempo de suspensión o por causales académicas/disciplinarias).
* **Carrera Egresada:** El estudiante ha aprobado el 100% de la malla curricular y práctica profesional de esta carrera, pero aún no rinde su examen de título.
* **Carrera Titulada:** El estudiante ha aprobado su proceso de titulación en esta carrera y se ha emitido su diploma oficial.

### Estados de la Inscripción de Asignatura
* **Asignatura Inscrita (En Curso):** La asignatura ha sido registrada correctamente por el alumno en el período actual y se encuentra en desarrollo.
* **Asignatura Aprobada:** El alumno ha cumplido con los requisitos de asistencia mínima y ha obtenido una calificación final igual o superior a 4.0.
* **Asignatura Reprobada:** El alumno no ha alcanzado la calificación mínima final de 4.0 o ha incumplido el porcentaje mínimo de asistencia requerido, debiendo cursar la asignatura nuevamente.
* **Asignatura Renunciada (Botada):** El alumno ha dado de baja formalmente la asignatura dentro de los plazos establecidos (generalmente antes de las primeras evaluaciones), sin que esta afecte su promedio de notas ni se cuente como reprobación.
* **Asignatura Convalidada (Homologada):** Asignatura reconocida y aprobada administrativamente debido a estudios previos equivalentes realizados por el alumno, ya sea en la misma institución o en otra externa acreditada.

### Estados de la Práctica Profesional
* **Práctica Inscrita:** El alumno ha registrado su práctica en el sistema y ha entregado la documentación inicial, pero aún no comienza sus horas en el centro de práctica.
* **Práctica Activa:** El alumno se encuentra actualmente ejecutando sus funciones y completando las horas reglamentarias en el centro o empresa asignada.
* **Práctica Terminada (Pendiente de Evaluación):** El alumno ha completado el 100% de las horas requeridas en el centro de práctica, pero el informe final del supervisor de la empresa o del profesor guía de la institución aún no ha sido evaluado o calificado.
* **Práctica Aprobada:** La actividad ha sido evaluada satisfactoriamente tanto por el empleador (supervisor) como por la institución, cumpliendo con la nota mínima de aprobación.
* **Práctica Rechazada (Reprobada):** La práctica es invalidada o calificada bajo la nota mínima de aprobación. Esto puede ocurrir por evaluación técnica deficiente, incumplimiento de asistencia u horas, faltas graves a la ética profesional en la empresa, o abandono injustificado de las labores.

> 💡 **MAPEO SQL PARA LLM (Definiciones):**
> * Para buscar el estado general/financiero de un alumno (persona), realiza un `JOIN` entre la tabla `alumno` y `estado_financiero` usando `estado_financiero_id`. Los valores a buscar en `estado_financiero.nombre` son `'Al Día'` o `'Moroso'`.
> * Para buscar el estado académico de un alumno en una carrera, haz `JOIN` entre `inscripcion_carrera` y la tabla normalizada `estado_carrera` usando `estado_carrera_id`. Los valores literales en `estado_carrera.nombre` son: `'Activa'`, `'Suspendida'`, `'Abandonada'`, `'En Pérdida'`, `'Egresada'`, `'Titulada'`.
> * Para buscar el estado de las asignaturas, haz `JOIN` entre `inscripcion_asignatura` y `estado_asignatura` usando `estado_asignatura_id`. Valores: `'Inscrita'`, `'Aprobada'`, `'Reprobada'`, `'Renunciada'`, `'Convalidada'`.
> * Para buscar el estado de la práctica, haz `JOIN` entre `practica_profesional` y `estado_practica` usando `estado_practica_id`. Valores: `'Inscrita'`, `'Activa'`, `'Terminada'`, `'Aprobada'`, `'Rechazada'`.

### Presencia Académica y Filtros Temporales Generales
Cuando una consulta hace referencia a estudiantes "en un semestre o año X" (por ejemplo: "alumnos en 2019-1", "estudiantes durante 2021"), se asume que el estudiante estuvo **activo y matriculado** (o registró el evento consultado) durante ese período, independientemente de cuándo ingresó a la carrera.

> 💡 **MAPEO SQL PARA LLM (Presencia Semestral y Filtros Temporales):**
> * 🚫 **ESTRICTAMENTE PROHIBIDO:** Usar `inscripcion_carrera.semestre_ingreso_id` para aislar o filtrar en qué semestre nos encontramos (por ejemplo, cuando piden alumnos morosos o con carrera activa en `'2019-1'`). Ese campo solo indica cuándo empezó el alumno su primer año.
> * ✅ **REGLA OBLIGATORIA PARA LISTAR O CONTAR ALUMNOS EN UN SEMESTRE:** Si la consulta pide listar o contar alumnos, estudiantes, morosos o activos en un semestre específico (ej. "en 2019-1", "en 2020-1"), la presencia en ese semestre se valida **SIEMPRE** uniendo el expediente académico con `matricula_semestral` (`JOIN matricula_semestral ms ON ic.id = ms.inscripcion_carrera_id`) y luego a `semestre` (`JOIN semestre s ON ms.semestre_id = s.id`).
> * ✅ **REGLA OBLIGATORIA PARA FILTROS POR AÑO COMPLETO (EJ. "DURANTE EL AÑO 2021"):** Cuando el usuario mencione un año calendario completo (ej. "durante el año 2021", "en 2021") sin especificar semestre (`2021-1` o `2021-2`), **NO ES AMBIGUO y está PROHIBIDO devolver error de ambigüedad**. Debes abarcar todo el año uniendo la tabla del evento con `semestre s` y filtrando por fechas: `s.fecha_inicio >= '2021-01-01' AND s.fecha_fin <= '2021-12-31'`.
> * **EXCEPCIÓN PARA RENDIMIENTO:** **SÓLO** debes usar un JOIN a `inscripcion_asignatura` si el usuario pregunta específicamente por carga académica, notas, promedios, ramos inscritos, aprobados o reprobados.

---

## 1. Matrículas
El proceso de matrícula es el acto mediante el cual un estudiante oficializa su vínculo con la institución para un período académico determinado.

### 1.1. Matrícula de Alumnos Nuevos
* **Restricción de historial:** Un alumno es considerado nuevo en una carrera únicamente si no registra matrículas previas en dicho programa de estudios en la institución.

### 1.2. Matrícula de Alumnos Antiguos
* **Condición de continuidad:** El alumno antiguo es aquel que renueva su matrícula para continuar una carrera en la que ya estaba inserto.
* **Requisitos financieros y académicos:** Para proceder con la matrícula de un alumno antiguo, el estudiante no debe presentar deudas financieras vencidas con la institución ni estar afecto a causales de eliminación académica (estado "En Pérdida").

> 💡 **MAPEO SQL PARA LLM (Matrículas):**
> * Las matrículas semestrales se registran en la tabla `matricula_semestral`, la cual vincula el expediente del estudiante (`inscripcion_carrera_id`) con un semestre específico (`semestre_id`). 
> * Cuando el usuario pida listar o contar alumnos "matriculados" o presentes en un período, la consulta debe basarse en la existencia de registros en la tabla `matricula_semestral`, cruzada con la tabla `semestre` (`ms.semestre_id = s.id`).
> * Para listar alumnos habilitados para matricularse, se debe aplicar un `WHERE` validando que `estado_carrera.nombre != 'En Pérdida'` y `estado_financiero.nombre != 'Moroso'`.

---

## 2. Inscripción de Asignaturas (Ramos)
La inscripción de asignaturas es el proceso donde el alumno selecciona los ramos que cursará en el semestre.

### 2.1. Inscripción dentro de plazo
* **Proceso regular:** La inscripción dentro del plazo estipulado en el calendario académico permite al alumno asegurar su cupo en las secciones deseadas. 
* **Prerrequisitos:** El sistema de inscripción validará que el alumno haya aprobado todas las asignaturas que son prerrequisito del ramo que desea inscribir.

### 2.2. Inscripción fuera de plazo (Extemporánea)
* **Condiciones:** La inscripción o modificación de carga académica fuera de plazo solo se permite durante los primeros 10 días hábiles de iniciadas las clases.
* **Aprobación:** Toda inscripción fuera de plazo requiere la autorización formal del Jefe de Carrera y está sujeta a la disponibilidad de cupos en las secciones.

> 💡 **MAPEO SQL PARA LLM (Inscripción de Asignaturas y Cardinalidad N a N):**
> * Todas las asignaturas tomadas por un alumno están en la tabla `inscripcion_asignatura`.
> * La relación completa para saber qué ramos toma un estudiante en qué carrera es: `alumno` -> `inscripcion_carrera` -> `inscripcion_asignatura` -> `asignatura` -> `carrera`.
> * ⚠️ **ADVERTENCIA DE CARDINALIDAD:** Un alumno tiene MÚLTIPLES asignaturas (Relación 1 a N).
> * 🚫 **PROHIBICIÓN ESTRICTA DE SUM(CASE):** Para pivotes condicionales (ej. segmentar nuevos y antiguos) donde se cuenten ALUMNOS, está **estrictamente prohibido** utilizar la estructura `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`. Esto multiplica los resultados.
> * ✅ **PATRÓN OBLIGATORIO:** Debes usar **SIEMPRE** `COUNT(DISTINCT CASE WHEN [condición] THEN alumno_id END)` para garantizar el conteo de entidades únicas.

---

## 3. Calificaciones y Aprobación de Asignaturas
* **Escala de evaluación:** El rendimiento académico se evalúa en una escala numérica del 1.0 al 7.0, con un decimal.
* **Nota de aprobación mínima:** La calificación mínima final para aprobar una asignatura es un 4.0.

### 3.1 Aprobación regular (Eximición)
* **Eximición de examen final:** Un alumno se exime de rendir el examen final de una asignatura si su promedio de notas de presentación es igual o superior a 5.5, y no tiene calificaciones parciales inferiores a 4.0 durante el semestre. En este caso, la nota final de la asignatura será su nota de presentación.
* **Reprobación directa por notas:** El alumno que obtenga un promedio de presentación inferior a 3.5 reprueba automáticamente la asignatura sin derecho a examen, y deberá cursarla obligatoriamente en el siguiente período en que se dicte.

### 3.2 Aprobación mediante examen
* **Derecho a examen:** El alumno que no cumpla con los requisitos de eximición y tenga un promedio de notas de presentación igual o superior a 3.5, tiene el derecho y la obligación de rendir el examen final.
* **Ponderación:** La nota final de la asignatura se calculará ponderando la nota de presentación (promedio de las evaluaciones del semestre) en un 70% y la nota del examen final en un 30%.
* **Nota mínima de examen:** Para aprobar la asignatura mediante esta vía, el estudiante debe obtener una calificación mínima de 3.0 en el examen final, independientemente de su excelente nota de presentación.
* **Cálculo de aprobación final:** Si, tras aplicar la ponderación del 70% y 30%, la calificación final resultante es igual o superior a 4.0, la asignatura se considera aprobada. En caso contrario, se reprueba.

> 💡 **MAPEO SQL PARA LLM (Calificaciones):**
> * Para extraer o calcular notas, utiliza los campos `calificacion_presentacion`, `calificacion_examen` y `calificacion_final` de la tabla `inscripcion_asignatura`.
> * Para emular el cálculo de la nota final vía SQL usa la expresión aritmética: `ROUND((calificacion_presentacion * 0.70) + (calificacion_examen * 0.30), 1)`.
> * Para listar alumnos aprobados o reprobados en un ramo, haz `JOIN` con `estado_asignatura` y filtra por `nombre IN ('Aprobada', 'Reprobada')`.

---

## 4. Asistencias
* **Asistencia mínima exigida:** Para tener derecho a rendir el examen final o aprobar una asignatura, el alumno debe cumplir con un mínimo del 75% de asistencia a las clases lectivas y un 100% a los laboratorios o actividades prácticas.
* **Reprobación por inasistencia:** El incumplimiento del porcentaje mínimo de asistencia (RI) conduce a la reprobación automática de la asignatura, independientemente de las calificaciones obtenidas, quedando con calificación final de 1.0.

> 💡 **MAPEO SQL PARA LLM (Asistencias y Sigla RI):**
> * La asistencia total del semestre reside en la columna `porcentaje_asistencia` (tabla `inscripcion_asignatura`).
> * Cuando se solicite buscar estudiantes reprobados por inasistencia (a menudo referidos como "RI"), se debe filtrar utilizando `porcentaje_asistencia < 75` E `estado_asignatura.nombre = 'Reprobada'`. (Nota: Estos registros tendrán forzadamente `calificacion_final = 1.0`).

---

## 5. Evaluaciones
* **Tipos de evaluación:** El semestre incluye evaluaciones parciales (solemnes, controles, trabajos prácticos) y una evaluación final o examen.
* **Inasistencia a evaluaciones:** El alumno que no se presente a una evaluación parcial programada será calificado con la nota mínima (1.0).
* **Justificación de inasistencia:** Las inasistencias a evaluaciones solo pueden justificarse por motivos médicos o de fuerza mayor, presentando los certificados correspondientes a la Dirección Académica en un plazo máximo de 48 horas hábiles posteriores a la evaluación. Si la justificación es aceptada, el alumno tendrá derecho a rendir una prueba recuperativa al final del semestre.

> 💡 **MAPEO SQL PARA LLM (Evaluaciones y Cambios de Estado):**
> * Los ceros o ausencias injustificadas impactan directamente el promedio almacenado en `calificacion_presentacion` dentro de `inscripcion_asignatura`. 
> * Para revisar el historial de cómo cambió un estado de una asignatura por reprobación/justificación en un semestre particular, debes cruzar `inscripcion_asignatura` con `historial_inscripcion_asignatura` usando `inscripcion_asignatura_id`.
> * 🔑 **NUEVA REGLA (SEMESTRE DEL EVENTO):** La tabla `historial_inscripcion_asignatura` ahora cuenta con la llave foránea `semestre_id`. Cuando necesites saber **cuándo (en qué semestre)** se registró un evento de reprobación, renuncia, o modificación de estado de una asignatura, **SIEMPRE** debes conectar `historial_inscripcion_asignatura.semestre_id` a la tabla `semestre` para evaluar los filtros temporales de esos cambios.
> * ⚠️ **ADVERTENCIA DE CARDINALIDAD:** `historial_inscripcion_asignatura` es una tabla de relación 1 a N. Si vas a contar eventos de cambios, usa `COUNT(historial_inscripcion_asignatura.id)`. Si necesitas contar estudiantes afectados, usa `COUNT(DISTINCT alumno.id)`.

---

## 6. Suspensión de Estudios (Congelamiento)
La suspensión de estudios permite al alumno interrumpir temporalmente su avance académico sin perder su calidad de alumno regular, pasando su carrera temporalmente al estado **"Suspendida"**.

* **Plazos y condiciones:** La solicitud de suspensión debe presentarse formalmente antes de la fecha de término del período de modificación de carga académica. Si se suspende dentro de este plazo, se detienen los cobros de arancel del semestre en curso.
* **Duración máxima y paso a estado "En Pérdida":** Un estudiante puede suspender sus estudios por un máximo de dos semestres consecutivos o cuatro discontinuos a lo largo de su carrera. **Si un alumno suspende más allá de esta duración máxima permitida, se considerará como término o pérdida de carrera, y el estado de la carrera pasará automáticamente a "En Pérdida".**
* **Reincorporación:** Al finalizar el período de suspensión regular, el alumno debe solicitar su reincorporación formal; de lo contrario, pasará a estado de "Carrera Abandonada" o "En Pérdida", según el tiempo transcurrido.

<!-- AJUSTE 5: Evitar que el ejemplo de '%suspensión%' contamine consultas generales de eliminación -->
> 💡 **MAPEO SQL PARA LLM (Suspensión):**
> * Para listar carreras suspendidas **actualmente**, filtra `estado_carrera.nombre = 'Suspendida'` cruzando `estado_carrera` directamente con `inscripcion_carrera.estado_carrera_id`.
> * Para buscar estudiantes que pasaron a estado en pérdida **específicamente por exceder el plazo de suspensión**, **NO cruces el estado con `inscripcion_carrera`**. Debes evaluar el evento en el pasado conectando `estado_carrera` con `historial_inscripcion_carrera.estado_carrera_id`. El patrón correcto es: `hic.motivo ILIKE '%suspensión%' AND ec_historial.nombre = 'En Pérdida'`.
> * ⚠️ **IMPORTANTE:** Utiliza el filtro `hic.motivo ILIKE '%suspensión%'` **ÚNICAMENTE** cuando el usuario mencione explícitamente en su pregunta las palabras *"suspensión"*, *"postergación"* o *"congelamiento"*. Si el usuario pregunta por motivos de eliminación académica en general, **NO** filtres la columna `hic.motivo`.

---

## 7. Causales de Eliminación
Un alumno perderá su calidad de estudiante regular (eliminación académica) y **el estado de su carrera pasará de manera definitiva a "En Pérdida"** si incurre en alguna de las siguientes causales:

* **Reprobación reiterada:** Reprobar por tercera vez una misma asignatura.
* **Bajo rendimiento:** Obtener un promedio semestral ponderado inferior a 3.0 en dos semestres consecutivos.
* **Abandono prolongado:** No registrar matrícula ni solicitud de suspensión de estudios por dos semestres académicos consecutivos.
* **Faltas disciplinarias:** Incurrir en faltas graves o gravísimas al reglamento de convivencia institucional, previo proceso sumario.

<!-- AJUSTE 6: Prohibir ambigüedad por año completo, prohibir filtro literal ILIKE '%eliminación académica%' y fijar el patrón SQL -->
> 💡 **MAPEO SQL PARA LLM (Causales de Eliminación y N a N):**
> * Para encontrar a los alumnos eliminados **actualmente**, filtra cruzando `estado_carrera` con `inscripcion_carrera.estado_carrera_id` donde `nombre = 'En Pérdida'`.
> * ✅ **CONSULTAS DE ELIMINACIÓN DURANTE UN AÑO COMPLETO (EJ. "DURANTE EL AÑO 2021") — NO SON AMBIGUAS:** Cuando el usuario pida los estudiantes que pasaron al estado de carrera en pérdida durante un año específico (ej. *"durante el año 2021"*) sin indicar un semestre puntual, **ESTÁ ESTRICTAMENTE PROHIBIDO declarar la consulta como ambigua**. Debes consultar todo el año uniendo `historial_inscripcion_carrera hic` con `semestre s ON hic.semestre_id = s.id` y filtrando `s.fecha_inicio >= '2021-01-01' AND s.fecha_fin <= '2021-12-31'`:
>   ```sql
>   SELECT a.nombres, a.apellidos, c.nombre AS carrera, hic.motivo
>   FROM inscripcion_carrera ic
>   JOIN alumno a ON ic.alumno_id = a.id
>   JOIN carrera c ON ic.carrera_id = c.id
>   JOIN historial_inscripcion_carrera hic ON ic.id = hic.inscripcion_carrera_id
>   JOIN estado_carrera ec_historial ON hic.estado_carrera_id = ec_historial.id
>   JOIN semestre s ON hic.semestre_id = s.id
>   WHERE ec_historial.nombre = 'En Pérdida'
>     AND s.fecha_inicio >= '2021-01-01'
>     AND s.fecha_fin <= '2021-12-31';
>   ```
> * Si además se pide proyectar el **semestre de ingreso** del alumno en la misma consulta, haz un segundo `JOIN` a `semestre` usando otro alias conectado al expediente: `JOIN semestre s_ing ON ic.semestre_ingreso_id = s_ing.id`.
> * 🚫 **PROHIBIDO FILTRAR `hic.motivo` POR LA FRASE 'ELIMINACIÓN ACADÉMICA':** Cuando el usuario pida *"desglosados por el motivo exacto de eliminación académica"*, **NUNCA** agregues `AND hic.motivo ILIKE '%eliminación académica%'` en el `WHERE`. El estado `'En Pérdida'` ya representa la eliminación académica; solo debes proyectar la columna `hic.motivo` en el `SELECT`.
> * ⚠️ **ADVERTENCIA DE CARDINALIDAD:** Las tablas de historial (`historial_inscripcion_carrera`) tienen cardinalidad 1 a N con el expediente (`inscripcion_carrera`). Al agrupar o contar eventos de causal, evalúa si el usuario pide "cantidad de eventos registrados" (usa `COUNT(historial_inscripcion_carrera.id)`) o "cantidad de alumnos afectados" (usa `COUNT(DISTINCT alumno.id)`).

---

## 8. Prácticas Profesionales y Titulación
* **Requisitos de Práctica:** Para iniciar la práctica profesional, el alumno debe haber aprobado el 100% de las asignaturas estipuladas hasta el penúltimo semestre de su malla curricular.
* **Calidad de Egresado y Titulado:** Las normativas referidas a los cambios de estado hacia "Alumno Egresado" y "Alumno Titulado" se rigen por lo expuesto en la sección "Definiciones > Estados del Alumno".

> 💡 **MAPEO SQL PARA LLM (Prácticas Profesionales y Titulación):**
> * La información de las prácticas reside en la tabla `practica_profesional`, conectada al estudiante a través de `inscripcion_carrera_id`.
> * Si se pregunta "por qué reprobó la práctica el alumno X", haz `JOIN` con `historial_practica_profesional`, asegurando que `estado_practica_id` referencie a `'Rechazada'`, y obtén el texto de la columna `comentarios`.
> * ⚠️ **ADVERTENCIA DE CARDINALIDAD:** Puede existir más de un historial de práctica para un alumno. Utiliza siempre `COUNT(DISTINCT practica_profesional.id)` o `COUNT(DISTINCT alumno.id)` si cuentas la cantidad de estudiantes rechazados, no el conteo del historial.
> * *OJO:* No busques "titulados" en la tabla de prácticas. Los estados "Egresada" y "Titulada" pertenecen a `inscripcion_carrera` (cruzando con `estado_carrera`).

---

## 9. Finanzas y Aranceles
* **Obligación de pago:** La matrícula y el arancel anual son obligaciones adquiridas al momento de firmar el contrato de prestación de servicios.
* **Morosidad:** El atraso superior a 30 días en el pago de las cuotas de arancel cambiará el estado financiero a "Moroso", inhabilitando al estudiante para solicitar certificados oficiales, y un atraso superior a 60 días bloqueará la toma de ramos para el siguiente período académico.
* **Devoluciones:** En caso de retiro formal (abandono notificado) antes del inicio de clases, el alumno tiene derecho a la devolución del 100% del arancel pagado por adelantado, reteniendo la institución el valor de la matrícula por costos administrativos.

<!-- AJUSTE 4: Inyectar la regla de matricula_semestral DENTRO de Finanzas y Aranceles (Corrige el Caso 1) -->
> 💡 **MAPEO SQL PARA LLM (Finanzas y Aranceles):**
> * Para consultar alumnos con deudas generales/bloqueos, se usa el estado de la persona: `alumno a JOIN estado_financiero ef ON a.estado_financiero_id = ef.id` (`ef.nombre = 'Moroso'`).
> * ⚠️ **CRÍTICO — ALUMNOS MOROSOS Y/O CON CARRERA ACTIVA EN UN SEMESTRE ESPECÍFICO (EJ. `2019-1`):**
>   Si la pregunta filtra alumnos con estado financiero `'Moroso'` (y/o con carrera `'Activa'`) en un semestre determinado (ej. *"que en 2019-1 se encuentran con un estado financiero moroso, pero que mantienen su carrera activa"*), **ESTÁ ESTRICTAMENTE PROHIBIDO** unir la tabla `semestre` mediante `ic.semestre_ingreso_id = s.id`. Debes validar que el alumno estuvo matriculado en ese semestre uniendo `matricula_semestral`:
>   ```sql
>   FROM alumno a
>   JOIN estado_financiero ef ON a.estado_financiero_id = ef.id
>   JOIN inscripcion_carrera ic ON a.id = ic.alumno_id
>   JOIN carrera c ON ic.carrera_id = c.id
>   JOIN estado_carrera ec ON ic.estado_carrera_id = ec.id
>   JOIN matricula_semestral ms ON ic.id = ms.inscripcion_carrera_id
>   JOIN semestre s ON ms.semestre_id = s.id
>   WHERE ef.nombre = 'Moroso' AND ec.nombre = 'Activa' AND s.codigo = '2019-1'
>   ```
> * Para consultar el estado de pago de la matrícula de un semestre en específico (ej. "pagó la matrícula del semestre 2024-1"), se usa la tabla transaccional `matricula_semestral` haciendo `JOIN` con `estado_matricula` (`nombre IN ('Pagado', 'Pendiente', 'Moroso')`) y cruzando con la tabla `semestre`.
> * ⚠️ **ADVERTENCIA DE CARDINALIDAD:** `matricula_semestral` tiene un registro por cada semestre. NUNCA sumes montos (`SUM(monto)`) ni cuentes alumnos haciendo un `JOIN` directo con `inscripcion_asignatura` en la misma consulta, a menos que uses CTEs o Subqueries. Si lo haces directamente, los montos financieros se multiplicarán por la cantidad de ramos que el alumno tomó ese semestre (problema de Fan-Out).