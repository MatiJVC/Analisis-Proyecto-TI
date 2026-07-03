from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base


class FactIoT(Base):
    __tablename__ = "fact_iot"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Business Keys
    sensor_id = Column(String(100), nullable=False, index=True)
    asset_id = Column(String(100), nullable=False, index=True)

    # Dimension Attributes
    sensor_type = Column(String(50), nullable=False, index=True)
    location = Column(String(255), nullable=True)

    # Core Metrics
    battery_level = Column(Float, nullable=True)  # percentage 0-100
    signal_strength = Column(Float, nullable=True)  # RSSI or similar
    last_data_received_at = Column(DateTime(timezone=True), nullable=True)
    last_ingested_at = Column(DateTime(timezone=True), nullable=True)

    # Sensor-specific data (flexible, varies by sensor_type)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    acceleration = Column(Float, nullable=True)
    connection_status = Column(String(20), nullable=True)  # connected, offline, etc

    # Status & Flags
    is_online = Column(Boolean, default=True, index=True)
    has_anomaly = Column(Boolean, default=False, index=True)
    low_battery_alert = Column(Boolean, default=False, index=True)

    # Additional metadata
    extra_data = Column(JSONB, nullable=True)  # For any additional sensor-specific fields

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Composite Indexes
    __table_args__ = (
        Index("idx_fact_iot_sensor_type", "sensor_id", "sensor_type"),
        Index("idx_fact_iot_asset_status", "asset_id", "is_online"),
        Index("idx_fact_iot_battery_alert", "low_battery_alert", "created_at"),
        Index("idx_fact_iot_anomaly", "has_anomaly", "created_at"),
    )

    def __repr__(self):
        return (
            f"<FactIoT(id={self.id}, sensor_id={self.sensor_id}, "
            f"asset_id={self.asset_id}, sensor_type={self.sensor_type}, "
            f"is_online={self.is_online}, battery={self.battery_level}%)>"
        )
