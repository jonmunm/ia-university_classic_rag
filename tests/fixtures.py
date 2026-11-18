FIXTURES = [
    {
        "query" : """
            Dame los nombres y apellidos de los alumnos de la carrera de Ingeniería Civil Informática" 
            que en 2019-1 se encuentran con un estado financiero moroso, pero que mantienen su carrera activa.
            """,
        "expected_sql" : """
                select 
                    a.nombres, a.apellidos 
                from inscripcion_carrera ic 
                    left join carrera c on ic.carrera_id = c.id 
                    left join alumno a on ic.alumno_id = a.id
                    left join estado_financiero ef on a.estado_financiero_id = ef.id
                    left join estado_carrera ec on ic.estado_carrera_id = ec.id 
                    left join matricula_semestral ms on ms.inscripcion_carrera_id = ic.id
                    left join semestre s on ms.semestre_id = s.id
                    
                where
                    c.nombre = 'Ingeniería Civil Informática'
                    and ef.nombre = 'Moroso'
                    and ec.nombre = 'Activa'
                    and s.codigo = '2019-1'
        """
    },
    {
        "query" : """
            Necesito el conteo de alumnos antiguos de 'Enfermería' que reprobaron la 
            asignatura de 'Anatomía Macroscópica' durante el semestre 2020-1 específicamente por no cumplir con el porcentaje mínimo de asistencia 
            requerido.
        """,
        "expected_sql" : """
            with step_0 as (
                select
                    al.nombres || ' ' || al.apellidos as alumno,
                    s.codigo as semestre_ingreso,
                    ec.nombre as estado_carrera
                FROM 
                    inscripcion_carrera ic
                    left JOIN semestre s on ic.semestre_ingreso_id = s.id
                    left JOIN carrera c on ic.carrera_id = c.id
                    left join alumno al on ic.alumno_id = al.id
                    left join estado_carrera ec on ic.estado_carrera_id = ec.id
                where
                    c.nombre = 'Enfermería'
                    and s.codigo in ('2018-1', '2019-1')
            ),

            step_1 as (
                select
                    al.nombres || ' ' || al.apellidos as alumno,
                    s.codigo as semestre_inscripcion,
                    ea.nombre as estado_asignatura,
                    ia.porcentaje_asistencia
                FROM 
                    inscripcion_asignatura ia 
                    left join estado_asignatura ea  on ia.estado_asignatura_id = ea.id
                    left join asignatura a on ia.asignatura_id = a.id
                    left JOIN semestre s on ia.semestre_id = s.id
                    left JOIN inscripcion_carrera ic on ia.inscripcion_carrera_id = ic.id
                    left JOIN carrera c on ic.carrera_id = c.id
                    left join alumno al on ic.alumno_id = al.id
                where
                    c.nombre = 'Enfermería'
                    and s.codigo = '2020-1'
                    and ea.nombre = 'Reprobada'
                    and ia.porcentaje_asistencia < 75
                    and a.nombre = 'Anatomía Macroscópica'
            )

            select count(*) as cantidad_alumnos_reprobados
            from
            (
                select
                    step_0.alumno
                from
                    step_0
                where
                    step_0.alumno in (
                    select
                        distinct step_1.alumno
                    from
                        step_1
                )
            )
        """
    },
    {    
        "query" : """
            Dame el nombre, apellidos y carrera de los estudiantes que pasaron al estado de carrera en pérdida durante el año 2021, desplegando el
            motivo exacto de eliminación académica registrado en su historial
             
            También dame el motivo de la pérdida de carrera (no le agregues alias)
        """,
        "expected_sql" : """
			select
                a.nombres,
                a.apellidos,
                c.nombre as carrera,
                hic.motivo
            FROM 
            	historial_inscripcion_carrera hic
            left join inscripcion_carrera ic on hic.inscripcion_carrera_id = ic.id
            left join alumno a on ic.alumno_id = a.id
            left join carrera c on ic.carrera_id = c.id
            left join estado_carrera ea on hic.estado_carrera_id = ea.id
            left JOIN semestre s ON hic.semestre_id = s.id
            where ea.nombre = 'En Pérdida'
            AND s.fecha_inicio >= '2021-01-01' 
            AND s.fecha_fin <= '2021-12-31';
        """
    },
    {
        "query" : """
            Entrégame el conteo de alumnos de Psicología (con el alias de total_alumnos) que tienen su práctica profesional en estado aprobada y que ya alcanzaron 
            el estado de egresada o titulada en su expediente académico.
        """,
        "expected_sql" : """
            select COUNT(DISTINCT alumno_id) AS total_alumnos
            from
            (
                select a.id as alumno_id 
                from practica_profesional pp 
                left join inscripcion_carrera ic on pp.inscripcion_carrera_id = ic.id 
                left join carrera c on ic.carrera_id = c.id 
                left join estado_carrera ec on ic.estado_carrera_id = ec.id 
                left join estado_practica ep on pp.estado_practica_id = ep.id
                left join alumno a on ic.alumno_id = a.id 
                
                where ec.nombre in ('Egresada', 'Titulada')
                and ep.nombre = 'Aprobada'
                and c.nombre = 'Psicología'
            );            
        """
    },
    {
        "query" : """
            Dame el nombre y apellidos de los alumnos de Arquitectura cuya práctica profesional pasó a estado rechazada en el semestre 2021-2, incluyendo el 
            comentario o motivo de rechazo registrado por el supervisor de la empresa.
        
            También debe proyectarse el comentario o motivo de rechazo de la práctica profesional (sin alias).
        """,
        "expected_sql" : """
            select *
            from
            (
                select   a.nombres, a.apellidos, hp.comentarios
                from practica_profesional pp 
                left join inscripcion_carrera ic on pp.inscripcion_carrera_id = ic.id 
                left join carrera c on ic.carrera_id = c.id 
                left join estado_carrera ec on ic.estado_carrera_id = ec.id 
                left join estado_practica ep on pp.estado_practica_id = ep.id
                left join alumno a on ic.alumno_id = a.id 
                left join semestre s on pp.semestre_id = s.id
                left JOIN historial_practica_profesional hp ON pp.id = hp.practica_profesional_id
                
                where c.nombre = 'Arquitectura'
                and ep.nombre = 'Rechazada'
                and s.codigo = '2021-2'
            )
        """
    },
    {
        "query" : """
            Necesito el promedio de la calificación final (con el alias promedio_calificacion_final) obtenida por los alumnos que aprobaron el ramo de Historia Institucional de la carrera de Derecho en el semestre 2020-2, 
            considerando tanto a los eximidos como a los que rindieron examen final. 
        """,
        "expected_sql" : """
            select avg(ia.calificacion_final) as promedio_calificacion_final
            from inscripcion_asignatura ia
            LEFT join asignatura asi ON asi.id = ia.asignatura_id
            LEFT JOIN inscripcion_carrera ic on ia.inscripcion_carrera_id = ic.id 
            left join carrera c on ic.carrera_id = c.id  
            left join semestre s on ia.semestre_id = s.id
            LEFT JOIN estado_asignatura ea ON ea.id = ia.estado_asignatura_id
            
            where c.nombre = 'Derecho'
            and asi.nombre = 'Historia Institucional'
            and s.codigo = '2020-2'
            AND ea.nombre = 'Aprobada'
        """
    },
    {
        "query" : """
            Dame el conteo comparativo de alumnos nuevos (alias como cantidad_nuevos) versus alumnos antiguos (alias como cantidad_antiguos)
            matriculados en la carrera de Derecho durante el primer semestre del año 2020 (2020-1). 
        """,
        "expected_sql" : """
            WITH nuevos AS (
                SELECT count(DISTINCT ic.alumno_id) as cantidad_nuevos
                FROM inscripcion_carrera ic
                JOIN carrera c ON c.id = ic.carrera_id
                JOIN matricula_semestral ms ON ic.id = ms.inscripcion_carrera_id
                JOIN semestre s ON ms.semestre_id = s.id
                WHERE s.codigo = '2020-1'
                AND c.nombre = 'Derecho'
                AND ms.semestre_id = ic.semestre_ingreso_id
            ),
            antiguos AS (
                SELECT count(DISTINCT ic.alumno_id) as cantidad_antiguos
                FROM inscripcion_carrera ic
                JOIN carrera c ON c.id = ic.carrera_id
                JOIN matricula_semestral ms ON ic.id = ms.inscripcion_carrera_id
                JOIN semestre s ON ms.semestre_id = s.id
                WHERE s.codigo = '2020-1'
                AND c.nombre = 'Derecho'
                AND ms.semestre_id > ic.semestre_ingreso_id
            )
            SELECT n.cantidad_nuevos, a.cantidad_antiguos
            FROM nuevos n
            CROSS JOIN antiguos a;
        """
    },
    {
        "query" : """
            Genera la lista de estudiantes que han solicitado o están en abandono de carrera.
            Despliega el rut, nombres, apellidos y carrera del alumno (alias como carrera_nombre), además del estado actual de la carrera (alias como estado_actual)
        """,
        "expected_sql" : """
            select 
                a.rut, 
                a.nombres, 
                a.apellidos, 
                c.nombre AS carrera_nombre, 
                ec.nombre AS estado_actual
            from inscripcion_carrera ic 
            left join estado_carrera ec on ic.estado_carrera_id = ec.id
            left join alumno a on a.id = ic.alumno_id
            left join carrera c on ic.carrera_id = c.id

            where
                ec.nombre ILIKE '%Abandonada%'
        """
    },
    {
        "query" : """
            Cuál es el conteo de alumnos de Ingeniería Civil Informática que inscribieron la asignatura de 
            Cálculo Diferencial en el semestre 2020-1, pero que terminaron con el ramo en estado renunciada 
            (botada) antes de las evaluaciones.
        """,
        "expected_sql" : """
                SELECT COUNT(DISTINCT a.id) AS cantidad_alumnos
                    FROM inscripcion_carrera ic
                JOIN alumno a ON ic.alumno_id = a.id
                JOIN carrera c ON ic.carrera_id = c.id
                JOIN inscripcion_asignatura ia ON ic.id = ia.inscripcion_carrera_id
                JOIN asignatura asg ON ia.asignatura_id = asg.id
                JOIN estado_asignatura ea ON ia.estado_asignatura_id = ea.id
                JOIN semestre s ON ia.semestre_id = s.id
                WHERE c.nombre ILIKE '%Ingeniería Civil Informática%'
                    AND asg.nombre ILIKE '%Cálculo Diferencial%'
                    AND s.codigo = '2020-1'
                    AND ea.nombre = 'Renunciada';
        """
    },
    {
        "query" : """
            Dame la lista de estudiantes (rut, nombres, apellidos y nombre de la carrere) que han hecho
            abandono de la carrerea, y y que figuran como morosos financieramente.

            Para el nombre de la carrera, usa el alias nombre_carrera
        """,
        "expected_sql" : """
                SELECT 
                    a.rut, 
                    a.nombres, 
                    a.apellidos, 
                    c.nombre as nombre_carrera
                FROM inscripcion_carrera ic 
                LEFT JOIN estado_carrera ec ON ic.estado_carrera_id = ec.id
                LEFT JOIN carrera c ON ic.carrera_id = c.id
                LEFT JOIN alumno a ON a.id = ic.alumno_id
                LEFT JOIN estado_financiero ef ON ef.id = a.estado_financiero_id 
                WHERE ec.nombre = 'Abandonada'
                AND ef.nombre = 'Moroso';
        """
    }

]