"""
Data Warehouse Helper Module
Utilities for loading and managing data in the DWH
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid

from app.models.warehouse import (
    DimUsuarios, DimProfesionales, DimZonas, DimEspecialidades, DimPacientes,
    FactVisitas, FactAlertas, FactFichasClinicas,
    AggVisitasDiarias, AggAlertas,
    AuditPipeline
)


class DimensionHelper:
    """Helper class for SCD Type 2 dimension loading"""
    
    @staticmethod
    def cargar_o_actualizar_dimension(
        db: Session,
        modelo_dim: Any,
        business_key: str,
        business_key_value: Any,
        nuevos_valores: Dict[str, Any]
    ) -> Any:
        """
        Load or update a dimension record using SCD Type 2 logic.
        
        Args:
            db: Database session
            modelo_dim: Dimension model class (e.g., DimUsuarios)
            business_key: Business key field name (e.g., 'usuario_id')
            business_key_value: Value of the business key
            nuevos_valores: Dict of new values to insert/update
            
        Returns:
            The dimension record (new or existing)
        """
        # Try to find current record
        record_actual = db.query(modelo_dim).filter(
            and_(
                getattr(modelo_dim, business_key) == business_key_value,
                modelo_dim.es_actual == True
            )
        ).first()
        
        if record_actual is None:
            # New dimension record
            nuevo_record = modelo_dim(
                **{business_key: business_key_value},
                **nuevos_valores,
                es_actual=True,
                fecha_inicio=datetime.utcnow()
            )
            db.add(nuevo_record)
            db.commit()
            return nuevo_record
        
        # Check if values changed
        valores_cambiados = False
        for campo, nuevo_valor in nuevos_valores.items():
            if getattr(record_actual, campo) != nuevo_valor:
                valores_cambiaron = True
                break
        
        if not valores_cambiados:
            # No changes, return existing record
            return record_actual
        
        # Close current record (SCD Type 2)
        record_actual.es_actual = False
        record_actual.fecha_fin = datetime.utcnow()
        
        # Create new record with updated values
        nuevo_record = modelo_dim(
            **{business_key: business_key_value},
            **nuevos_valores,
            es_actual=True,
            fecha_inicio=datetime.utcnow()
        )
        db.add(nuevo_record)
        db.commit()
        
        return nuevo_record


class FactHelper:
    """Helper class for fact table operations"""
    
    @staticmethod
    def cargar_fact_visita(
        db: Session,
        visita_id: uuid.UUID,
        paciente_dim_id: uuid.UUID,
        profesional_dim_id: uuid.UUID,
        zona_dim_id: Optional[uuid.UUID],
        usuario_creador_dim_id: Optional[uuid.UUID],
        fecha_programada: date,
        hora_programada: Optional[str] = None,
        fecha_inicio_real: Optional[datetime] = None,
        fecha_fin_real: Optional[datetime] = None,
        estado: str = "programada",
        completada: int = 0,
        puntual: int = 0
    ) -> FactVisitas:
        """
        Load a visit fact record.
        
        Calculates metrics like duration and delay automatically.
        """
        duracion_minutos = None
        retraso_minutos = None
        
        if fecha_inicio_real and fecha_fin_real:
            duracion_minutos = int((fecha_fin_real - fecha_inicio_real).total_seconds() / 60)
        
        if hora_programada and fecha_inicio_real:
            # Parse hora_programada (HH:MM) and compare with fecha_inicio_real
            try:
                hora_parts = hora_programada.split(':')
                hora_float = int(hora_parts[0]) + int(hora_parts[1]) / 60
                inicio_hora_float = fecha_inicio_real.hour + fecha_inicio_real.minute / 60
                retraso_minutos = int((inicio_hora_float - hora_float) * 60)
            except:
                pass
        
        # Check if already exists
        existente = db.query(FactVisitas).filter(
            FactVisitas.visita_id == visita_id
        ).first()
        
        if existente:
            # Update existing record
            existente.estado = estado
            existente.completada = completada
            existente.puntual = puntual
            existente.fecha_inicio_real = fecha_inicio_real
            existente.fecha_fin_real = fecha_fin_real
            existente.duracion_minutos = duracion_minutos
            existente.retraso_minutos = retraso_minutos
            existente.updated_at = datetime.utcnow()
            db.commit()
            return existente
        
        # Insert new record
        fact = FactVisitas(
            id=uuid.uuid4(),
            visita_id=visita_id,
            paciente_dim_id=paciente_dim_id,
            profesional_dim_id=profesional_dim_id,
            zona_dim_id=zona_dim_id,
            usuario_creador_dim_id=usuario_creador_dim_id,
            fecha_programada=fecha_programada,
            hora_programada=hora_programada,
            fecha_inicio_real=fecha_inicio_real,
            fecha_fin_real=fecha_fin_real,
            estado=estado,
            completada=completada,
            puntual=puntual,
            duracion_minutos=duracion_minutos,
            retraso_minutos=retraso_minutos
        )
        db.add(fact)
        db.commit()
        
        return fact
    
    @staticmethod
    def cargar_fact_alerta(
        db: Session,
        alerta_id: uuid.UUID,
        paciente_dim_id: uuid.UUID,
        tipo: str,
        prioridad: str = "MEDIUM",
        estado: str = "OPEN",
        mensaje: Optional[str] = None,
        visita_dim_id: Optional[uuid.UUID] = None
    ) -> FactAlertas:
        """Load an alert fact record."""
        
        # Check if already exists
        existente = db.query(FactAlertas).filter(
            FactAlertas.alerta_id == alerta_id
        ).first()
        
        if existente:
            # Update existing
            existente.estado = estado
            existente.updated_at = datetime.utcnow()
            db.commit()
            return existente
        
        # Insert new
        alerta = FactAlertas(
            id=uuid.uuid4(),
            alerta_id=alerta_id,
            paciente_dim_id=paciente_dim_id,
            visita_dim_id=visita_dim_id,
            tipo=tipo,
            prioridad=prioridad,
            estado=estado,
            mensaje=mensaje
        )
        db.add(alerta)
        db.commit()
        
        return alerta


class AuditHelper:
    """Helper class for pipeline audit tracking"""
    
    @staticmethod
    def iniciar_pipeline(
        db: Session,
        pipeline_name: str,
        source_system: str,
        target_table: str
    ) -> str:
        """
        Start pipeline execution tracking.
        
        Returns:
            execution_id
        """
        execution_id = f"{pipeline_name}_{datetime.utcnow().isoformat()}"
        
        audit = AuditPipeline(
            id=uuid.uuid4(),
            pipeline_name=pipeline_name,
            execution_id=execution_id,
            source_system=source_system,
            target_table=target_table,
            estado="RUNNING",
            fecha_inicio=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        
        return execution_id
    
    @staticmethod
    def finalizar_pipeline(
        db: Session,
        execution_id: str,
        estado: str = "SUCCESS",
        registros_leidos: int = 0,
        registros_insertados: int = 0,
        registros_actualizados: int = 0,
        registros_rechazados: int = 0,
        errores: Optional[str] = None,
        advertencias: Optional[str] = None
    ) -> None:
        """Finalize pipeline execution tracking."""
        
        audit = db.query(AuditPipeline).filter(
            AuditPipeline.execution_id == execution_id
        ).first()
        
        if not audit:
            raise ValueError(f"Pipeline execution {execution_id} not found")
        
        fecha_fin = datetime.utcnow()
        duracion_segundos = (fecha_fin - audit.fecha_inicio).total_seconds()
        
        audit.estado = estado
        audit.registros_leidos = str(registros_leidos)
        audit.registros_insertados = str(registros_insertados)
        audit.registros_actualizados = str(registros_actualizados)
        audit.registros_rechazados = str(registros_rechazados)
        audit.fecha_fin = fecha_fin
        audit.duracion_segundos = str(int(duracion_segundos))
        audit.errores = errores
        audit.advertencias = advertencias
        
        if estado == "SUCCESS" and registros_rechazados == 0:
            audit.calidad_datos = "100"
        elif registros_rechazados > 0:
            audit.calidad_datos = str(
                int(100.0 * (registros_leidos - registros_rechazados) / registros_leidos)
            )
        
        db.commit()


class ReportHelper:
    """Helper class for generating common reports"""
    
    @staticmethod
    def resumen_visitas_hoy(db: Session) -> Dict[str, Any]:
        """Get today's visit summary."""
        result = db.query(
            FactVisitas.estado,
            func.count(FactVisitas.id).label("cantidad"),
            func.sum(FactVisitas.completada).label("completadas"),
            func.sum(FactVisitas.puntual).label("puntuales")
        ).filter(
            FactVisitas.fecha_programada == date.today()
        ).group_by(FactVisitas.estado).all()
        
        return {
            "fecha": date.today().isoformat(),
            "resumen": [
                {
                    "estado": r.estado,
                    "cantidad": r.cantidad,
                    "completadas": r.completadas,
                    "puntuales": r.puntuales
                }
                for r in result
            ]
        }
    
    @staticmethod
    def alertas_criticas_abiertas(db: Session) -> List[Dict[str, Any]]:
        """Get all open critical alerts."""
        from sqlalchemy import func
        
        alertas = db.query(FactAlertas).filter(
            and_(
                FactAlertas.estado == "OPEN",
                FactAlertas.prioridad.in_(["CRITICAL", "HIGH"])
            )
        ).order_by(FactAlertas.created_at).all()
        
        return [
            {
                "alerta_id": str(a.alerta_id),
                "tipo": a.tipo,
                "prioridad": a.prioridad,
                "mensaje": a.mensaje,
                "tiempo_abierta": (datetime.utcnow() - a.created_at).total_seconds() / 3600
            }
            for a in alertas
        ]


# Example usage in a pipeline:
"""
def sync_visitas_diarias():
    db = SessionLocal()
    try:
        execution_id = AuditHelper.iniciar_pipeline(
            db,
            pipeline_name="sync_visitas_diarias",
            source_system="sistema_clinico_api",
            target_table="fact_visitas"
        )
        
        # Fetch from source system
        visitas_api = fetch_visitas_from_api()
        
        registros_insertados = 0
        registros_rechazados = 0
        
        for visita in visitas_api:
            try:
                FactHelper.cargar_fact_visita(
                    db,
                    visita_id=visita['id'],
                    paciente_dim_id=visita['paciente_dim_id'],
                    # ... other fields
                )
                registros_insertados += 1
            except Exception as e:
                registros_rechazados += 1
                logger.error(f"Error loading visita: {e}")
        
        AuditHelper.finalizar_pipeline(
            db,
            execution_id=execution_id,
            estado="SUCCESS" if registros_rechazados == 0 else "PARTIAL",
            registros_leidos=len(visitas_api),
            registros_insertados=registros_insertados,
            registros_rechazados=registros_rechazados
        )
    finally:
        db.close()
"""
