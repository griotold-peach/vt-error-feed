# app/container.py
"""
의존성 조립 (Dependency Assembly)
"""
from app.adapters.teams_notifier import TeamsNotifier
from app.application.services.handler import AlertHandler
from app.application.services.monitoring import MonitoringHandler
from app.application.services.incident import IncidentService


class ServiceContainer:
    """
    서비스 컨테이너
    
    애플리케이션의 모든 의존성을 생성하고 조립합니다.
    """
    
    def __init__(self):
        # Adapter 생성 (Singleton)
        self._notifier = TeamsNotifier()
        
        # Services 생성
        self._incident_service = IncidentService(self._notifier)
        self._alert_handler = AlertHandler(self._notifier, self._incident_service)
        self._monitoring_handler = MonitoringHandler(self._notifier)
    
    @property
    def alert_handler(self) -> AlertHandler:
        """AlertHandler 인스턴스"""
        return self._alert_handler
    
    @property
    def monitoring_handler(self) -> MonitoringHandler:
        """MonitoringHandler 인스턴스"""
        return self._monitoring_handler
    
    @property
    def incident_service(self) -> IncidentService:
        """IncidentService 인스턴스"""
        return self._incident_service


# 전역 컨테이너 인스턴스
_container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    """
    ServiceContainer 싱글톤 인스턴스 반환
    
    Returns:
        ServiceContainer 인스턴스
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def init_container() -> ServiceContainer:
    """
    ServiceContainer 초기화
    
    애플리케이션 시작 시 명시적으로 호출합니다.
    
    Returns:
        ServiceContainer 인스턴스
    """
    global _container
    _container = ServiceContainer()
    print("✅ Service container initialized")
    return _container